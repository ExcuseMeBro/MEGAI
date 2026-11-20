// Pure logic for megai-budget-guard. No I/O here, so every rule is unit-testable.
import { createHash } from 'node:crypto';

export const MODES = ['off', 'observe', 'warn', 'enforce'];

export const DEFAULTS = Object.freeze({
  mode: 'observe',
  capTools: ['bash', 'codemode', 'ipython'],
  capChars: 8000,
  headChars: 5000,
  tailChars: 2000,
  warnUsd: 5,
  stopUsd: 15,
  contextWarnTokens: 120000,
  contextTierTokens: 272000,
  requestWarn: 150,
  expensiveRatio: 3,
  baseline: { id: 'openai/gpt-6.2-sol', input: 2, cacheRead: 0.1 },
  retentionDays: 7,
  confirmTimeoutMs: 60000,
});

export const NOTICE_RESERVE = 600;
const num = (v, min, max, dflt) => (typeof v === 'number' && Number.isFinite(v) && v >= min && v <= max ? v : dflt);

/** Merge config.json and env into a validated config. Invalid values fall back to defaults. */
export function resolveConfig(file = {}, env = {}) {
  const f = file && typeof file === 'object' && !Array.isArray(file) ? file : {};
  const envMode = String(env.MEGAI_BUDGET_GUARD ?? '').trim().toLowerCase();
  const mode = envMode === '0' ? 'off' : MODES.includes(envMode) ? envMode : MODES.includes(f.mode) ? f.mode : DEFAULTS.mode;
  const capChars = num(f.capChars, 2000, 1_000_000, DEFAULTS.capChars);
  let headChars = num(f.headChars, 200, capChars, DEFAULTS.headChars);
  let tailChars = num(f.tailChars, 0, capChars, DEFAULTS.tailChars);
  // Reserve room for the notice and file path so a capped result never exceeds capChars.
  const room = capChars - NOTICE_RESERVE;
  if (headChars + tailChars > room) { headChars = Math.floor(room * 0.7); tailChars = room - headChars; }
  const warnUsd = num(f.warnUsd, 0.01, 10_000, DEFAULTS.warnUsd);
  const b = f.baseline && typeof f.baseline === 'object' ? f.baseline : {};
  return {
    mode,
    capTools: Array.isArray(f.capTools) && f.capTools.every(t => typeof t === 'string') ? [...f.capTools] : [...DEFAULTS.capTools],
    capChars, headChars, tailChars,
    warnUsd,
    stopUsd: Math.max(num(f.stopUsd, 0.01, 10_000, DEFAULTS.stopUsd), warnUsd),
    contextWarnTokens: num(f.contextWarnTokens, 1000, 10_000_000, DEFAULTS.contextWarnTokens),
    contextTierTokens: num(f.contextTierTokens, 1000, 10_000_000, DEFAULTS.contextTierTokens),
    requestWarn: num(f.requestWarn, 1, 1_000_000, DEFAULTS.requestWarn),
    expensiveRatio: num(f.expensiveRatio, 1.1, 1000, DEFAULTS.expensiveRatio),
    baseline: {
      id: typeof b.id === 'string' ? b.id : DEFAULTS.baseline.id,
      input: num(b.input, 0.000001, 10_000, DEFAULTS.baseline.input),
      cacheRead: num(b.cacheRead, 0.000001, 10_000, DEFAULTS.baseline.cacheRead),
    },
    retentionDays: num(f.retentionDays, 1, 365, DEFAULTS.retentionDays),
    confirmTimeoutMs: num(f.confirmTimeoutMs, 5000, 600_000, DEFAULTS.confirmTimeoutMs),
  };
}

export const textOf = content => (Array.isArray(content)
  ? content.filter(c => c && c.type === 'text' && typeof c.text === 'string').map(c => c.text).join('\n')
  : typeof content === 'string' ? content : '');

/**
 * Decide whether a tool result should be capped. Returns null when it is out of scope.
 * Nested calls (made by another tool such as codemode) are never capped: their output
 * feeds a script, not the model.
 */
export function capPlan(event, config) {
  if (!event || event.parentToolCallId) return null;
  if (!config.capTools.includes(String(event.toolName ?? ''))) return null;
  const text = textOf(event.content);
  if (text.length <= config.capChars) return null;
  return { text, total: text.length, omitted: text.length - config.headChars - config.tailChars };
}

/** Build the capped text shown to the model. */
export function cappedText(plan, config, path) {
  const noteFor = omitted => `[budget-guard: output was ${plan.total} chars; ${omitted} chars omitted here. ` +
    `Full output: ${path} — read only the lines you need (read with offset/limit, or grep/rg) instead of printing it again.]`;
  // Size the slices from the real notice so the whole result fits capChars.
  const room = Math.max(0, config.capChars - noteFor(plan.total).length - 8);
  let headLen = config.headChars, tailLen = config.tailChars;
  if (headLen + tailLen > room) { headLen = Math.floor(room * headLen / (headLen + tailLen)); tailLen = room - headLen; }
  const head = plan.text.slice(0, headLen);
  const tail = tailLen ? plan.text.slice(plan.text.length - tailLen) : '';
  return `${head}\n…\n${noteFor(plan.text.length - head.length - tail.length)}\n…\n${tail}`;
}

/** Replace text blocks with one capped block, keep non-text blocks (such as images). */
export function cappedContent(content, text) {
  const rest = Array.isArray(content) ? content.filter(c => !(c && c.type === 'text')) : [];
  return [{ type: 'text', text }, ...rest];
}

const modelKey = m => `${m?.provider ?? '?'}/${m?.model ?? m?.id ?? '?'}`;

/**
 * Sum billed usage over session entries, like Pi's own totals: assistant and tool-result
 * messages, plus usage, compaction and branch-summary entries (all branches: spent money
 * stays spent). Only assistant messages count as requests.
 */
export function usageTotals(entries) {
  const out = { usd: 0, requests: 0, byModel: {} };
  for (const e of Array.isArray(entries) ? entries : []) {
    if (e?.type === 'message' && e.message) addUsage(out, e.message);
    else if (e && e.type !== 'custom' && e.usage) addUsage(out, { role: e.type, provider: e.provider, model: e.model, usage: e.usage });
  }
  return out;
}

const costOf = message => { const usd = Number(message?.usage?.cost?.total); return Number.isFinite(usd) && usd > 0 ? usd : 0; };

export function addUsage(totals, message) {
  const cost = costOf(message);
  const request = message?.role === 'assistant';
  if (!request && !cost) return totals;
  if (request) totals.requests += 1;
  totals.usd += cost;
  const k = modelKey(message);
  const slot = totals.byModel[k] ??= { usd: 0, requests: 0 };
  slot.usd += cost; if (request) slot.requests += 1;
  return totals;
}

/** Totals from persisted entries, plus `message` when Pi has not persisted it yet. */
export function totalsWith(entries, message) {
  const t = usageTotals(entries);
  if (message && !(Array.isArray(entries) && entries.some(e => e?.type === 'message' && e.message?.role === message.role &&
    e.message?.timestamp === message.timestamp))) addUsage(t, message);
  return t;
}

export const STATE_TYPE = 'megai-budget-guard';

/** Latest persisted stop-limit decision in this session, if any. */
export function restoredLimit(entries, dflt) {
  let out = { limit: dflt, declined: false };
  for (const e of Array.isArray(entries) ? entries : []) {
    if (e?.type !== 'custom' || e.customType !== STATE_TYPE) continue;
    const d = e.data ?? {};
    if (typeof d.limit === 'number' && Number.isFinite(d.limit) && d.limit >= dflt) out = { limit: d.limit, declined: d.declined === true };
  }
  return out;
}

/** Price ratio of a model against the baseline, from its per-million input and cache-read prices. */
export function priceRatio(model, config) {
  const c = model?.cost;
  if (!c) return null;
  const r = [Number(c.input) / config.baseline.input, Number(c.cacheRead) / config.baseline.cacheRead].filter(Number.isFinite);
  return r.length ? Math.max(...r) : null;
}

export function modelAdvice(model, config) {
  const ratio = priceRatio(model, config);
  if (ratio === null || ratio < config.expensiveRatio) return null;
  const id = `${model.provider}/${model.id}`;
  if (id === config.baseline.id) return null;
  return {
    kind: 'model', model: id, ratio: Math.round(ratio * 10) / 10,
    message: `${id} costs ~${Math.round(ratio)}× ${config.baseline.id} per token. Use it for hard design or final review only; switch back with /model for routine work.`,
  };
}

/**
 * Thresholds newly crossed by the current state. `seen` is a Set of kinds already
 * reported in this session; this function adds to it.
 */
export function crossed(state, config, seen) {
  const out = [];
  const push = (kind, message) => { if (!seen.has(kind)) { seen.add(kind); out.push({ kind, message }); } };
  const handoff = 'Write a Factory Flow handoff on the Brokan task and continue in a new session (/new).';
  if (state.usd >= config.warnUsd) push('cost-warn', `Session cost $${state.usd.toFixed(2)} (warn at $${config.warnUsd}). Narrow the next step; avoid re-reading large files.`);
  if (state.tokens >= config.contextTierTokens) push('context-tier', `Context ${k(state.tokens)} tokens is above ${k(config.contextTierTokens)}: every request now costs about 2×. ${handoff}`);
  else if (state.tokens >= config.contextWarnTokens) push('context-warn', `Context ${k(state.tokens)} tokens (warn at ${k(config.contextWarnTokens)}). ${handoff}`);
  if (state.requests >= config.requestWarn) push('requests', `${state.requests} model requests in this session (warn at ${config.requestWarn}). ${handoff}`);
  return out;
}

export const k = n => `${Math.round(n / 1000)}k`;

export function overStop(state, limit) { return state.usd >= limit; }

export const sessionTag = id => createHash('sha256').update(String(id ?? '')).digest('hex').slice(0, 12);

const LOG_KEYS = { kind: 's', mode: 's', applied: 'b', tool: 's', chars: 'n', omitted: 'n', usd: 'n', tokens: 'n', requests: 'n', model: 's', ratio: 'n' };
const SAFE = /^[A-Za-z0-9._\/:-]{1,80}$/;

/** Numbers-only log record: whitelisted keys, short identifier strings, never content. */
export function logRecord(session, fields, now = Date.now()) {
  const out = { ts: new Date(now).toISOString(), s: sessionTag(session) };
  for (const [key, type] of Object.entries(LOG_KEYS)) {
    const v = fields?.[key];
    if (type === 'n' && typeof v === 'number' && Number.isFinite(v)) out[key] = Math.round(v * 1e4) / 1e4;
    else if (type === 'b' && typeof v === 'boolean') out[key] = v;
    else if (type === 's' && typeof v === 'string' && SAFE.test(v)) out[key] = v;
  }
  return out;
}

/** Summarize log lines for the last `days` days. */
export function summarize(lines, now = Date.now(), days = 7) {
  const since = now - days * 86400_000;
  const s = { days, sessions: new Set(), caps: 0, capsApplied: 0, omitted: 0, omittedWould: 0, kinds: {}, ended: 0, usd: 0, expensive: new Set() };
  const snapshots = new Map(); // cumulative per session: keep the latest, never sum reloads
  for (const line of lines) {
    let r; try { r = JSON.parse(line); } catch { continue; }
    const t = Date.parse(r?.ts);
    if (!Number.isFinite(t) || t < since) continue;
    s.sessions.add(r.s);
    if (r.kind === 'cap') { s.caps++; if (r.applied) { s.capsApplied++; s.omitted += r.omitted || 0; } else s.omittedWould += r.omitted || 0; continue; }
    if (r.kind === 'session') { const prev = snapshots.get(r.s); if (!prev || t >= prev.t) snapshots.set(r.s, { t, usd: r.usd || 0 }); continue; }
    if (r.kind === 'model') s.expensive.add(r.s);
    const key = r.applied === false && r.kind === 'cost-stop' ? 'cost-stop:would' : r.kind;
    s.kinds[key] = (s.kinds[key] || 0) + 1;
  }
  s.ended = snapshots.size;
  for (const v of snapshots.values()) s.usd += v.usd;
  return s;
}

export function formatWeek(s, mode) {
  const lines = [`Budget guard (${mode}) — last ${s.days} days, ${s.sessions.size} sessions logged`];
  lines.push(`Large tool outputs: ${s.caps} over the limit, ${s.capsApplied} capped; ~${k(s.omitted / 4)} tokens kept out of context` +
    (s.omittedWould ? `, ~${k(s.omittedWould / 4)} more would have been in enforce mode.` : '.'));
  const names = { 'cost-warn': 'cost warnings', 'cost-stop': 'cost stops', 'cost-stop:would': 'would-be cost stops (not enforced)', 'context-warn': 'context warnings', 'context-tier': 'contexts above the 2× price tier', requests: 'long-session warnings' };
  for (const [kind, label] of Object.entries(names)) if (s.kinds[kind]) lines.push(`${label}: ${s.kinds[kind]}`);
  if (s.expensive.size) lines.push(`Sessions on an expensive model: ${s.expensive.size}`);
  if (s.ended) lines.push(`Sessions with recorded cost: ${s.ended}, total $${s.usd.toFixed(2)} (Pi-recorded, latest snapshot per session).`);
  if (mode === 'observe') lines.push('Observe mode changed nothing. Enable with MEGAI_BUDGET_GUARD=warn or =enforce, or "mode" in config.json.');
  return lines.join('\n');
}

export function formatSession(state, config, limit, notes) {
  const top = Object.entries(state.byModel).sort((a, b) => b[1].usd - a[1].usd).slice(0, 4)
    .map(([m, v]) => `${m} $${v.usd.toFixed(2)} (${v.requests})`).join(', ');
  return [
    `Budget guard (${config.mode}) — this session: $${state.usd.toFixed(2)}, ${state.requests} requests, context ${k(state.tokens)} tokens`,
    top ? `By model: ${top}` : 'No model requests yet.',
    `Limits: warn $${config.warnUsd}, stop $${limit}${config.mode === 'enforce' ? '' : ' (enforced only in enforce mode)'}; context ${k(config.contextWarnTokens)}/${k(config.contextTierTokens)}; ${config.requestWarn} requests; outputs over ${config.capChars} chars (${config.capTools.join(', ')}).`,
    `Large outputs this session: ${notes.caps} (${notes.capsApplied} capped).`,
  ].join('\n');
}

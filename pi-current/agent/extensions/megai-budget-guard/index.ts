import { createHash, randomBytes } from 'node:crypto';
import { chmodSync, closeSync, constants, lstatSync, mkdirSync, openSync, readdirSync, readFileSync, renameSync, rmdirSync, unlinkSync, writeFileSync, writeSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import {
  STATE_TYPE, capPlan, cappedContent, cappedText, crossed, formatSession, formatWeek, logRecord, modelAdvice, overStop,
  resolveConfig, restoredLimit, sessionTag, summarize, totalsWith,
} from './core.mjs';

// Budget guard: keeps large tool outputs out of the context, reports session cost,
// context size and request count against limits, and flags expensive models.
// Default mode "observe" changes nothing and only writes a numbers-only log.
// MEGAI_BUDGET_GUARD=off|observe|warn|enforce overrides config.json "mode".
const LOG_MAX = 2 * 1024 * 1024;
const HELP = 'Budget guard: /budget (this session) | /budget week | /budget allow [USD] (raise the stop limit for this session)';

function loadFileConfig() {
  try { return JSON.parse(readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'config.json'), 'utf8')); }
  catch { return {}; }
}

// Same resolution as Pi: PI_CODING_AGENT_DIR with a leading ~ expanded, else ~/.pi/agent.
export function agentDir(env: NodeJS.ProcessEnv = process.env) {
  const v = String(env.PI_CODING_AGENT_DIR ?? '').trim();
  if (!v) return join(homedir(), '.pi', 'agent');
  if (v === '~') return homedir();
  return v.startsWith('~/') ? join(homedir(), v.slice(2)) : resolve(v);
}

/** A real directory (not a symlink), or nothing. */
function realDir(path: string) {
  try { const st = lstatSync(path); return st.isDirectory() && !st.isSymbolicLink(); } catch { return false; }
}

function privateDir(path: string) {
  mkdirSync(path, { recursive: true, mode: 0o700 });
  if (!realDir(path)) throw new Error('unsafe directory');
  chmodSync(path, 0o700);
}

export function registerBudgetGuard(pi: ExtensionAPI, env: NodeJS.ProcessEnv = process.env, fileConfig = loadFileConfig()) {
  const config = resolveConfig(fileConfig, env);
  const root = () => join(agentDir(), 'budget-guard');
  let state: any = null;

  const log = (fields: Record<string, unknown>) => {
    if (config.mode === 'off' || !state) return;
    try {
      privateDir(root());
      const file = join(root(), 'events.jsonl');
      try { const st = lstatSync(file); if (st.isFile() && st.size > LOG_MAX) renameSync(file, join(root(), 'events.1.jsonl')); } catch { /* no log yet */ }
      const fd = openSync(file, constants.O_WRONLY | constants.O_APPEND | constants.O_CREAT | constants.O_NOFOLLOW, 0o600);
      try { writeSync(fd, JSON.stringify(logRecord(state.id, { mode: config.mode, ...fields })) + '\n'); } finally { closeSync(fd); }
    } catch { /* logging never breaks a run */ }
  };
  const visible = () => config.mode === 'warn' || config.mode === 'enforce';
  const tell = (ctx: any, message: string, level = 'warning') => { if (visible()) { try { ctx?.ui?.notify?.(message, level); } catch { /* no UI */ } } };
  const entriesOf = (ctx: any) => { try { return ctx?.sessionManager?.getEntries?.() ?? []; } catch { return []; } };
  // Only enforce mode owns stop decisions; observe/warn never write session state.
  const persist = (s: any) => { if (config.mode !== 'enforce') return; try { pi.appendEntry?.(STATE_TYPE, { limit: s.limit, declined: s.declined }); } catch { /* in-memory only */ } };

  // Capped outputs exist only in enforce mode; never follow a linked store.
  function prune() {
    if (config.mode !== 'enforce') return;
    try {
      const dir = join(root(), 'outputs');
      if (!realDir(root()) || !realDir(dir)) return;
      // Expire each saved file by its own age, then drop empty session folders.
      const cutoff = Date.now() - config.retentionDays * 86400_000;
      for (const name of readdirSync(dir)) {
        if (!/^[0-9a-f]{12}$/.test(name)) continue;
        const sub = join(dir, name);
        if (!realDir(sub)) continue;
        let left = 0;
        for (const file of readdirSync(sub)) {
          const path = join(sub, file);
          const st = lstatSync(path);
          if (st.isFile() && !st.isSymbolicLink() && /\.txt$/.test(file) && st.mtimeMs < cutoff) unlinkSync(path); else left++;
        }
        if (!left) rmdirSync(sub);
      }
    } catch { /* nothing to prune */ }
  }

  function finish(ctx?: any) {
    if (!state) return;
    if (ctx) { const entries = entriesOf(ctx); if (entries.length) state.totals = totalsWith(entries); }
    if (state.totals.requests) log({ kind: 'session', usd: state.totals.usd, requests: state.totals.requests, tokens: state.maxTokens });
  }

  function ensure(ctx: any) {
    let id: string;
    try { id = ctx?.sessionManager?.getSessionId?.() || `ephemeral-${process.pid}`; } catch { id = `ephemeral-${process.pid}`; }
    if (state?.id === id) return state;
    finish();
    const entries = entriesOf(ctx);
    const saved = restoredLimit(entries, config.stopUsd);
    state = { id, totals: totalsWith(entries), tokens: 0, maxTokens: 0, seen: new Set<string>(), models: new Set<string>(),
      notes: { caps: 0, capsApplied: 0 }, limit: saved.limit, declined: saved.declined, confirming: null as Promise<boolean> | null };
    return state;
  }

  function contextTokens(ctx: any) { try { return Number(ctx?.getContextUsage?.()?.tokens) || 0; } catch { return 0; } }

  function advise(ctx: any, model: any) {
    const advice = modelAdvice(model, config);
    if (!advice || state.models.has(advice.model)) return;
    state.models.add(advice.model);
    log({ kind: 'model', model: advice.model, ratio: advice.ratio, applied: visible() });
    tell(ctx, advice.message);
  }

  function check(ctx: any) {
    const s = state;
    for (const hit of crossed({ ...s.totals, tokens: s.tokens }, config, s.seen)) {
      log({ kind: hit.kind, usd: s.totals.usd, tokens: s.tokens, requests: s.totals.requests, applied: visible() });
      tell(ctx, hit.message);
    }
  }

  pi.on('session_start', (_event: any, ctx: any) => {
    if (config.mode === 'off') return;
    try {
      const s = ensure(ctx);
      s.tokens = contextTokens(ctx); s.maxTokens = s.tokens;
      prune();
      advise(ctx, ctx?.model);
      if (s.totals.requests || s.tokens) check(ctx);
    } catch { /* fail open */ }
  });

  pi.on('model_select', (event: any, ctx: any) => {
    if (config.mode === 'off') return;
    try { ensure(ctx); advise(ctx, event?.model); } catch { /* fail open */ }
  });

  pi.on('message_end', (event: any, ctx: any) => {
    const message = event?.message;
    if (config.mode === 'off' || message?.role !== 'assistant') return;
    try {
      const s = ensure(ctx);
      s.totals = totalsWith(entriesOf(ctx), message);
      // The message's own usage is the size of the context it was answered from.
      const u = message.usage ?? {};
      const fromUsage = [u.input, u.cacheRead, u.cacheWrite, u.output].reduce((a: number, v: any) => a + (Number(v) || 0), 0);
      s.tokens = fromUsage || contextTokens(ctx) || s.tokens;
      s.maxTokens = Math.max(s.maxTokens, s.tokens);
      check(ctx);
      if (visible()) { try { ctx?.ui?.setStatus?.('budget', `$${s.totals.usd.toFixed(2)} · ${Math.round(s.tokens / 1000)}k`); } catch { /* no UI */ } }
    } catch { /* fail open */ }
  });

  pi.on('tool_call', async (_event: any, ctx: any) => {
    if (config.mode === 'off') return;
    try {
      const s = ensure(ctx);
      // Entries are synced through the current assistant message here: count every billed entry.
      s.totals = totalsWith(entriesOf(ctx));
      if (!overStop(s.totals, s.limit)) return;
      if (config.mode !== 'enforce') {
        // Dry run: record once, at the same gate and with the same totals, that enforce would stop here.
        if (!s.seen.has('cost-stop')) {
          s.seen.add('cost-stop');
          log({ kind: 'cost-stop', usd: s.totals.usd, requests: s.totals.requests, applied: false });
          tell(ctx, `Session cost $${s.totals.usd.toFixed(2)} reached the $${s.limit} stop limit (enforced only in enforce mode).`);
        }
        return;
      }
      if (!s.declined) {
        s.confirming ??= (async () => {
          const proposed = Math.max(s.limit, s.totals.usd) + config.stopUsd;
          log({ kind: 'cost-stop', usd: s.totals.usd, requests: s.totals.requests, applied: true });
          let ok = false;
          const signal = ctx?.signal;
          if (ctx?.hasUI && !signal?.aborted) {
            try {
              ok = (await ctx.ui.confirm('Budget guard',
                `This session has spent $${s.totals.usd.toFixed(2)} (limit $${s.limit}). Continue up to $${proposed.toFixed(2)}?`,
                { timeout: config.confirmTimeoutMs, signal })) === true;
            } catch { ok = false; }
          }
          // A cancelled run is not a budget decision: block this call, record nothing.
          if (signal?.aborted) return false;
          if (ok) s.limit = proposed; else s.declined = true;
          persist(s);
          return ok;
        })().finally(() => { s.confirming = null; });
        await s.confirming;
        if (!overStop(s.totals, s.limit)) return;
      }
      return {
        block: true, terminate: true,
        reason: `Budget guard: this session spent $${s.totals.usd.toFixed(2)} (limit $${s.limit}). Stop here and give a short handoff (done, next step, risks). The user can continue with /budget allow.`,
      };
    } catch { return; /* fail open */ }
  });

  pi.on('tool_result', (event: any, ctx: any) => {
    if (config.mode === 'off') return;
    try {
      const plan = capPlan(event, config);
      if (!plan) return;
      const s = ensure(ctx);
      s.notes.caps++;
      if (config.mode !== 'enforce') { log({ kind: 'cap', tool: event.toolName, chars: plan.total, omitted: plan.omitted, applied: false }); return; }
      const dir = join(root(), 'outputs', sessionTag(s.id));
      privateDir(root()); privateDir(join(root(), 'outputs')); privateDir(dir);
      const raw = String(event.toolCallId ?? '');
      // Providers may reuse call ids across turns: always add a unique suffix.
      const id = /^[A-Za-z0-9_-]{1,64}$/.test(raw) ? raw : createHash('sha256').update(raw).digest('hex').slice(0, 24);
      const path = join(dir, `${id}-${Date.now().toString(36)}-${randomBytes(4).toString('hex')}.txt`);
      writeFileSync(path, plan.text, { mode: 0o600, flag: 'wx' });
      s.notes.capsApplied++;
      log({ kind: 'cap', tool: event.toolName, chars: plan.total, omitted: plan.omitted, applied: true });
      return { content: cappedContent(event.content, cappedText(plan, config, path)) };
    } catch {
      return; // fail open: the original output stays
    }
  });

  pi.on('session_shutdown', (_event: any, ctx: any) => { try { finish(ctx); } catch { /* ignore */ } state = null; });

  pi.registerCommand('budget', {
    description: 'Session cost, context and large-output report; weekly summary; raise the stop limit',
    handler: async (input: string, ctx: any) => {
      const parts = String(input ?? '').trim().split(/\s+/).filter(Boolean);
      if (config.mode === 'off') { ctx.ui.notify('Budget guard is off (MEGAI_BUDGET_GUARD=off).', 'info'); return; }
      const s = ensure(ctx);
      s.totals = totalsWith(entriesOf(ctx));
      if (!parts.length) {
        s.tokens = contextTokens(ctx) || s.tokens;
        ctx.ui.notify(formatSession({ ...s.totals, tokens: s.tokens }, config, s.limit, s.notes), 'info');
        return;
      }
      if (parts[0] === 'week' && parts.length === 1) {
        let lines: string[] = [];
        if (realDir(root())) {
          for (const f of ['events.1.jsonl', 'events.jsonl']) {
            try {
              const p = join(root(), f);
              const st = lstatSync(p);
              if (st.isFile() && st.size <= LOG_MAX * 2) lines = lines.concat(readFileSync(p, 'utf8').split('\n'));
            } catch { /* missing */ }
          }
        }
        // Include the running session's current spend as its latest snapshot.
        if (s.totals.requests) lines.push(JSON.stringify(logRecord(s.id, { kind: 'session', usd: s.totals.usd, requests: s.totals.requests })));
        ctx.ui.notify(formatWeek(summarize(lines), config.mode), 'info');
        return;
      }
      if (parts[0] === 'allow' && parts.length <= 2) {
        if (config.mode !== 'enforce') { ctx.ui.notify(`Budget guard is in ${config.mode} mode: nothing is blocked, so there is no limit to raise.`, 'info'); return; }
        const extra = parts[1] === undefined ? config.stopUsd : Number(parts[1]);
        if (!Number.isFinite(extra) || extra <= 0 || extra > 10_000) { ctx.ui.notify(HELP, 'error'); return; }
        s.limit = Math.max(s.limit, s.totals.usd) + extra;
        s.declined = false;
        persist(s);
        log({ kind: 'allow', usd: s.limit });
        ctx.ui.notify(`Budget guard: stop limit for this session is now $${s.limit.toFixed(2)}.`, 'info');
        return;
      }
      ctx.ui.notify(HELP, parts[0] === 'help' ? 'info' : 'error');
    },
  });
}

export default function (pi: ExtensionAPI) { registerBudgetGuard(pi); }

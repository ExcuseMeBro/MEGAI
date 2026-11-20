import { createHash } from 'node:crypto';
import { appendFileSync, chmodSync, lstatSync, mkdirSync, readdirSync, readFileSync, renameSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import {
  addUsage, capPlan, cappedContent, cappedText, crossed, formatSession, formatWeek, logRecord, modelAdvice, overStop,
  resolveConfig, sessionTag, summarize, usageTotals,
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

const agentDir = () => process.env.PI_CODING_AGENT_DIR || join(homedir(), '.pi', 'agent');

function privateDir(path: string) {
  mkdirSync(path, { recursive: true, mode: 0o700 });
  const st = lstatSync(path);
  if (!st.isDirectory() || st.isSymbolicLink()) throw new Error('unsafe directory');
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
      try { if (statSync(file).size > LOG_MAX) renameSync(file, join(root(), 'events.1.jsonl')); } catch { /* no log yet */ }
      appendFileSync(file, JSON.stringify(logRecord(state.id, { mode: config.mode, ...fields })) + '\n', { mode: 0o600 });
    } catch { /* logging never breaks a run */ }
  };
  const visible = () => config.mode === 'warn' || config.mode === 'enforce';
  const tell = (ctx: any, message: string, level = 'warning') => { if (visible()) { try { ctx?.ui?.notify?.(message, level); } catch { /* no UI */ } } };

  function prune() {
    try {
      const dir = join(root(), 'outputs');
      const cutoff = Date.now() - config.retentionDays * 86400_000;
      for (const name of readdirSync(dir).slice(0, 500)) {
        const path = join(dir, name);
        const st = lstatSync(path);
        if (st.isDirectory() && !st.isSymbolicLink() && st.mtimeMs < cutoff) rmSync(path, { recursive: true, force: true });
      }
    } catch { /* nothing to prune */ }
  }

  function finish() {
    if (state && state.totals.requests) log({ kind: 'session', usd: state.totals.usd, requests: state.totals.requests, tokens: state.maxTokens });
  }

  function ensure(ctx: any) {
    const sm = ctx?.sessionManager;
    let id: string;
    try { id = sm?.getSessionId?.() || `ephemeral-${process.pid}`; } catch { id = `ephemeral-${process.pid}`; }
    if (state?.id === id) return state;
    finish();
    let totals;
    try { totals = usageTotals(sm?.getEntries?.() ?? []); } catch { totals = usageTotals([]); }
    state = { id, totals, tokens: 0, maxTokens: 0, seen: new Set<string>(), models: new Set<string>(), notes: { caps: 0, capsApplied: 0 },
      limit: config.stopUsd, declined: false, confirming: null as Promise<boolean> | null };
    return state;
  }

  function advise(ctx: any, model: any) {
    const advice = modelAdvice(model, config);
    if (!advice || state.models.has(advice.model)) return;
    state.models.add(advice.model);
    log({ kind: 'model', model: advice.model, ratio: advice.ratio, applied: visible() });
    tell(ctx, advice.message);
  }

  function check(ctx: any) {
    for (const hit of crossed({ ...state.totals, tokens: state.tokens }, config, state.seen)) {
      log({ kind: hit.kind, usd: state.totals.usd, tokens: state.tokens, requests: state.totals.requests, applied: visible() });
      tell(ctx, hit.message);
    }
  }

  pi.on('session_start', (_event: any, ctx: any) => {
    if (config.mode === 'off') return;
    try {
      ensure(ctx);
      prune();
      advise(ctx, ctx?.model);
      if (state.totals.requests) check(ctx);
    } catch { /* fail open */ }
  });

  pi.on('model_select', (event: any, ctx: any) => {
    if (config.mode === 'off') return;
    try { ensure(ctx); advise(ctx, event?.model); } catch { /* fail open */ }
  });

  pi.on('message_end', (event: any, ctx: any) => {
    if (config.mode === 'off' || event?.message?.role !== 'assistant') return;
    try {
      const s = ensure(ctx);
      addUsage(s.totals, event.message);
      const u = event.message.usage ?? {};
      const fromUsage = [u.input, u.cacheRead, u.cacheWrite, u.output].reduce((a: number, v: any) => a + (Number(v) || 0), 0);
      let tokens = fromUsage;
      try { tokens = Number(ctx?.getContextUsage?.()?.tokens) || fromUsage; } catch { /* use message usage */ }
      s.tokens = tokens; s.maxTokens = Math.max(s.maxTokens, tokens);
      check(ctx);
      if (visible()) { try { ctx?.ui?.setStatus?.('budget', `$${s.totals.usd.toFixed(2)} · ${Math.round(tokens / 1000)}k`); } catch { /* no UI */ } }
    } catch { /* fail open */ }
  });

  pi.on('tool_call', async (_event: any, ctx: any) => {
    if (config.mode !== 'enforce') return;
    try {
      const s = ensure(ctx);
      if (!overStop(s.totals, s.limit)) return;
      if (!s.declined) {
        s.confirming ??= (async () => {
          log({ kind: 'cost-stop', usd: s.totals.usd, requests: s.totals.requests, applied: true });
          if (!ctx?.hasUI) return false;
          try {
            return Boolean(await ctx.ui.confirm('Budget guard',
              `This session has spent $${s.totals.usd.toFixed(2)} (limit $${s.limit}). Continue up to $${s.limit + config.stopUsd}?`,
              { timeout: config.confirmTimeoutMs }));
          } catch { return false; }
        })();
        const ok = await s.confirming;
        s.confirming = null;
        if (ok) { s.limit += config.stopUsd; return; }
        s.declined = true;
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
      const name = /^[A-Za-z0-9_-]{1,64}$/.test(raw) ? raw : createHash('sha256').update(raw + Date.now()).digest('hex').slice(0, 24);
      const path = join(dir, `${name}.txt`);
      writeFileSync(path, plan.text, { mode: 0o600, flag: 'wx' });
      s.notes.capsApplied++;
      log({ kind: 'cap', tool: event.toolName, chars: plan.total, omitted: plan.omitted, applied: true });
      return { content: cappedContent(event.content, cappedText(plan, config, path)) };
    } catch {
      return; // fail open: the original output stays
    }
  });

  pi.on('session_shutdown', () => { try { finish(); } catch { /* ignore */ } state = null; });

  pi.registerCommand('budget', {
    description: 'Session cost, context and large-output report; weekly summary; raise the stop limit',
    handler: async (input: string, ctx: any) => {
      const parts = String(input ?? '').trim().split(/\s+/).filter(Boolean);
      if (config.mode === 'off') { ctx.ui.notify('Budget guard is off (MEGAI_BUDGET_GUARD=off).', 'info'); return; }
      const s = ensure(ctx);
      if (!parts.length) {
        try { s.tokens = Number(ctx?.getContextUsage?.()?.tokens) || s.tokens; } catch { /* keep */ }
        ctx.ui.notify(formatSession({ ...s.totals, tokens: s.tokens }, config, s.limit, s.notes), 'info');
        return;
      }
      if (parts[0] === 'week' && parts.length === 1) {
        let lines: string[] = [];
        for (const f of ['events.1.jsonl', 'events.jsonl']) {
          try {
            const p = join(root(), f);
            const st = lstatSync(p);
            if (st.isFile() && st.size <= LOG_MAX * 2) lines = lines.concat(readFileSync(p, 'utf8').split('\n'));
          } catch { /* missing */ }
        }
        ctx.ui.notify(formatWeek(summarize(lines), config.mode), 'info');
        return;
      }
      if (parts[0] === 'allow' && parts.length <= 2) {
        const extra = parts[1] === undefined ? config.stopUsd : Number(parts[1]);
        if (!Number.isFinite(extra) || extra <= 0 || extra > 10_000) { ctx.ui.notify(HELP, 'error'); return; }
        s.limit = Math.max(s.limit, s.totals.usd) + extra;
        s.declined = false;
        log({ kind: 'allow', usd: s.limit });
        ctx.ui.notify(`Budget guard: stop limit for this session is now $${s.limit.toFixed(2)}.`, 'info');
        return;
      }
      ctx.ui.notify(HELP, parts[0] === 'help' ? 'info' : 'error');
    },
  });
}

export default function (pi: ExtensionAPI) { registerBudgetGuard(pi); }

import assert from 'node:assert/strict';
import { test } from 'node:test';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, symlinkSync, utimesSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  addUsage, capPlan, cappedContent, cappedText, crossed, formatWeek, logRecord, modelAdvice, priceRatio, resolveConfig,
  restoredLimit, sessionTag, summarize, totalsWith, usageTotals,
} from '../agent/extensions/megai-budget-guard/core.mjs';
import { registerBudgetGuard } from '../agent/extensions/megai-budget-guard/index.ts';

const cfg = (file = {}, env = {}) => resolveConfig(file, env);
const assistant = (usd, model = 'gpt-6.2-sol', provider = 'openai') => ({ type: 'message', message: { role: 'assistant', provider, model, usage: { input: 1000, cacheRead: 9000, output: 100, cost: { total: usd } } } });

test('config: observe by default, env overrides, invalid values fall back', () => {
  assert.equal(cfg().mode, 'observe');
  assert.equal(cfg({ mode: 'enforce' }).mode, 'enforce');
  assert.equal(cfg({ mode: 'enforce' }, { MEGAI_BUDGET_GUARD: '0' }).mode, 'off');
  assert.equal(cfg({}, { MEGAI_BUDGET_GUARD: 'warn' }).mode, 'warn');
  assert.equal(cfg({ mode: 'bogus' }, { MEGAI_BUDGET_GUARD: 'bogus' }).mode, 'observe');
  const c = cfg({ capChars: 'x', warnUsd: -1, stopUsd: 1, warnUsd2: 3 });
  assert.equal(c.capChars, 8000); assert.equal(c.warnUsd, 5); assert.equal(c.stopUsd, 5, 'stop is never below warn');
  const small = cfg({ capChars: 3000, headChars: 2500, tailChars: 2500 });
  assert.ok(small.headChars + small.tailChars <= small.capChars);
});

test('cap: only top-level listed tools over the limit; nested calls untouched', () => {
  const c = cfg();
  const big = 'a'.repeat(6000) + 'MIDDLE' + 'z'.repeat(6000);
  const ev = (more = {}) => ({ toolName: 'codemode', toolCallId: 'call_1', content: [{ type: 'text', text: big }], ...more });
  assert.equal(capPlan(ev({ content: [{ type: 'text', text: 'short' }] }), c), null);
  assert.equal(capPlan(ev({ toolName: 'read' }), c), null);
  assert.equal(capPlan(ev({ parentToolCallId: 'outer' }), c), null);
  const plan = capPlan(ev(), c);
  assert.equal(plan.total, big.length);
  const text = cappedText(plan, c, '/tmp/x.txt');
  assert.ok(text.length <= c.capChars);
  assert.ok(text.startsWith('a'.repeat(100)) && text.endsWith('z'.repeat(100)));
  assert.ok(!text.includes('MIDDLE'));
  assert.match(text, /Full output: \/tmp\/x\.txt/);
  const image = { type: 'image', data: 'AA', mimeType: 'image/png' };
  const content = cappedContent([{ type: 'text', text: big }, image], text);
  assert.deepEqual(content, [{ type: 'text', text }, image]);
});

test('usage: totals over all entries, per model, ignores non-assistant and bad costs', () => {
  const t = usageTotals([assistant(0.5), assistant(1.25, 'gpt-6-astra'), { type: 'message', message: { role: 'user' } }, assistant(NaN), { type: 'custom' }]);
  assert.equal(t.requests, 3);
  assert.equal(Math.round(t.usd * 100), 175);
  assert.equal(t.byModel['openai/gpt-6-astra'].requests, 1);
  addUsage(t, assistant(2).message);
  assert.equal(Math.round(t.usd * 100), 375);
});

test('thresholds fire once each; context tier replaces the plain context warning', () => {
  const c = cfg(), seen = new Set();
  assert.deepEqual(crossed({ usd: 1, tokens: 50_000, requests: 10 }, c, seen), []);
  const first = crossed({ usd: 6, tokens: 130_000, requests: 151 }, c, seen).map(h => h.kind);
  assert.deepEqual(first, ['cost-warn', 'context-warn', 'requests']);
  assert.deepEqual(crossed({ usd: 7, tokens: 130_000, requests: 160 }, c, seen), []);
  const tier = crossed({ usd: 7, tokens: 300_000, requests: 160 }, c, seen);
  assert.deepEqual(tier.map(h => h.kind), ['context-tier']);
  assert.match(tier[0].message, /2×/);
});

test('model advice: flags models at or above the ratio, never the baseline', () => {
  const c = cfg();
  const astra = { provider: 'openai', id: 'gpt-6-astra', cost: { input: 10, cacheRead: 1 } };
  assert.equal(priceRatio(astra, c), 10);
  assert.match(modelAdvice(astra, c).message, /~10×/);
  assert.equal(modelAdvice({ provider: 'openai', id: 'gpt-6.2-sol', cost: { input: 2, cacheRead: 0.1 } }, c), null);
  assert.equal(modelAdvice({ provider: 'opencode-go', id: 'deepseek-v4.1-flash', cost: { input: 0.15, cacheRead: 0.003 } }, c), null);
  assert.equal(modelAdvice({ provider: 'x', id: 'nocost' }, c), null);
});

test('log records keep only whitelisted numbers and identifiers, never content', () => {
  const r = logRecord('session-secret-id', { kind: 'cap', tool: 'bash', chars: 12000, omitted: 5000, applied: true, text: 'TOKEN=abc', model: 'has spaces & stuff', extra: 1 }, 0);
  assert.deepEqual(Object.keys(r).sort(), ['applied', 'chars', 'kind', 'omitted', 's', 'tool', 'ts']);
  assert.equal(r.s, sessionTag('session-secret-id'));
  assert.ok(!JSON.stringify(r).includes('session-secret-id'));
  const now = Date.parse('2026-11-20T00:00:00Z');
  const lines = [
    JSON.stringify({ ...logRecord('a', { kind: 'cap', omitted: 4000, applied: false }, now - 1000) }),
    JSON.stringify({ ...logRecord('a', { kind: 'cost-warn' }, now - 1000) }),
    JSON.stringify({ ...logRecord('b', { kind: 'model', model: 'openai/gpt-6-astra' }, now - 1000) }),
    JSON.stringify({ ...logRecord('b', { kind: 'session', usd: 3.5 }, now - 1000) }),
    JSON.stringify({ ...logRecord('c', { kind: 'cap', omitted: 9 }, now - 30 * 86400_000) }),
    'not json',
  ];
  const s = summarize(lines, now);
  assert.equal(s.sessions.size, 2); assert.equal(s.caps, 1); assert.equal(s.omitted, 0); assert.equal(s.omittedWould, 4000); assert.equal(s.usd, 3.5);
  const text = formatWeek(s, 'observe');
  assert.match(text, /Observe mode changed nothing/);
  assert.match(text, /cost warnings: 1/);
});

// Minimal fake of the Pi extension API to exercise the wiring.
function fakePi(entries = []) {
  const handlers = {}, commands = {};
  return { handlers, commands, entries, on: (n, h) => { (handlers[n] ??= []).push(h); }, registerCommand: (n, d) => { commands[n] = d; },
    appendEntry: (customType, data) => entries.push({ type: 'custom', customType, data }) };
}
function ctxWith(entries = [], more = {}) {
  const notes = [];
  return { notes, hasUI: true, model: { provider: 'openai', id: 'gpt-6-astra', cost: { input: 10, cacheRead: 1 } },
    sessionManager: { getSessionId: () => 'sess-1', getEntries: () => entries },
    getContextUsage: () => ({ tokens: 50_000 }),
    ui: { notify: (m, l) => notes.push([l, m]), setStatus: () => {}, confirm: async () => false }, ...more };
}

test('wiring: observe mode logs but changes nothing and shows nothing', async t => {
  const dir = mkdtempSync(join(tmpdir(), 'bg-observe-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  process.env.PI_CODING_AGENT_DIR = dir;
  const pi = fakePi();
  registerBudgetGuard(pi, {}, { mode: 'observe' });
  const ctx = ctxWith([assistant(6)]);
  pi.handlers.session_start[0]({}, ctx);
  const res = pi.handlers.tool_result[0]({ toolName: 'bash', toolCallId: 'c1', content: [{ type: 'text', text: 'x'.repeat(20000) }] }, ctx);
  assert.equal(res, undefined);
  assert.equal(await pi.handlers.tool_call[0]({ toolName: 'bash' }, ctx), undefined);
  assert.deepEqual(ctx.notes, []);
  const log = readFileSync(join(dir, 'budget-guard', 'events.jsonl'), 'utf8');
  assert.match(log, /"kind":"cap"/); assert.match(log, /"kind":"model"/); assert.match(log, /"kind":"cost-warn"/);
  assert.ok(!log.includes('xxxx'));
  assert.equal(statSync(join(dir, 'budget-guard', 'events.jsonl')).mode & 0o777, 0o600);
  await pi.commands.budget.handler('', ctx);
  assert.match(ctx.notes.at(-1)[1], /\$6\.00, 1 requests/);
  await pi.commands.budget.handler('week', ctx);
  assert.match(ctx.notes.at(-1)[1], /Observe mode changed nothing/);
});

test('wiring: enforce caps to a private file, asks at the stop limit, blocks on decline, allow resumes', async t => {
  const dir = mkdtempSync(join(tmpdir(), 'bg-enforce-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  process.env.PI_CODING_AGENT_DIR = dir;
  const pi = fakePi();
  registerBudgetGuard(pi, {}, { mode: 'enforce', stopUsd: 10, warnUsd: 5 });
  let asked = 0;
  const entries = [assistant(4)];
  const ctx = ctxWith(entries, { ui: { notify: () => {}, setStatus: () => {}, confirm: async () => { asked++; return false; } } });
  pi.handlers.session_start[0]({}, ctx);
  const big = 'head-' + 'y'.repeat(20000) + '-tail';
  const res = pi.handlers.tool_result[0]({ toolName: 'codemode', toolCallId: 'call_9', content: [{ type: 'text', text: big }] }, ctx);
  const shown = res.content[0].text;
  assert.ok(shown.length < 8500 && shown.startsWith('head-') && shown.endsWith('-tail'));
  const path = shown.match(/Full output: (\S+\.txt)/)[1];
  assert.equal(readFileSync(path, 'utf8'), big);
  assert.equal(statSync(path).mode & 0o777, 0o600);
  assert.equal(await pi.handlers.tool_call[0]({ toolName: 'bash' }, ctx), undefined, 'under the limit');
  pi.handlers.message_end[0]({ message: assistant(7).message }, ctx);
  entries.push(assistant(7)); // Pi persists the message before the next tool call
  const [a, b] = await Promise.all([pi.handlers.tool_call[0]({}, ctx), pi.handlers.tool_call[0]({}, ctx)]);
  assert.equal(asked, 1, 'parallel calls share one confirmation');
  assert.equal(a.block, true); assert.equal(b.block, true); assert.equal(a.terminate, true);
  assert.equal((await pi.handlers.tool_call[0]({}, ctx)).block, true);
  assert.equal(asked, 1, 'no repeat prompt after a decline');
  await pi.commands.budget.handler('allow 5', ctx);
  assert.equal(await pi.handlers.tool_call[0]({}, ctx), undefined);
  const nested = pi.handlers.tool_result[0]({ toolName: 'bash', parentToolCallId: 'call_9', toolCallId: 'n1', content: [{ type: 'text', text: big }] }, ctx);
  assert.equal(nested, undefined);
  assert.equal(existsSync(join(dir, 'budget-guard', 'outputs')), true);
});

test('wiring: off mode registers but does nothing', async t => {
  const dir = mkdtempSync(join(tmpdir(), 'bg-off-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  process.env.PI_CODING_AGENT_DIR = dir;
  const pi = fakePi();
  registerBudgetGuard(pi, { MEGAI_BUDGET_GUARD: 'off' }, { mode: 'enforce' });
  const ctx = ctxWith([assistant(50)]);
  pi.handlers.session_start[0]({}, ctx);
  assert.equal(pi.handlers.tool_result[0]({ toolName: 'bash', content: [{ type: 'text', text: 'x'.repeat(20000) }] }, ctx), undefined);
  assert.equal(await pi.handlers.tool_call[0]({}, ctx), undefined);
  assert.equal(existsSync(join(dir, 'budget-guard')), false);
});

test('review fixes: cap fits its limit even with large configured slices', () => {
  const c = cfg({ capChars: 8000, headChars: 6000, tailChars: 2000 });
  const plan = capPlan({ toolName: 'bash', content: [{ type: 'text', text: 'q'.repeat(8001) }] }, c);
  assert.ok(cappedText(plan, c, '/very/long/path/'.repeat(8) + 'x.txt').length <= 8000);
});

test('review fixes: totals count usage, compaction and tool-result costs; pending message once', () => {
  const entries = [assistant(14), { type: 'compaction', usage: { cost: { total: 2 } } }, { type: 'usage', kind: 'cache_warm', provider: 'openai', model: 'm', usage: { cost: { total: 0.5 } } },
    { type: 'message', message: { role: 'toolResult', usage: { cost: { total: 0.25 } } } }, { type: 'custom', customType: 'x', usage: { cost: { total: 99 } } }];
  const t = usageTotals(entries);
  assert.equal(t.usd, 16.75); assert.equal(t.requests, 1);
  const pending = { role: 'assistant', timestamp: 5, usage: { cost: { total: 1 } } };
  assert.equal(totalsWith(entries, pending).usd, 17.75);
  assert.equal(totalsWith([...entries, { type: 'message', message: pending }], pending).usd, 17.75, 'not counted twice');
  assert.deepEqual(restoredLimit([{ type: 'custom', customType: 'megai-budget-guard', data: { limit: 30, declined: true } }], 15), { limit: 30, declined: true });
  assert.deepEqual(restoredLimit([{ type: 'custom', customType: 'megai-budget-guard', data: { limit: 3 } }], 15), { limit: 15, declined: false });
});

test('review fixes: weekly report keeps the latest snapshot per session and separates would-be actions', () => {
  const now = Date.parse('2026-11-20T00:00:00Z');
  const lines = [1, 2, 3].map(i => JSON.stringify(logRecord('a', { kind: 'session', usd: 10 }, now - i * 1000)))
    .concat(JSON.stringify(logRecord('a', { kind: 'cost-stop', applied: false }, now - 1)), JSON.stringify(logRecord('a', { kind: 'cap', omitted: 8000, applied: false }, now - 1)));
  const s = summarize(lines, now);
  assert.equal(s.ended, 1); assert.equal(s.usd, 10);
  const text = formatWeek(s, 'observe');
  assert.match(text, /would-be cost stops \(not enforced\): 1/);
  assert.match(text, /0 capped; ~0k tokens kept out of context, ~2k more would have been/);
});

function setDir(t, name) {
  const dir = mkdtempSync(join(tmpdir(), name));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  process.env.PI_CODING_AGENT_DIR = dir;
  return dir;
}

test('review fixes: pruning never follows a linked store and does not run in observe', t => {
  const dir = setDir(t, 'bg-prune-');
  const outside = join(dir, 'outside'), old = join(outside, 'abcdefabcdef');
  mkdirSync(old, { recursive: true }); writeFileSync(join(old, 'keep.txt'), 'x');
  const past = new Date(Date.now() - 30 * 86400_000); utimesSync(old, past, past);
  mkdirSync(join(dir, 'budget-guard'), { recursive: true }); symlinkSync(outside, join(dir, 'budget-guard', 'outputs'));
  for (const mode of ['enforce', 'observe']) {
    const pi = fakePi(); registerBudgetGuard(pi, {}, { mode });
    pi.handlers.session_start[0]({}, ctxWith());
    assert.ok(existsSync(join(old, 'keep.txt')), mode);
  }
  rmSync(join(dir, 'budget-guard', 'outputs'));
  const real = join(dir, 'budget-guard', 'outputs', 'abcdefabcdef'); mkdirSync(real, { recursive: true }); utimesSync(real, past, past);
  const obs = fakePi(); registerBudgetGuard(obs, {}, { mode: 'observe' }); obs.handlers.session_start[0]({}, ctxWith());
  assert.ok(existsSync(real), 'observe changes nothing');
  const enf = fakePi(); registerBudgetGuard(enf, {}, { mode: 'enforce' }); enf.handlers.session_start[0]({}, ctxWith());
  assert.ok(!existsSync(real), 'enforce prunes its own stale output folders');
});

test('review fixes: stop includes compaction cost, ceiling is above spend, one increase, survives reload', async t => {
  setDir(t, 'bg-stop-');
  const entries = [assistant(14), { type: 'compaction', usage: { cost: { total: 2 } } }];
  let asked = 0;
  const ui = answer => ({ notify: () => {}, setStatus: () => {}, confirm: async () => { asked++; return answer; } });
  const pi = fakePi(entries); registerBudgetGuard(pi, {}, { mode: 'enforce', stopUsd: 15, warnUsd: 5 });
  const ctx = ctxWith(entries, { ui: ui('yes') });
  pi.handlers.session_start[0]({}, ctx);
  assert.equal((await pi.handlers.tool_call[0]({}, ctx)).block, true, 'truthy non-true answer is a decline');
  assert.equal(asked, 1);
  // Reload: a new instance on the same session stays blocked without asking again.
  const again = fakePi(entries); registerBudgetGuard(again, {}, { mode: 'enforce', stopUsd: 15, warnUsd: 5 });
  const ctx2 = ctxWith(entries, { ui: ui(true) });
  again.handlers.session_start[0]({}, ctx2);
  assert.equal((await again.handlers.tool_call[0]({}, ctx2)).block, true);
  assert.equal(asked, 1);
  // A resumed $35 session: acceptance must set a ceiling above spend, once, for parallel calls.
  const rich = [assistant(35)];
  const p3 = fakePi(rich); registerBudgetGuard(p3, {}, { mode: 'enforce', stopUsd: 15, warnUsd: 5 });
  const ctx3 = ctxWith(rich, { sessionManager: { getSessionId: () => 'sess-3', getEntries: () => rich }, ui: ui(true) });
  p3.handlers.session_start[0]({}, ctx3);
  const both = await Promise.all([p3.handlers.tool_call[0]({}, ctx3), p3.handlers.tool_call[0]({}, ctx3)]);
  assert.deepEqual(both, [undefined, undefined]);
  assert.equal(asked, 2, 'one prompt for parallel calls');
  assert.equal(rich.at(-1).data.limit, 50, 'one increase from current spend');
  const p4 = fakePi(rich); registerBudgetGuard(p4, {}, { mode: 'enforce', stopUsd: 15, warnUsd: 5 });
  p4.handlers.session_start[0]({}, ctx3);
  assert.equal(await p4.handlers.tool_call[0]({}, ctx3), undefined, 'approved ceiling survives reload');
});

test('review fixes: context from the answered message and on resume; observe records a would-be stop', t => {
  const dir = setDir(t, 'bg-ctx-');
  const notes = [];
  const pi = fakePi(); registerBudgetGuard(pi, {}, { mode: 'warn' });
  const ctx = ctxWith([], { getContextUsage: () => ({ tokens: 110_000 }), ui: { notify: (m) => notes.push(m), setStatus: () => {}, confirm: async () => true } });
  pi.handlers.session_start[0]({}, ctx);
  pi.handlers.message_end[0]({ message: { role: 'assistant', timestamp: 1, usage: { input: 5000, cacheRead: 125_000, output: 300, cost: { total: 0.1 } } } }, ctx);
  assert.ok(notes.some(n => /Context 130k/.test(n)), notes.join('|'));
  const resumed = fakePi(); registerBudgetGuard(resumed, {}, { mode: 'warn' });
  const n2 = [];
  resumed.handlers.session_start[0]({}, ctxWith([], { sessionManager: { getSessionId: () => 'r', getEntries: () => [] }, getContextUsage: () => ({ tokens: 300_000 }), ui: { notify: m => n2.push(m), setStatus: () => {} } }));
  assert.ok(n2.some(n => /2×/.test(n)));
  const obs = fakePi(); registerBudgetGuard(obs, {}, { mode: 'observe' });
  obs.handlers.session_start[0]({}, ctxWith([assistant(16)], { sessionManager: { getSessionId: () => 'o', getEntries: () => [assistant(16)] } }));
  const log = readFileSync(join(dir, 'budget-guard', 'events.jsonl'), 'utf8');
  assert.match(log, /"kind":"cost-stop","mode":"observe","applied":false/);
});

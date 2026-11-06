// Run: node --experimental-strip-types --test pi-current/tests/keep-going.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const core = await import(join(root, 'agent/extensions/megai-keep-going/keep-going-core.mjs'));
const { classifyFinal, isGptModel, modeFromEnv, NUDGE } = core;

test('premature stops observed in real GPT sessions are detected', () => {
  // spm#766: two clarifying questions instead of coding.
  assert.equal(classifyFinal('Ikki narsani aniqlashtirib ber, bro:  1. Kassir **faqat o‘z filialidagi** to‘lovlarni o‘zgartirib/o‘chirsinmi? 2. Tahrirlashda qaysi maydonlar kerak?  Hozircha kodga yoki prodga o‘zgartirish kiritilmadi.'), 'ask');
  // spm#762: investigated, changed nothing.
  assert.equal(classifyFinal('**Holat:** kod o‘zgartirilmagan, testlar o‘tkazilmagan, `dev → main` merge yoki prod deploy bajarilmagan.'), 'not-done');
  assert.equal(classifyFinal('Agar Firebase kerak bo‘lmasa, plaginni o‘chirib APK chiqara olaman — ayting, shunday qilamizmi?'), 'ask');
  assert.equal(classifyFinal('I found the root cause in auth.ts. Should I go ahead and implement the fix?'), 'ask');
  assert.equal(classifyFinal('Here is the plan. Do you want me to start with the backend?'), 'ask');
  assert.equal(classifyFinal('Testlar yashil. Endi dev ga push qilaymi?', { edited: true }), 'ask');
  assert.equal(classifyFinal('План готов. Продолжить?'), 'ask');
  assert.equal(classifyFinal('Do I have your permission to add an index on the `email` column of your `users` table?'), 'ask');
  assert.equal(classifyFinal('I will apply the migration once I have your approval.'), 'ask');
  assert.equal(classifyFinal('I have not made any changes yet; the design needs a decision.'), 'not-done');
});

test('finished work and plain reports are left alone', () => {
  assert.equal(classifyFinal('`npm run verify` is green: lint, 73 tests and build pass. Merged to dev at 1a2b3c4 and pushed; task worktree removed.'), null);
  assert.equal(classifyFinal('Tayyor: endpoint qo‘shildi, testlar o‘tdi, dev ga push qilindi.'), null);
  // A question in the middle of a long report is not the ending.
  const report = 'Why did it fail? The cache key ignored tenant id. ' + 'Fixed and verified. '.repeat(60);
  assert.equal(classifyFinal(report), null);
  // Closing offers after real edits are normal, not a refusal.
  assert.equal(classifyFinal('Done, all tests pass. If you want, I can also add a migration guide.', { edited: true }), null);
  assert.equal(classifyFinal('Done. Let me know if you need anything else.', { edited: true }), null);
  // Questions inside code blocks do not count.
  assert.equal(classifyFinal('Added the prompt:\n```\nconst q = "Shall I continue?";\n```\nAll tests pass.'), null);
  assert.equal(classifyFinal(''), null);
});

test('offers count only when nothing was changed', () => {
  assert.equal(classifyFinal('I reviewed the module. If you want, I can refactor it.'), 'ask');
  assert.equal(classifyFinal('I reviewed the module. If you want, I can refactor it.', { edited: true }), null);
});

test('model gating and env switch', () => {
  assert.equal(isGptModel({ provider: 'openai', id: 'gpt-6.1-sol' }), true);
  assert.equal(isGptModel({ provider: 'opencode-go', id: 'openai/gpt-6.1-terra' }), true);
  assert.equal(isGptModel({ provider: 'anthropic', id: 'claude-opus-5-5' }), false);
  assert.equal(isGptModel({ provider: 'deepseek', id: 'deepseek-v4.1-flash' }), false);
  assert.equal(isGptModel(undefined), false);
  assert.equal(modeFromEnv({}), 'gpt');
  assert.equal(modeFromEnv({ MEGAI_KEEP_GOING: '0' }), 'off');
  assert.equal(modeFromEnv({ MEGAI_KEEP_GOING: 'all' }), 'all');
});

async function loadExtension() {
  const handlers = {};
  const mod = await import(join(root, 'agent/extensions/megai-keep-going/index.ts'));
  mod.default({ on: (name, fn) => { handlers[name] = fn; } });
  return handlers;
}

function settleEvent(userText, assistantContent, extra = {}) {
  return {
    type: 'agent_before_settle', entries: [], continue: false, outcome: 'completed',
    context: {
      canContinue: true, pendingMessages: [], contextEntries: [], contextMessages: [],
      llmMessages: [
        { role: 'user', content: [{ type: 'text', text: userText }] },
        { role: 'assistant', content: assistantContent },
      ],
    },
    ...extra,
  };
}

const gpt = { model: { provider: 'openai', id: 'gpt-6.1-sol' } };
const ask = [{ type: 'text', text: 'Plan tayyor. Boshlaymi?' }];

test('Pi extension continues GPT once per user prompt', async () => {
  const h = await loadExtension();
  h.before_agent_start({ messageType: 'user' });
  const first = h.agent_before_settle(settleEvent('payment edit API qo‘sh', ask), gpt);
  assert.equal(first.continue, true);
  assert.deepEqual(first.entries, [{ type: 'custom_message', customType: 'megai-keep-going', content: NUDGE, display: true }]);
  assert.equal(h.agent_before_settle(settleEvent('payment edit API qo‘sh', ask), gpt), undefined, 'second stop in same prompt');
  h.before_agent_start({ messageType: 'custom' });
  assert.equal(h.agent_before_settle(settleEvent('x', ask), gpt), undefined, 'custom runs do not reset');
  h.before_agent_start({ messageType: 'user' });
  assert.equal(h.agent_before_settle(settleEvent('yana bitta', ask), gpt).continue, true, 'new user prompt resets');
});

test('Pi extension skips non-GPT, questions, aborted runs, queued input and finished work', async () => {
  const h = await loadExtension();
  const reset = () => h.before_agent_start({ messageType: 'user' });
  reset(); assert.equal(h.agent_before_settle(settleEvent('fix it', ask), { model: { provider: 'anthropic', id: 'claude-opus-5-5' } }), undefined);
  reset(); assert.equal(h.agent_before_settle(settleEvent('nima deysan, shunisi yaxshimi?', ask), gpt), undefined);
  reset(); assert.equal(h.agent_before_settle(settleEvent('fix it', ask, { outcome: 'aborted' }), gpt), undefined);
  reset(); const queued = settleEvent('fix it', ask); queued.context.pendingMessages = [{}];
  assert.equal(h.agent_before_settle(queued, gpt), undefined);
  reset(); assert.equal(h.agent_before_settle(settleEvent('fix it', [{ type: 'text', text: 'Done; tests pass and dev is pushed.' }]), gpt), undefined);
  reset(); const offered = [
    { type: 'toolCall', id: '1', name: 'edit', arguments: {} },
    { type: 'text', text: 'Done. If you want, I can also add docs.' },
  ];
  assert.equal(h.agent_before_settle(settleEvent('fix it', offered), gpt), undefined);
  reset(); assert.equal(h.agent_before_settle(null, gpt), undefined, 'fails open');
});

test('Pi extension anchors on the real prompt, not injected custom messages', async () => {
  const h = await loadExtension();
  h.before_agent_start({ messageType: 'user' });
  // agentmemory recall arrives as role "custom" after the prompt; llmMessages would fold it into a user turn.
  const ev = settleEvent('payment edit API qo‘sh', [{ type: 'toolCall', id: '1', name: 'edit', arguments: {} }]);
  ev.context.contextMessages = [
    { role: 'user', content: 'payment edit API qo‘sh' },
    { role: 'custom', customType: 'agentmemory-recall', content: 'Reference data?' },
    { role: 'assistant', content: [{ type: 'toolCall', id: '1', name: 'edit', arguments: {} }] },
    { role: 'toolResult', content: [{ type: 'text', text: 'ok' }] },
    { role: 'assistant', content: [{ type: 'text', text: 'Done. If you want, I can also add docs.' }] },
  ];
  assert.equal(h.agent_before_settle(ev, gpt), undefined, 'edit before the offer is seen');
  ev.context.contextMessages[4] = { role: 'assistant', content: [{ type: 'text', text: 'Endpoint qo‘shildi. Dev ga push qilaymi?' }] };
  assert.equal(h.agent_before_settle(ev, gpt).continue, true);
});

function runHook(input, env = {}) {
  const hook = join(root, 'codex/hooks/megai-keep-going.mjs');
  const r = spawnSync(process.execPath, [hook], { input: JSON.stringify(input), env: { ...process.env, ...env }, encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr);
  return JSON.parse(r.stdout);
}

function transcript(lines) {
  const dir = mkdtempSync(join(tmpdir(), 'keep-going-'));
  const file = join(dir, 'rollout.jsonl');
  writeFileSync(file, lines.map((l) => JSON.stringify(l)).join('\n') + '\n');
  return file;
}
const user = (text) => ({ type: 'response_item', payload: { type: 'message', role: 'user', content: [{ type: 'input_text', text }] } });
const call = (name, input) => ({ type: 'response_item', payload: { type: 'custom_tool_call', name, input } });

test('Codex Stop hook blocks (continues) once on a permission question', () => {
  const t = transcript([user('<environment_context>cwd</environment_context>'), user('add the endpoint')]);
  const out = runHook({ hook_event_name: 'Stop', stop_hook_active: false, last_assistant_message: 'Should I implement it now?', transcript_path: t });
  assert.deepEqual(out, { decision: 'block', reason: NUDGE });
  assert.deepEqual(runHook({ stop_hook_active: true, last_assistant_message: 'Should I implement it now?', transcript_path: t }), {});
  assert.deepEqual(runHook({ stop_hook_active: false, last_assistant_message: 'Should I implement it now?' }, { MEGAI_KEEP_GOING: '0' }), {});
});

test('Codex Stop hook leaves finished work, question prompts and bad input alone', () => {
  const edited = transcript([user('fix the bug'), call('exec', "await tools.exec_command({cmd: \"sed -i '' s/a/b/ app.ts\"})")]);
  assert.deepEqual(runHook({ stop_hook_active: false, last_assistant_message: 'Fixed. If you want, I can also add tests.', transcript_path: edited }), {});
  const question = transcript([user('qaysi variant yaxshiroq?')]);
  assert.deepEqual(runHook({ stop_hook_active: false, last_assistant_message: 'B variant. Shuni qilaymi?', transcript_path: question }), {});
  assert.deepEqual(runHook({ stop_hook_active: false, last_assistant_message: 'All tests pass.' }), {});
  const r = spawnSync(process.execPath, [join(root, 'codex/hooks/megai-keep-going.mjs')], { input: 'not json', encoding: 'utf8' });
  assert.equal(r.status, 0);
  assert.deepEqual(JSON.parse(r.stdout), {});
});

test('Pi and Codex share an identical classifier', () => {
  assert.equal(
    readFileSync(join(root, 'agent/extensions/megai-keep-going/keep-going-core.mjs'), 'utf8'),
    readFileSync(join(root, 'codex/hooks/keep-going-core.mjs'), 'utf8'),
  );
});

test('hooks.json registers exactly the Stop hook', () => {
  const cfg = JSON.parse(readFileSync(join(root, 'codex/hooks.json'), 'utf8'));
  assert.deepEqual(Object.keys(cfg.hooks), ['Stop']);
  assert.match(cfg.hooks.Stop[0].hooks[0].command, /\$HOME\/\.codex\/hooks\/megai-keep-going\.mjs/);
});

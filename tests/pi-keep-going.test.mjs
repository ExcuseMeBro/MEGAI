import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, realpathSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';
import {
  CUSTOM_TYPE, NUDGE, buildNudge, classifyFinal, isReservedBlock, maxFromEnv, isGptModel,
} from '../pi-defaults/extensions/megai-keep-going/keep-going-core.mjs';
import { decide } from '../pi-defaults/extensions/megai-keep-going/index.ts';
import { piPackageRoot } from './pi-package.mjs';

const extensionPath = fileURLToPath(new URL('../pi-defaults/extensions/megai-keep-going/index.ts', import.meta.url));

test('classifier: premature stops by kind', () => {
  const cases = [
    ['Implemented the parser. Shall I also wire the CLI?', {}, 'ask'],
    ['Rejani tayyorladim. Boshlaymi?', {}, 'ask'],
    ['Which approach would you prefer: A or B?', {}, 'ask'],
    ['I reviewed the module. I will now implement the retry logic.', { edited: true, toolsRan: true }, 'announce'],
    ["Got it. Next, I'll run the tests and fix failures.", { toolsRan: true }, 'announce'],
    ['Kodni o‘qib chiqdim. Endi migratsiyani yozaman.', { toolsRan: true }, 'announce'],
    ['Hammasi aniq. Migratsiyani yozishni boshlayman.', { toolsRan: true }, 'announce'],
    ['Понял задачу. Сейчас исправлю обработчик.', { toolsRan: true }, 'announce'],
    ['Implementing the full sync engine is too large for a single turn.', { toolsRan: true }, 'refusal'],
    ['I can\'t complete the payment integration here.', {}, 'refusal'],
    ['Added the model.\n\nRemaining work:\n- endpoints\n- tests', { edited: true, toolsRan: true }, 'unfinished'],
    ['Model qo‘shildi. Qolgan ishlar: endpoint va testlar.', { edited: true, toolsRan: true }, 'unfinished'],
    ['The endpoint is not yet implemented.', { edited: true, toolsRan: true }, 'unfinished'],
    ['Plan:\n1. Add table\n2. Add API\n3. Add UI', { toolsRan: false }, 'plan'],
    ['No code changes were made.', { toolsRan: true }, 'not-done'],
    ['Investigated.\n\nNext steps:\n- patch the handler', { toolsRan: true }, 'unfinished'],
  ];
  for (const [text, opts, expected] of cases) assert.equal(classifyFinal(text, opts), expected, text);
});

test('classifier: finished reports and real blockers are left alone', () => {
  const quiet = [
    ['Delivered 1a2b3c4 to origin/dev; tests pass; Brokan megai#1 → review.', { edited: true, toolsRan: true }],
    ['Done. If you want, I can also add a dark theme later.', { edited: true, toolsRan: true }],
    ['Plan:\n1. a\n2. b\n3. c', { toolsRan: true }],
    ['Fixed the bug and added a regression test. Run `/reload` to pick it up.', { edited: true, toolsRan: true }],
    ['Everything else is delivered. I need the Stripe API key to finish the live check; shall I wait?', { edited: true, toolsRan: true }],
    ['Merged to dev. Pushing to main needs your approval: proceed?', { edited: true, toolsRan: true }],
    ['The staging host is unreachable, so the deploy smoke check is blocked.', { toolsRan: true }],
    ['Task paused: missing migration owner.\nFACTORY_PAUSE', { toolsRan: true }],
    ['I mentioned earlier that I will now implement it, and it is implemented and tested.', { edited: true, toolsRan: true }],
    ['1. Add table\n2. Add API\n3. Add UI', { toolsRan: false }],
    ['Lane 2 delivered. #1065 agenti hali ishlamoqda; natijasi kelgach birlashtiriladi.', { edited: true, toolsRan: true }],
    ['Kod tayyor. Xotira bosimi og‘ir DB testlarini bloklayapti; gate Brokan’da qayd etildi.', { edited: true, toolsRan: true }],
    ['Qolgan ishlar provayder ruxsati va production tasdig‘ini kutyapti.', { edited: true, toolsRan: true }],
    ['', {}],
  ];
  for (const [text, opts] of quiet) assert.equal(classifyFinal(text, opts), null, text);
  assert.ok(isReservedBlock('Need the production database password to continue.'));
  assert.equal(isReservedBlock('Delivered to dev.'), false);
});

test('nudge text escalates and keeps the reserved boundary', () => {
  assert.match(NUDGE, /pre-approved/);
  const first = buildNudge('announce', 1, 3), second = buildNudge('announce', 2, 3);
  assert.match(first, /^\[megai keep-going 1\/3 · announce\]/);
  assert.doesNotMatch(first, /repeated stop/);
  assert.match(second, /repeated stop/);
  for (const text of [first, second]) assert.match(text, /production data, real money movement, main\/release\/tag\/force push, spending/);
  assert.equal(maxFromEnv({}), 3);
  assert.equal(maxFromEnv({ MEGAI_KEEP_GOING_MAX: '5' }), 5);
  assert.equal(maxFromEnv({ MEGAI_KEEP_GOING_MAX: '99' }), 8);
  assert.equal(maxFromEnv({ MEGAI_KEEP_GOING_MAX: 'x' }), 3);
  assert.ok(isGptModel({ provider: 'openai', id: 'gpt-6.1-sol' }));
  assert.equal(isGptModel({ provider: 'anthropic', id: 'claude-opus' }), false);
});

const user = (text) => ({ role: 'user', content: text });
const said = (text) => ({ role: 'assistant', content: [{ type: 'text', text }] });
const tool = (name = 'bash') => ({ role: 'assistant', content: [{ type: 'toolCall', id: 't', name, arguments: {} }] });
const own = () => ({ role: 'custom', customType: CUSTOM_TYPE, content: 'nudge', display: true });
const settle = (messages, extra = {}) => ({ outcome: 'completed', continue: false, entries: [],
  context: { contextMessages: messages, llmMessages: [], pendingMessages: [], canContinue: false }, ...extra });
const gpt = { provider: 'openai', id: 'gpt-6.1-sol' };

test('decide: model scope, outcome, pending input and question prompts', () => {
  const stop = [user('Add retries'), tool(), said('I will now add the retry logic.')];
  assert.deepEqual(decide(settle(stop), gpt, {}), { reason: 'announce', round: 1, max: 3 });
  assert.equal(decide(settle(stop), { provider: 'anthropic', id: 'claude' }, {}), null);
  assert.ok(decide(settle(stop), { provider: 'anthropic', id: 'claude' }, { MEGAI_KEEP_GOING: 'all' }));
  assert.equal(decide(settle(stop), gpt, { MEGAI_KEEP_GOING: '0' }), null);
  assert.equal(decide(settle(stop, { outcome: 'aborted' }), gpt, {}), null);
  assert.equal(decide(settle(stop, { continue: true }), gpt, {}), null);
  const pending = settle(stop); pending.context.pendingMessages = [user('wait')];
  assert.equal(decide(pending, gpt, {}), null);
  assert.equal(decide(settle([user('Is this safe?'), said('Shall I patch it?')]), gpt, {}), null);
});

test('decide: bounded budget, repeat and no-progress stops, Factory segments', () => {
  const env = {};
  const base = [user('Build the export'), tool('edit')];
  assert.equal(decide(settle([...base, said('Shall I proceed?'), own(), tool(), said('Next, I will run the tests.')]), gpt, env).round, 2);
  // Same reply after a nudge: the model is not moving.
  assert.equal(decide(settle([...base, said('Shall I proceed?'), own(), said('Shall I proceed?')]), gpt, env), null);
  // Two text-only answers in a row after nudges.
  assert.equal(decide(settle([...base, said('Shall I proceed?'), own(), said('Should I start now?'), own(), said('Can I begin?')]), gpt, env), null);
  // Progress between nudges keeps the budget alive up to the limit.
  const progressing = [...base, said('Shall I proceed?'), own(), tool(), said('Should I start step 2?'), own(), tool(), said('Can I do step 3?')];
  assert.equal(decide(settle(progressing), gpt, env).round, 3);
  assert.equal(decide(settle([...progressing, own(), tool(), said('May I do step 4?')]), gpt, env), null);
  assert.equal(decide(settle([...progressing, own(), tool(), said('May I do step 4?')]), gpt, { MEGAI_KEEP_GOING_MAX: '5' }).round, 4);
  // A Factory task message starts a fresh budget.
  const factory = { role: 'custom', customType: 'megai-factory', content: 'Run megai#2', display: true };
  assert.equal(decide(settle([...progressing, own(), tool(), said('Delivered.'), factory, tool(), said('Shall I continue?')]), gpt, env).round, 1);
  // Other custom messages (memory recall) do not reset it.
  const recall = { role: 'custom', customType: 'agentmemory', content: 'recall', display: false };
  assert.equal(decide(settle([...progressing, own(), recall, tool(), said('May I do step 4?')]), gpt, env), null);
});

// The installed Pi SDK with its native faux model drives the real extension through
// agent_before_settle, so the continuation is a real provider request.
const root = piPackageRoot();
const native = { timeout: 60000 };

async function session(t, respond) {
  const { createAgentSession, DefaultResourceLoader, ModelRuntime, SessionManager, SettingsManager } =
    await import(pathToFileURL(join(root, 'dist/index.js')));
  const { fauxProvider, fauxAssistantMessage, InMemoryCredentialStore } =
    await import(pathToFileURL(join(dirname(root), 'pi-ai/dist/index.js')));
  const base = realpathSync(mkdtempSync(join(tmpdir(), 'pi-keep-going-')));
  const cwd = join(base, 'cwd'), agentDir = join(base, 'agent');
  mkdirSync(cwd); mkdirSync(agentDir);
  const priorDir = process.env.PI_CODING_AGENT_DIR, priorMode = process.env.MEGAI_KEEP_GOING;
  process.env.PI_CODING_AGENT_DIR = agentDir;
  process.env.MEGAI_KEEP_GOING = 'all'; // The faux model is not a GPT model.
  const settingsManager = SettingsManager.inMemory({ compaction: { enabled: false } }, { projectTrusted: true });
  const resourceLoader = new DefaultResourceLoader({ cwd, agentDir, settingsManager,
    additionalExtensionPaths: [extensionPath], noSkills: true, noContextFiles: true, noPromptTemplates: true, noThemes: true });
  await resourceLoader.reload();
  assert.deepEqual(resourceLoader.getExtensions().errors, []);
  const modelRuntime = await ModelRuntime.create({ credentials: new InMemoryCredentialStore(),
    modelsPath: null, modelsStorePath: join(base, 'models-cache.json'), refreshOnCreate: false });
  const faux = fauxProvider({ models: [{ id: 'fixture', reasoning: true }] });
  modelRuntime.registerNativeProvider(faux.provider);
  const { session: s } = await createAgentSession({ cwd, agentDir, resourceLoader, settingsManager, modelRuntime,
    model: faux.getModel(), thinkingLevel: 'low', sessionManager: SessionManager.inMemory(cwd), noTools: 'all' });
  await s.bindExtensions({ mode: 'rpc', uiContext: { notify: () => {}, setStatus: () => {} },
    abortHandler: () => { void s.abort(); }, onError: (error) => { throw error; } });
  const calls = [];
  faux.setResponses(Array.from({ length: 12 }, () => async (context) => {
    const last = context.messages.at(-1);
    const text = typeof last?.content === 'string' ? last.content : last?.content?.map((b) => b.text ?? '').join('\n');
    calls.push(text);
    return fauxAssistantMessage(respond(calls.length, text));
  }));
  t.after(() => {
    s.dispose();
    if (priorDir === undefined) delete process.env.PI_CODING_AGENT_DIR; else process.env.PI_CODING_AGENT_DIR = priorDir;
    if (priorMode === undefined) delete process.env.MEGAI_KEEP_GOING; else process.env.MEGAI_KEEP_GOING = priorMode;
    rmSync(base, { recursive: true, force: true });
  });
  return { s, calls };
}

test('native Pi: an announce-and-stop reply gets a real continuation', native, async (t) => {
  const { s, calls } = await session(t, (n) => (n === 1 ? 'I read the code. I will now implement the exporter.' : 'Implemented the exporter and its tests; all pass.'));
  await s.prompt('Add a CSV exporter');
  assert.equal(calls.length, 2);
  assert.match(calls[1], /\[megai keep-going 1\/3 · announce\]/);
  const custom = s.messages.filter((m) => m.role === 'custom' && m.customType === CUSTOM_TYPE);
  assert.equal(custom.length, 1);
});

test('native Pi: a model that keeps asking stops after the no-progress guard', native, async (t) => {
  const { s, calls } = await session(t, (n) => `Step ${n} looks ready. Shall I proceed with step ${n}?`);
  await s.prompt('Migrate the settings page');
  assert.equal(calls.length, 3); // prompt + two nudges, then two text-only answers in a row stop it
  assert.match(calls[2], /keep-going 2\/3 · ask\].*repeated stop/);
});

test('native Pi: a finished report and a question prompt get no nudge', native, async (t) => {
  const { s, calls } = await session(t, (n) => (n === 1 ? 'Delivered abc1234 to origin/dev; tests pass.' : 'Shall I explain more?'));
  await s.prompt('Fix the typo in the footer');
  await s.prompt('Why did the build fail?');
  assert.equal(calls.length, 2);
});

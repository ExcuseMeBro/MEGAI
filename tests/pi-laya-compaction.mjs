// Local Laya fast compaction through the real installer, Pi loader and stdio bridge.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

assert.ok(process.env.PI_PACKAGE_ROOT, 'Set PI_PACKAGE_ROOT to installed Pi');
const { DefaultResourceLoader } = await import(pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js')));
process.env.PI_OFFLINE = '1';
const ROOT = resolve('.');
const temp = mkdtempSync(join(tmpdir(), 'pi-laya-compaction-'));
const agent = join(temp, 'agent');
const fake = {
  calls: join(temp, 'calls.jsonl'), script: join(temp, 'script.jsonl'), routers: join(temp, 'routers.jsonl'),
};
const KEPT = ['LAYA_PYTHON', 'LAYA_LOG', 'LAYA_GATE', 'LAYA_FAKE_CALLS', 'LAYA_FAKE_SCRIPT',
  'LAYA_FAKE_ROUTERS', 'LAYA_FAKE_STALE_IDS', 'LAYA_FAKE_KEEP_P', 'LAYA_FAKE_STALE_P', 'PYTHONPATH'];
const savedEnv = Object.fromEntries(KEPT.map((name) => [name, process.env[name]]));
process.env.PYTHONPATH = resolve('tests/fixtures/laya_fake');
process.env.LAYA_PYTHON = 'python3';
process.env.LAYA_GATE = '0';
process.env.LAYA_LOG = join(temp, 'laya-calls.jsonl');
process.env.LAYA_FAKE_CALLS = fake.calls;
process.env.LAYA_FAKE_SCRIPT = fake.script;
process.env.LAYA_FAKE_ROUTERS = fake.routers;
process.env.LAYA_FAKE_KEEP_P = '0.95';
process.env.LAYA_FAKE_STALE_P = '0.05';

const lines = (path) => existsSync(path) ? readFileSync(path, 'utf8').split('\n').filter(Boolean) : [];
function install(...flags) {
  execFileSync('python3', ['-B', resolve('lib/pi_model_policy.py'), ...flags], {
    stdio: 'pipe',
    env: { ...process.env, HOME: temp, MEGAI_HOME: join(temp, 'megai'), MEGAI_SOURCE: ROOT,
      PI_CODING_AGENT_DIR: agent },
  });
  mkdirSync(agent, { recursive: true });
}
async function load() {
  process.env.PI_CODING_AGENT_DIR = agent;
  const loader = new DefaultResourceLoader({ cwd: temp, agentDir: agent });
  await loader.reload();
  const loaded = loader.getExtensions();
  assert.deepEqual(loaded.errors, []);
  return loaded.extensions;
}
const notices = [];
const ctx = { hasUI: false, mode: 'print', cwd: temp, isIdle: () => true, isProjectTrusted: () => false,
  abort() {}, getSystemPrompt: () => '', ui: { notify(message) { notices.push(message); } } };
const assistant = (text, toolCalls) => ({ role: 'assistant', content: [
  { type: 'text', text }, { type: 'thinking', thinking: 'private reasoning' },
  ...toolCalls.map(([id, name, args]) => ({ type: 'toolCall', id, name, arguments: args })),
] });
const result = (id, name, text) => ({ role: 'toolResult', toolCallId: id, toolName: name,
  content: [{ type: 'text', text }], isError: false });
const span = () => [
  { role: 'user', content: 'fix the parser bug' },
  assistant('reading it', [['a', 'read', { path: 'src/parser.ts' }]]),
  result('a', 'read', 'parser source, long and stale'),
  assistant('now the tests', [['b', 'bash', { command: 'pytest -q' }]]),
  result('b', 'bash', '3 passed'),
  assistant('patching', [['c', 'edit', { path: 'src/parser.ts' }]]),
  result('c', 'edit', 'patched one line'),
];
function compact(hook, { preparation = {}, ...event } = {}) {
  return hook({ type: 'session_before_compact', branchEntries: [], reason: 'threshold', willRetry: false,
    signal: new AbortController().signal, ...event, preparation: {
      firstKeptEntryId: 'entry-42', messagesToSummarize: span(), turnPrefixMessages: [], isSplitTurn: false,
      tokensBefore: 12_000, previousSummary: undefined,
      fileOps: { read: new Set(['old.ts']), written: new Set(), edited: new Set(['src/parser.ts']) },
      settings: { enabled: true, reserveTokens: 16_384, keepRecentTokens: 20_000 }, ...preparation,
    } }, ctx);
}

let extensions = [];
const shutdown = async () => {
  for (const extension of extensions) {
    for (const handler of extension.handlers.get('session_shutdown') ?? []) await handler({}, ctx);
  }
};
try {
  install();
  const retired = join(agent, 'extensions/megai-laya-compaction/index.ts');
  const installedHelper = join(agent, 'extensions/megai-laya/compaction.ts');
  assert.ok(!existsSync(retired), 'the retired second extension must not remain installed');
  assert.equal(readFileSync(installedHelper, 'utf8'), readFileSync(resolve('pi-skill/laya/compaction.ts'), 'utf8'));
  extensions = await load();
  const extension = extensions.find((item) => item.path.endsWith('extensions/megai-laya/index.ts'));
  assert.ok(extension, 'the active Laya extension must load through Pi');
  const hook = extension.handlers.get('session_before_compact')?.[0];
  assert.equal(typeof hook, 'function');

  process.env.LAYA_FAKE_STALE_IDS = 'call_1,result_1,result_2';
  const compacted = await compact(hook);
  assert.ok(compacted, notices.join('\n') || 'compaction unexpectedly deferred');
  const { summary, details } = compacted.compaction;
  assert.equal(compacted.compaction.firstKeptEntryId, 'entry-42');
  assert.equal(compacted.compaction.tokensBefore, 12_000);
  assert.match(summary, /\[User\]: fix the parser bug/);
  assert.match(summary, /\[Assistant tool calls\]: bash/);
  assert.match(summary, /bash — dropped as stale \(8 chars\)/);
  assert.match(summary, /edit\(\{"path":"src\/parser.ts"\}\)/);
  assert.match(summary, /patched one line/);
  assert.doesNotMatch(summary, /parser source|private reasoning/);
  assert.deepEqual(details.readFiles, ['old.ts']);
  assert.deepEqual(details.modifiedFiles, ['src/parser.ts']);
  assert.deepEqual({ ...details.laya, charsBefore: true, charsAfter: true, ms: true }, {
    calls: 3, kept: 1, resultsDropped: 1, callsDropped: 1, requests: 1, failed: 0,
    charsBefore: true, charsAfter: true, ms: true,
  });
  const first = JSON.parse(lines(fake.calls)[0]);
  assert.deepEqual(Object.keys(first.questions), ['call_1', 'result_1', 'call_2', 'result_2', 'call_3', 'result_3']);
  assert.equal(first.route, 'english');
  assert.ok(!summary.includes('fix the parser bug') || summary.includes('[User]'), 'input is only present as kept transcript');

  // Pi/Jiti loads extension modules without a module cache. A tool call after
  // compaction must still reuse the exact same runtime owner and Router process.
  const tools = new Map();
  for (const item of extensions) {
    for (const [name, tool] of item.tools) tools.set(name, tool.definition);
  }
  const laya = tools.get('laya');
  assert.ok(laya, 'the main extension must register the laya tool');
  const answered = JSON.parse((await laya.execute('shared-runtime', {
    state: 'one local runtime',
    questions: { same: { type: 'noul', instructions: 'Use the existing runtime?' } },
  }, undefined, undefined, ctx)).content[0].text);
  assert.equal(answered.ok, true);
  const routers = lines(fake.routers).map(JSON.parse);
  assert.equal(routers.length, 1, `tool and compaction created separate Routers: ${JSON.stringify(routers)}`);
  assert.equal(new Set(routers.map((row) => row.pid)).size, 1, 'one process owns tool and compaction');

  // Nothing stale defers to Pi's summarizer. The script file is read per call,
  // so this changes a warm child without reloading either model.
  const keepAll = Object.fromEntries(
    ['call_1', 'result_1', 'call_2', 'result_2', 'call_3', 'result_3']
      .map((id) => [id, { type: 'noul', noul: 0.95 }]),
  );
  writeFileSync(fake.script, JSON.stringify({ answers: keepAll }) + '\n');
  assert.equal(await compact(hook), undefined);

  // One failed local batch keeps everything and is never retried.
  writeFileSync(fake.script, JSON.stringify({ error: 'local inference failed' }) + '\n');
  assert.equal(await compact(hook), undefined);
  assert.equal(lines(fake.script).length, 0, 'the failing directive is consumed once');

  const beforeShortcuts = lines(fake.calls).length;
  assert.equal(await compact(hook, { reason: 'overflow' }), undefined);
  assert.equal(await compact(hook, { customInstructions: 'focus on the API' }), undefined);
  assert.equal(lines(fake.calls).length, beforeShortcuts, 'overflow/focused compaction makes no model call');

  // Nine calls batch as 4 + 4 + 1 because each asks two questions.
  const batchAnswers = (first, last) => ({ answers: Object.fromEntries(
    Array.from({ length: last - first + 1 }, (_, offset) => first + offset)
      .flatMap((id) => [
        [`call_${id}`, { type: 'noul', noul: 0.95 }],
        [`result_${id}`, { type: 'noul', noul: 0.05 }],
      ]),
  ) });
  writeFileSync(fake.script, [batchAnswers(1, 4), batchAnswers(5, 8), batchAnswers(9, 9)]
    .map(JSON.stringify).join('\n') + '\n');
  const many = [];
  for (let i = 0; i < 9; i += 1) {
    many.push(assistant(`step ${i}`, [[`c${i}`, 'read', { path: `${i}.ts` }]]));
    many.push(result(`c${i}`, 'read', `body ${i}`));
  }
  const big = await compact(hook, { preparation: { messagesToSummarize: many } });
  assert.equal(big.compaction.details.laya.calls, 9);
  assert.equal(big.compaction.details.laya.resultsDropped, 9);
  assert.equal(big.compaction.details.laya.requests, 3);
  assert.equal(big.compaction.summary.split('[Tool result]').length - 1, 9);

  const chained = await compact(hook, { preparation: { previousSummary: '## Earliest work\nolder detail' } });
  assert.match(chained.compaction.summary, /## Earliest work\nolder detail/);

  await shutdown();
  install('--remove');
  assert.ok(!existsSync(installedHelper));
  assert.ok(!existsSync(installedHelper));
  const ledger = readFileSync(process.env.LAYA_LOG, 'utf8');
  assert.ok(!ledger.includes('fix the parser bug'), 'the Laya ledger excludes transcript text');
  console.log('PASS: local Laya compaction keeps wanted transcript content, drops stale calls/results, batches '
    + 'eight questions, fails open, defers overflow and focused compaction, carries earlier summaries, and uses '
    + 'the active extension\'s single local bridge without a hosted service');
} finally {
  await shutdown();
  for (const [name, value] of Object.entries(savedEnv)) {
    if (value === undefined) delete process.env[name]; else process.env[name] = value;
  }
  rmSync(temp, { recursive: true, force: true });
}

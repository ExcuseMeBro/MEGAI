// The Jev fast compaction extension: installed by the real installer, loaded by the
// real Pi resource loader, and driven through its real `session_before_compact` hook.
// Offline — the TypeSafe endpoint is a local server and no provider or keychain is reachable.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createServer } from 'node:http';
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

assert.ok(process.env.PI_PACKAGE_ROOT, 'Set PI_PACKAGE_ROOT to installed Pi');
const { DefaultResourceLoader } = await import(pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js')));
process.env.PI_OFFLINE = '1';
const ROOT = resolve('.');
const temp = mkdtempSync(join(tmpdir(), 'pi-jev-compaction-'));
const agent = join(temp, 'agent');
const KEPT = ['TYPESAFE_API_KEY', 'TYPESAFE_ENDPOINT', 'TYPESAFE_TIMEOUT_MS'];
const savedEnv = Object.fromEntries(KEPT.map((name) => [name, process.env[name]]));
const path = process.env.PATH;

function install(...flags) {
  execFileSync('python3', ['-B', resolve('lib/pi_model_policy.py'), ...flags], {
    stdio: 'pipe',
    env: { ...process.env, HOME: temp, MEGAI_HOME: join(temp, 'megai'), MEGAI_SOURCE: ROOT, PI_CODING_AGENT_DIR: agent },
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

const ctx = {
  hasUI: false, mode: 'print', cwd: temp, isIdle: () => true, isProjectTrusted: () => false,
  abort() {}, getSystemPrompt: () => '', ui: { notify() {} },
};

/** The fake Jev: one `noul` probability per question id. Call 1 and its result are
 * stale enough to leave together, result 2 leaves with a note, everything else stays. */
const calls = [];
let answer = (id) => (id === 'call_1' || id === 'result_1' || id === 'result_2' ? 0.05 : 0.95);
let status = 200;
const server = createServer((request, response) => {
  let body = '';
  request.on('data', (chunk) => { body += chunk; });
  request.on('end', () => {
    calls.push({ url: request.url, authorization: request.headers.authorization, body: JSON.parse(body) });
    response.writeHead(status, { 'content-type': 'application/json' });
    if (status !== 200) return response.end(JSON.stringify({ error: 'upstream' }));
    const answers = {};
    for (const id of Object.keys(calls.at(-1).body.questions)) {
      assert.equal(calls.at(-1).body.questions[id].type, 'noul', 'every compaction question is a noul');
      answers[id] = { type: 'noul', noul: answer(id) };
    }
    response.end(JSON.stringify({ answers, model: 'jev-1.13.0', usage: { input_tokens: 40, output_tokens: 8 } }));
  });
});
await new Promise((ready) => server.listen(0, '127.0.0.1', ready));
const endpoint = `http://127.0.0.1:${server.address().port}/v1/systemone`;

const assistant = (text, toolCalls) => ({
  role: 'assistant',
  content: [
    { type: 'text', text },
    { type: 'thinking', thinking: 'private reasoning that must not be carried forward' },
    ...toolCalls.map(([id, name, args]) => ({ type: 'toolCall', id, name, arguments: args })),
  ],
});
const result = (id, name, text) => ({
  role: 'toolResult', toolCallId: id, toolName: name, content: [{ type: 'text', text }], isError: false,
});
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
  return hook({
    type: 'session_before_compact',
    branchEntries: [],
    reason: 'threshold',
    willRetry: false,
    signal: new AbortController().signal,
    ...event,
    preparation: {
      firstKeptEntryId: 'entry-42',
      messagesToSummarize: span(),
      turnPrefixMessages: [],
      isSplitTurn: false,
      tokensBefore: 12_000,
      previousSummary: undefined,
      fileOps: { read: new Set(['old.ts']), written: new Set(), edited: new Set(['src/parser.ts']) },
      settings: { enabled: true, reserveTokens: 16_384, keepRecentTokens: 20_000 },
      ...preparation,
    },
  }, ctx);
}

try {
  install();
  assert.equal(readFileSync(join(agent, 'extensions/megai-jev-compaction/index.ts'), 'utf8'),
    readFileSync(resolve('pi-skill/jev-compaction/index.ts'), 'utf8'),
    'the installer must place the extension byte for byte');
  const extensions = await load();
  const extension = extensions.find((item) => item.path.endsWith('extensions/megai-jev-compaction/index.ts'));
  assert.ok(extension, 'the installed extension must load through the real loader, relative import included');
  const hook = extension.handlers.get('session_before_compact')?.[0];
  assert.equal(typeof hook, 'function', 'the extension must register session_before_compact');

  process.env.TYPESAFE_API_KEY = 'synthetic-only';
  process.env.TYPESAFE_ENDPOINT = endpoint;

  const compacted = await compact(hook);
  const { summary, details } = compacted.compaction;
  assert.equal(compacted.compaction.firstKeptEntryId, 'entry-42');
  assert.equal(compacted.compaction.tokensBefore, 12_000);
  assert.match(summary, /\[User\]: fix the parser bug/, 'user text stays verbatim');
  assert.match(summary, /\[Assistant\]: now the tests/, 'assistant text stays verbatim');
  assert.match(summary, /\[Assistant tool calls\]: bash/, 'a call whose result is stale stays');
  assert.match(summary, /bash — dropped as stale \(8 chars\)/, 'a stale result leaves one line');
  assert.match(summary, /edit\(\{"path":"src\/parser.ts"\}\)/, 'a wanted call stays verbatim');
  assert.match(summary, /patched one line/, 'a wanted result stays verbatim');
  assert.doesNotMatch(summary, /parser source|private reasoning/, 'a dropped call takes its result and every thinking block is gone');
  assert.deepEqual(details, {
    readFiles: ['old.ts'],
    modifiedFiles: ['src/parser.ts'],
    jev: { calls: 3, kept: 1, resultsDropped: 1, callsDropped: 1, requests: 1, failed: 0,
      charsBefore: details.jev.charsBefore, charsAfter: summary.length, ms: details.jev.ms },
  });
  assert.ok(details.jev.charsBefore > 0 && Number.isFinite(details.jev.ms));

  // One request, two questions per call, exact request shape, key never echoed.
  assert.equal(calls.length, 1, 'three calls are one request');
  assert.equal(calls[0].url, '/v1/systemone');
  assert.equal(calls[0].authorization, 'Bearer synthetic-only');
  assert.equal(calls[0].body.model, 'jev-latest');
  assert.deepEqual(Object.keys(calls[0].body.questions), ['call_1', 'result_1', 'call_2', 'result_2', 'call_3', 'result_3']);
  assert.match(calls[0].body.questions.result_2.instructions, /output of tool call 2 \(bash, 8 chars\)/);
  assert.match(calls[0].body.state, /fix the parser bug/);
  assert.ok(!summary.includes('synthetic-only'));

  // Nothing stale, a Jev failure, no key, focus instructions and overflow recovery
  // all leave the summary to Pi's own summarizer.
  answer = () => 0.95;
  assert.equal(await compact(hook), undefined, 'nothing dropped must not replace the summary');
  assert.equal(calls.length, 2, 'a nothing-dropped cycle still asks once before deferring');
  answer = () => 0.05;
  status = 500;
  assert.equal(await compact(hook), undefined, 'a provider error keeps everything');
  status = 200;
  assert.equal(calls.length, 3, 'a failed batch is not retried');

  delete process.env.TYPESAFE_API_KEY;
  mkdirSync(join(temp, 'bin'), { recursive: true });
  writeFileSync(join(temp, 'bin/security'), '#!/bin/sh\nexit 44\n');
  chmodSync(join(temp, 'bin/security'), 0o755);
  process.env.PATH = join(temp, 'bin') + ':' + (path ?? '');
  assert.equal(await compact(hook), undefined, 'no key must not reach the network');
  process.env.PATH = path ?? '';
  process.env.TYPESAFE_API_KEY = 'synthetic-only';

  assert.equal(await compact(hook, { reason: 'overflow' }), undefined, 'overflow recovery must stay with Pi');
  assert.equal(await compact(hook, { customInstructions: 'focus on the API' }), undefined, 'focus instructions must stay with Pi');

  // Batches: two questions per call, at most eight per request.
  const many = [];
  for (let index = 0; index < 9; index += 1) {
    many.push(assistant(`step ${index}`, [[`c${index}`, 'read', { path: `${index}.ts` }]]));
    many.push(result(`c${index}`, 'read', `body ${index}`));
  }
  answer = (id) => (id.startsWith('result_') ? 0.05 : 0.95);
  const big = await compact(hook, { preparation: { messagesToSummarize: many } });
  assert.equal(big.compaction.details.jev.calls, 9);
  assert.equal(big.compaction.details.jev.resultsDropped, 9);
  assert.equal(big.compaction.details.jev.requests, 3, 'nine calls are 4 + 4 + 1 per request');
  assert.equal(big.compaction.summary.split('[Tool result]').length - 1, 9);

  // A wanted result larger than the budget keeps a bounded head and says so.
  answer = (id) => (id === 'call_1' || id === 'result_1' ? 0.05 : 0.95);
  const large = await compact(hook, {
    preparation: {
      messagesToSummarize: [
        assistant('reading', [['a', 'read', { path: '1.ts' }], ['c', 'read', { path: '2.ts' }]]),
        result('a', 'read', 'stale body'),
        result('c', 'read', 'y'.repeat(5_000)),
      ],
    },
  });
  assert.match(large.compaction.summary, /\[1000 chars not kept; re-run the tool if they matter\]/);
  assert.ok(large.compaction.summary.length < 4_400, 'the kept result is capped');

  // The previous summary is carried into the new one, so an older cycle survives.
  const chained = await compact(hook, { preparation: { previousSummary: '## Earliest work\nolder detail' } });
  assert.match(chained.compaction.summary, /## Earliest work\nolder detail/);

  install('--remove');
  assert.ok(!existsSync(join(agent, 'extensions/megai-jev-compaction/index.ts')), 'the installer must remove its own asset');
  console.log('PASS: real installer and Pi loader; Jev fast compaction keeps text, calls and wanted results verbatim, '
    + 'drops stale ones through the hook, batches 8 questions per request, and every missing-key, provider-error, '
    + 'nothing-dropped, focus-instruction and overflow path leaves the summary to Pi');
} finally {
  server.close();
  for (const [name, value] of Object.entries(savedEnv)) {
    if (value === undefined) delete process.env[name];
    else process.env[name] = value;
  }
  if (path !== undefined) process.env.PATH = path;
  rmSync(temp, { recursive: true, force: true });
}

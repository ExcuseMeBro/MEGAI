// The Jev throttling retry: a scripted 429/529 sequence recovers, a persistent
// throttle stays bounded, and every other failure remains a single attempt.
// Offline — the endpoint is a local server and no provider, keychain or TypeSafe
// call is reachable. Key handling and the tool-call gate stay in tests/pi-jev.mjs.
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
const temp = mkdtempSync(join(tmpdir(), 'pi-jev-retry-'));
const agent = join(temp, 'agent');
const KEPT = ['TYPESAFE_API_KEY', 'TYPESAFE_ENDPOINT', 'TYPESAFE_TIMEOUT_MS',
  'JEV_GATE_TIMEOUT_MS', 'JEV_GATE', 'JEV_GATE_BLOCK'];
const savedEnv = Object.fromEntries(KEPT.map((name) => [name, process.env[name]]));
// A short deadline keeps the timeout case fast; the extension reads it at load.
process.env.TYPESAFE_TIMEOUT_MS = '150';
process.env.JEV_GATE_TIMEOUT_MS = '150';

const questions = {
  task_type: { type: 'choice', instructions: 'Which type?', criteria: { bug: 'a defect', chore: null } },
};
const OK = {
  model: 'jev-1.13.0',
  usage: { input_tokens: 700, output_tokens: 40 },
  answers: { task_type: { choice: 'bug', probabilities: { bug: 0.91 }, confidence: 0.91 } },
};
const throttled = (status) => ({ status, body: { error: 'throttled' } });

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

const calls = [];
let script = [];
let held = null;
let path = process.env.PATH;
function send(response, data) {
  try {
    response.writeHead(data.status ?? 200, { 'content-type': 'application/json' });
    response.end(data.raw ?? JSON.stringify(data.body ?? {}));
  } catch { /* the caller may already have cancelled the request */ }
}
const server = createServer((request, response) => {
  let body = '';
  request.on('data', (chunk) => { body += chunk; });
  request.on('end', () => {
    calls.push({ url: request.url, authorization: request.headers.authorization, body: JSON.parse(body) });
    const next = script.shift() ?? { status: 200, body: OK };
    if (next.hold) held = () => send(response, next);
    else if (next.delayMs) setTimeout(() => send(response, next), next.delayMs);
    else send(response, next);
  });
});
await new Promise((ready) => server.listen(0, '127.0.0.1', ready));
const endpoint = `http://127.0.0.1:${server.address().port}/v1/systemone`;

function read(result) {
  return JSON.parse(result.content[0].text);
}

try {
  install();
  const installed = join(agent, 'extensions/megai-jev/index.ts');
  assert.equal(readFileSync(installed, 'utf8'), readFileSync(resolve('pi-skill/jev/index.ts'), 'utf8'));
  const extensions = await load();
  const tools = new Map();
  for (const extension of extensions) {
    for (const [name, tool] of extension.tools) tools.set(name, tool.definition);
  }
  const jev = tools.get('jev');
  assert.ok(jev, 'the installed extension must register the jev tool');

  mkdirSync(join(temp, 'bin'), { recursive: true });
  writeFileSync(join(temp, 'bin/security'), '#!/bin/sh\nexit 44\n');
  chmodSync(join(temp, 'bin/security'), 0o755);
  process.env.PATH = join(temp, 'bin') + ':' + (path ?? '');
  process.env.TYPESAFE_API_KEY = 'synthetic-only';
  process.env.TYPESAFE_ENDPOINT = endpoint;
  const called = (state) => jev.execute('retry', { state, questions }, undefined, undefined, ctx);

  // Two throttles then a success: the call recovers, and the two backoff waits
  // (0.5 s then 1 s) are spent rather than skipped.
  script = [throttled(429), throttled(429)];
  let before = calls.length;
  const started = Date.now();
  const recovered = read(await called('fix the flaky test'));
  const waited = Date.now() - started;
  assert.equal(calls.length, before + 3, '429, 429, 200 must be exactly three attempts');
  assert.equal(recovered.ok, true);
  assert.equal(recovered.answers.task_type.choice, 'bug');
  assert.ok(waited >= 1400, `the backoff must be observable as elapsed time (saw ${waited} ms)`);

  // A persistent throttle stays bounded: the first attempt plus two retries, then
  // the ordinary ok:false the caller already handles.
  script = [throttled(429), throttled(429), throttled(429), throttled(429)];
  before = calls.length;
  const exhausted = read(await called('fix the flaky test'));
  assert.equal(calls.length, before + 3, 'a persistent 429 stops after the first attempt plus two retries');
  assert.equal(exhausted.ok, false);
  assert.match(exhausted.error, /HTTP 429/);
  assert.ok(!exhausted.error.includes('synthetic-only'));

  // 529 means overloaded and is throttling too: one retry recovers it.
  script = [throttled(529)];
  before = calls.length;
  const overloaded = read(await called('fix the flaky test'));
  assert.equal(calls.length, before + 2, 'a 529 must be retried once');
  assert.equal(overloaded.ok, true);

  // Anything else is a real failure and stays exactly one attempt.
  script = [throttled(500)];
  before = calls.length;
  const broken = read(await called('fix the flaky test'));
  assert.equal(calls.length, before + 1, 'a 500 must not be retried');
  assert.match(broken.error, /HTTP 500/);

  script = [{ status: 200, raw: 'not json at all' }];
  before = calls.length;
  const nonJson = read(await called('fix the flaky test'));
  assert.equal(calls.length, before + 1, 'a malformed body must not be retried');
  assert.match(nonJson.error, /was not JSON/);

  // A slower-than-deadline reply is a timeout, not throttling, and is not retried.
  script = [{ delayMs: 400, body: OK }];
  before = calls.length;
  const timedOut = read(await called('fix the flaky test'));
  assert.equal(timedOut.ok, false);
  assert.equal(timedOut.error, 'Jev call timed out or was cancelled');
  assert.equal(calls.length, before + 1, 'a timed-out call must not be retried');
  await new Promise((tick) => setTimeout(tick, 400));

  // A caller cancellation during a backoff wait stops the retry instead of
  // delaying the abort the tool and the gate both depend on.
  script = [{ ...throttled(429), hold: true }, { status: 200, body: OK }];
  before = calls.length;
  const controller = new AbortController();
  const pending = jev.execute('retry', { state: 'fix the flaky test', questions }, controller.signal, undefined, ctx);
  for (let spin = 0; spin < 400 && calls.length === before; spin += 1) {
    await new Promise((tick) => setTimeout(tick, 5));
  }
  controller.abort();
  held?.();
  held = null;
  const cancelled = read(await pending);
  assert.equal(cancelled.ok, false);
  assert.equal(cancelled.error, 'Jev call timed out or was cancelled');
  assert.equal(calls.length, before + 1, 'a cancelled call must not be retried');

  process.env.PATH = path ?? '';
  install('--remove');
  assert.ok(!existsSync(installed), 'the installer must remove its own asset');
  console.log('PASS: the Jev tool retries HTTP 429 and 529 with an observable exponential backoff, recovers a '
    + 'throttled burst, stays bounded on a persistent throttle, and keeps 500, malformed-body, timeout and '
    + 'cancellation paths at exactly one attempt');
} finally {
  server.close();
  for (const [name, value] of Object.entries(savedEnv)) {
    if (value === undefined) delete process.env[name];
    else process.env[name] = value;
  }
  if (path !== undefined) process.env.PATH = path;
  rmSync(temp, { recursive: true, force: true });
}

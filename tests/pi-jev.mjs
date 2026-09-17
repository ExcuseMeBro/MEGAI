// The Jev decision tool: installed by the real installer, loaded by the real Pi
// resource loader, and fail-open. Offline — the endpoint is a local server and no
// provider, keychain or TypeSafe call is reachable.
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
const temp = mkdtempSync(join(tmpdir(), 'pi-jev-'));
const agent = join(temp, 'agent');
const KEPT = ['TYPESAFE_API_KEY', 'TYPESAFE_ENDPOINT', 'TYPESAFE_TIMEOUT_MS'];
const savedEnv = Object.fromEntries(KEPT.map((name) => [name, process.env[name]]));
// A short deadline keeps the timeout case fast; the extension reads it at load.
process.env.TYPESAFE_TIMEOUT_MS = '150';

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
let reply = null;
let held = null;
let path = process.env.PATH;
function send(response, data) {
  try {
    response.writeHead(data.status ?? 200, { 'content-type': 'application/json' });
    response.end(data.raw ?? JSON.stringify(data.body));
  } catch { /* the caller may already have cancelled the request */ }
}
const server = createServer((request, response) => {
  let body = '';
  request.on('data', (chunk) => { body += chunk; });
  request.on('end', () => {
    calls.push({ url: request.url, authorization: request.headers.authorization, body: JSON.parse(body) });
    if (reply) {
      if (reply.hold) held = () => send(response, reply);
      else if (reply.delayMs) setTimeout(() => send(response, reply), reply.delayMs);
      else send(response, reply);
      return;
    }
    response.writeHead(200, { 'content-type': 'application/json' });
    response.end(JSON.stringify({
      model: 'jev-1.13.0',
      usage: { input_tokens: 700, output_tokens: 40 },
      answers: {
        task_type: { choice: 'bug', probabilities: { bug: 0.91 }, confidence: 0.91 },
        effort: { score: 0.9, probabilities: [0.2, 0.7], confidence: 0.7 },
        needs_approval: { noul: 0.04 },
      },
    }));
  });
});
await new Promise((ready) => server.listen(0, '127.0.0.1', ready));
const endpoint = `http://127.0.0.1:${server.address().port}/v1/systemone`;

const questions = {
  task_type: { type: 'choice', instructions: 'Which type?', criteria: { bug: 'a defect', chore: null } },
  effort: { type: 'score', instructions: 'How much of the repo?', criteria: ['one file', 'few files'] },
  needs_approval: { type: 'noul', instructions: 'Is this reserved?', criteria: { true: 'push to main', false: 'ordinary change' } },
};

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

  // No key and no reachable keychain: fail open, and never touch the network.
  mkdirSync(join(temp, 'bin'), { recursive: true });
  writeFileSync(join(temp, 'bin/security'), '#!/bin/sh\nexit 44\n');
  chmodSync(join(temp, 'bin/security'), 0o755);
  process.env.PATH = join(temp, 'bin') + ':' + (path ?? '');
  delete process.env.TYPESAFE_API_KEY;
  delete process.env.TYPESAFE_ENDPOINT;
  const missing = read(await jev.execute('call-1', { state: 'fix the flaky test', questions }, undefined, undefined, ctx));
  assert.equal(missing.ok, false);
  assert.match(missing.error, /no TypeSafe key/);
  assert.match(missing.guidance, /do not retry in a loop/);
  assert.equal(calls.length, 0, 'a missing key must not reach the network');
  process.env.PATH = path ?? '';

  // A missing key asks the user once when a dialog is available, keeps the answer
  // in memory for the session, and never echoes it; a cancel means no key.
  process.env.TYPESAFE_ENDPOINT = endpoint;
  const declined = { ...ctx, hasUI: true, ui: { notify() {}, input: async () => undefined } };
  const cancelledKey = read(await jev.execute('call-2', { state: 'fix the flaky test', questions }, undefined, undefined, declined));
  assert.equal(cancelledKey.ok, false);
  assert.match(cancelledKey.error, /no TypeSafe key/);
  assert.equal(calls.length, 0, 'a declined dialog must not reach the network');
  const asked = [];
  const dialog = { ...ctx, hasUI: true, ui: { notify() {}, input: async (title) => { asked.push(title); return 'typed-key'; } } };
  const prompted = await jev.execute('call-3', { state: 'fix the flaky test', questions }, undefined, undefined, dialog);
  assert.equal(asked.length, 1, 'a missing key must ask exactly once');
  assert.match(asked[0], /TypeSafe API key/);
  assert.equal(read(prompted).ok, true);
  assert.equal(calls.length, 1, 'the entered key must be used for the call');
  assert.equal(calls.at(-1).authorization, 'Bearer typed-key');
  assert.ok(!prompted.content[0].text.includes('typed-key'), 'the entered key must never be echoed');

  // Malformed questions are rejected before any request.
  process.env.TYPESAFE_API_KEY = 'synthetic-only';
  const beforeInvalid = calls.length;
  const invalid = read(await jev.execute('call-4', {
    state: 'fix the flaky test',
    questions: { ...questions, effort: { type: 'score', instructions: 'How much?', criteria: [] } },
  }, undefined, undefined, ctx));
  assert.equal(invalid.ok, false);
  assert.match(invalid.error, /invalid criteria for "effort"/);
  assert.equal(calls.length, beforeInvalid, 'invalid questions must not reach the network');

  // A real call: exact request shape, answers passed through, key never echoed.
  const result = await jev.execute('call-5', { state: 'fix the flaky test', questions }, undefined, undefined, ctx);
  assert.equal(calls.length, beforeInvalid + 1);
  assert.equal(calls[beforeInvalid].url, '/v1/systemone');
  assert.equal(calls[beforeInvalid].authorization, 'Bearer synthetic-only');
  assert.deepEqual(calls[beforeInvalid].body, { state: 'fix the flaky test', model: 'jev-latest', questions });
  assert.equal(read(result).ok, true);
  assert.equal(read(result).answers.needs_approval.noul, 0.04);
  assert.equal(read(result).model, 'jev-1.13.0');
  assert.ok(!result.content[0].text.includes('synthetic-only'), 'the key must never appear in tool output');

  // A provider error is a bounded, key-free failure.
  reply = { status: 500, body: { error: 'upstream' } };
  const broken = read(await jev.execute('call-4', { state: 'fix the flaky test', questions }, undefined, undefined, ctx));
  assert.equal(broken.ok, false);
  assert.match(broken.error, /HTTP 500/);
  assert.ok(!broken.error.includes('synthetic-only'));

  // Every other failure shape stays a bounded, key-free ok:false.
  reply = { status: 200, raw: 'not json at all' };
  const nonJson = read(await jev.execute('call-5', { state: 'fix the flaky test', questions }, undefined, undefined, ctx));
  assert.equal(nonJson.ok, false);
  assert.match(nonJson.error, /was not JSON/);
  reply = { status: 200, body: { model: 'jev-1.13.0' } };
  const noAnswers = read(await jev.execute('call-6', { state: 'fix the flaky test', questions }, undefined, undefined, ctx));
  assert.equal(noAnswers.ok, false);
  assert.match(noAnswers.error, /carried no answers/);
  reply = { status: 200, raw: JSON.stringify({ answers: { padding: 'x'.repeat(300_000) } }) };
  const oversized = read(await jev.execute('call-7', { state: 'fix the flaky test', questions }, undefined, undefined, ctx));
  assert.equal(oversized.ok, false);
  assert.equal(oversized.error, 'Jev response too large');

  // A caller-cancelled call is reported as cancellation after exactly one request.
  reply = { hold: true, body: { answers: { task_type: { choice: 'bug' } } } };
  const heldStart = calls.length;
  const controller = new AbortController();
  const pending = jev.execute('call-8', { state: 'fix the flaky test', questions }, controller.signal, undefined, ctx);
  for (let spin = 0; spin < 400 && calls.length === heldStart; spin += 1) {
    await new Promise((tick) => setTimeout(tick, 5));
  }
  controller.abort();
  const cancelledCall = read(await pending);
  assert.equal(cancelledCall.ok, false);
  assert.equal(cancelledCall.error, 'Jev call timed out or was cancelled');
  assert.equal(calls.length, heldStart + 1, 'a cancelled call must not be retried');
  held?.();

  // The deadline is bounded: a 400 ms reply against the 150 ms timeout is reported
  // instead of awaited, and never retried.
  reply = { delayMs: 400, body: { answers: { task_type: { choice: 'bug' } } } };
  const slowStart = calls.length;
  const timedOut = read(await jev.execute('call-9', { state: 'fix the flaky test', questions }, undefined, undefined, ctx));
  assert.equal(timedOut.ok, false);
  assert.equal(timedOut.error, 'Jev call timed out or was cancelled');
  assert.ok(calls.length <= slowStart + 1, 'a timed-out call must not be retried');
  await new Promise((tick) => setTimeout(tick, 400));
  reply = null;

  install('--remove');
  assert.ok(!existsSync(installed), 'the installer must remove its own asset');
  console.log('PASS: real installer and Pi loader; jev tool registered, request shape exact, key never leaked, the '
    + 'missing key asks the user once and honours a decline, and invalid-question, HTTP-error, non-JSON, no-answers, '
    + 'oversized-body, cancelled and timed-out paths all fail open without retrying or touching the network');
} finally {
  server.close();
  for (const [name, value] of Object.entries(savedEnv)) {
    if (value === undefined) delete process.env[name];
    else process.env[name] = value;
  }
  if (path !== undefined) process.env.PATH = path;
  rmSync(temp, { recursive: true, force: true });
}

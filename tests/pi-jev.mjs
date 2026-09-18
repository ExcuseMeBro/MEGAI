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
const KEPT = ['TYPESAFE_API_KEY', 'TYPESAFE_ENDPOINT', 'TYPESAFE_TIMEOUT_MS', 'JEV_GATE_TIMEOUT_MS',
  'JEV_GATE', 'JEV_GATE_BLOCK'];
const savedEnv = Object.fromEntries(KEPT.map((name) => [name, process.env[name]]));
// A short deadline keeps the timeout case fast; the extension reads it at load.
process.env.TYPESAFE_TIMEOUT_MS = '150';
process.env.JEV_GATE_TIMEOUT_MS = '150';

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
  const gate = extensions.find((item) => item.path.endsWith('extensions/megai-jev/index.ts'))
    .handlers.get('tool_call')?.[0];
  assert.equal(typeof gate, 'function', 'the extension must register the tool_call gate');

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

  // The live API takes an ordered level list for `score` and a label→meaning map
  // for `choice`/`noul`; the other accepted shape is normalized before the request.
  const shape = read(await jev.execute('call-shape', {
    state: 'fix the flaky test',
    questions: {
      task_type: { type: 'choice', instructions: 'Which type?', criteria: ['bug', 'chore'] },
      effort: { type: 'score', instructions: 'How much?', criteria: { one: 'one file', few: 'few files' } },
      needs_approval: { type: 'noul', instructions: 'Is this reserved?', criteria: ['no', 'yes'] },
    },
  }, undefined, undefined, ctx));
  assert.equal(shape.ok, true);
  assert.equal(calls.length, beforeInvalid + 1);
  assert.deepEqual(calls.at(-1).body.questions, {
    task_type: { type: 'choice', instructions: 'Which type?', criteria: { bug: null, chore: null } },
    effort: { type: 'score', instructions: 'How much?', criteria: ['one', 'few'] },
    needs_approval: { type: 'noul', instructions: 'Is this reserved?', criteria: { no: null, yes: null } },
  });
  // Criteria the API requires are never sent missing.
  const noCriteria = read(await jev.execute('call-shape-2', {
    state: 'fix the flaky test',
    questions: { task_type: { type: 'choice', instructions: 'Which type?' } },
  }, undefined, undefined, ctx));
  assert.equal(noCriteria.ok, false);
  assert.match(noCriteria.error, /criteria required for "task_type"/);
  assert.equal(calls.length, beforeInvalid + 1, 'a question missing required criteria must not reach the network');

  // A real call: exact request shape, answers passed through, key never echoed.
  const beforeReal = calls.length;
  const result = await jev.execute('call-5', { state: 'fix the flaky test', questions }, undefined, undefined, ctx);
  assert.equal(calls.length, beforeReal + 1);
  assert.equal(calls[beforeReal].url, '/v1/systemone');
  assert.equal(calls[beforeReal].authorization, 'Bearer synthetic-only');
  assert.deepEqual(calls[beforeReal].body, { state: 'fix the flaky test', model: 'jev-latest', questions });
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

  // The gate: one Jev judgment per tool call the model emits — `mcp`, `mcpScript`,
  // built-ins, all of them — before the tool runs. A strong objection blocks it once,
  // and every failure lets the call through untouched.
  delete process.env.JEV_GATE;
  delete process.env.JEV_GATE_BLOCK;
  const noticed = [];
  const gating = {
    ...ctx,
    cwd: '/repo',
    sessionManager: { getBranch: () => [
      { type: 'message', message: { role: 'user', content: 'fix the flaky parser test' } },
      { type: 'message', message: { role: 'assistant', content: [{ type: 'text', text: 'reading it' }] } },
    ] },
    ui: { notify: (text, level) => noticed.push([text, level]) },
  };
  const judged = (name, input) => gate({ toolName: name, toolCallId: 't1', input }, gating);
  const answering = (object) => ({
    body: { answers: { object: { type: 'noul', noul: object } } },
  });

  reply = answering(0.05);
  let before = calls.length;
  assert.equal(await judged('mcp', { tool: 'plane_workitem', args: { action: 'list' } }), undefined,
    'a call Jev does not object to runs');
  assert.equal(calls.length, before + 1, 'exactly one request per tool call');
  assert.equal(calls.at(-1).url, '/v1/systemone');
  assert.equal(calls.at(-1).authorization, 'Bearer synthetic-only');
  assert.equal(calls.at(-1).body.model, 'jev-latest');
  assert.deepEqual(Object.keys(calls.at(-1).body.questions), ['object'], 'one question per call');
  assert.equal(calls.at(-1).body.questions.object.type, 'noul');
  assert.match(calls.at(-1).body.questions.object.instructions, /must not run as written/);
  assert.match(calls.at(-1).body.state, /fix the flaky parser test/, 'the judgment carries the goal');
  assert.match(calls.at(-1).body.state, /Tool call: mcp\(\{"tool":"plane_workitem"/, 'and the call itself');
  assert.equal(noticed.length, 0, 'a call Jev does not object to is silent');

  // Below the block threshold nothing is reported: the gate used to warn on an
  // `advance` below 0.4, which flagged a third of all real calls.
  reply = answering(0.64);
  assert.equal(await judged('read', { path: 'a.ts' }), undefined);
  assert.equal(noticed.length, 0, 'a soft objection runs silently');

  // A strong objection blocks once, with the reason. The identical retry runs, so a
  // Jev answer can never deadlock work the model is certain about.
  reply = answering(0.9);
  const blocked = await judged('bash', { command: 'rm -rf src' });
  assert.equal(blocked.block, true);
  assert.match(blocked.reason, /this bash call must not run as written \(objection 0\.9\)/);
  assert.match(blocked.reason, /Repeated unchanged, it runs/);
  assert.equal(noticed.length, 0, 'the block is its own report');
  assert.equal(await judged('bash', { command: 'rm -rf src' }), undefined,
    'a repeated identical call must run rather than deadlock');
  assert.equal(noticed.length, 1, 'the retry is reported and runs');
  assert.match(noticed.at(-1)[0], /objection 0\.9.*Running it unchanged/);

  // The threshold is the measured one, not an old 0.7: 0.6 passes, 0.66 blocks.
  reply = answering(0.6);
  assert.equal(await judged('edit', { path: 'a.ts', edits: [] }), undefined, '0.6 does not block');
  reply = answering(0.66);
  assert.equal((await judged('edit', { path: 'a.ts', edits: [] })).block, true,
    'the block threshold is 0.65');

  // The boundary is exact and inclusive: 0.649 passes, exactly 0.65 blocks.
  reply = answering(0.649);
  assert.equal(await judged('grep', { pattern: 'x' }), undefined, '0.649 does not block');
  reply = answering(0.65);
  assert.equal((await judged('grep', { pattern: 'x' })).block, true, 'exactly 0.65 blocks');

  // JEV_GATE_BLOCK=0 keeps the judgment and drops the block.
  reply = answering(0.95);
  process.env.JEV_GATE_BLOCK = '0';
  assert.equal(await judged('write', { path: 'a.ts', content: 'x' }), undefined);
  assert.match(noticed.at(-1)[0], /objection 0\.95.*Running it unchanged/);
  delete process.env.JEV_GATE_BLOCK;

  // A failed or unanswered judgment is not a verdict, and is not retried.
  reply = { status: 500, body: { error: 'upstream' } };
  before = calls.length;
  assert.equal(await judged('bash', { command: 'ls' }), undefined, 'a failed judgment must not block the call');
  assert.equal(calls.length, before + 1, 'a failed judgment is not retried');
  assert.equal(noticed.length, 2, 'a failure is not a verdict');
  reply = { delayMs: 400, body: answering(0.9).body };
  before = calls.length;
  assert.equal(await judged('edit', { path: 'a.ts' }), undefined,
    'a judgement slower than the gate deadline must fail open');
  assert.ok(calls.length <= before + 1, 'a timed-out judgment is not retried');
  assert.equal(noticed.length, 2);
  await new Promise((tick) => setTimeout(tick, 400));
  reply = null;

  // JEV_GATE=0, the `jev` tool itself and a missing key never reach the network.
  before = calls.length;
  process.env.JEV_GATE = '0';
  assert.equal(await judged('read', { path: 'a.ts' }), undefined);
  delete process.env.JEV_GATE;
  assert.equal(await judged('jev', { state: 'x', questions }), undefined, 'the gate must not judge itself');
  assert.equal(calls.length, before, 'a switched-off or self call sends nothing');
  const environment = process.env.TYPESAFE_API_KEY;
  delete process.env.TYPESAFE_API_KEY;
  assert.equal(await judged('read', { path: 'a.ts' }), undefined);
  assert.equal(calls.at(-1).authorization, 'Bearer typed-key',
    'the gate shares the session key the tool asked for');
  process.env.TYPESAFE_API_KEY = environment;

  // A session the extension cannot read is still judged, just without a goal.
  before = calls.length;
  assert.equal(await gate({ toolName: 'read', toolCallId: 't2', input: { path: 'a.ts' } }, ctx), undefined);
  assert.equal(calls.length, before + 1);
  assert.doesNotMatch(calls.at(-1).body.state, /What the session is working on/);
  assert.match(calls.at(-1).body.state, /Tool call: read\(\{"path":"a.ts"\}\)/);
  reply = null;

  // The route question: the gate offers the skills and MCP tools Pi already loaded,
  // and blocks once when a cheap model's Jev pick is a better next move than the call.
  const jevExtension = extensions.find((item) => item.path.endsWith('extensions/megai-jev/index.ts'));
  const routeCatalog = jevExtension.handlers.get('before_agent_start')?.[0];
  assert.equal(typeof routeCatalog, 'function', 'the extension must cache the routing catalog');
  const routing = (choice, probability, object = 0.05) => ({
    body: { answers: {
      object: { type: 'noul', noul: object },
      route: { choice, probabilities: { [choice]: probability }, confidence: probability },
    } },
  });

  delete process.env.JEV_ROUTE;
  routeCatalog({
    systemPromptOptions: {
      skills: [
        { name: 'megai', description: 'focused verification for a flaky test' },
        { name: 'ponytail', description: 'laziest solution for any coding task' },
      ],
      toolSnippets: { mcp: 'MCP gateway: install, status, search, describe, auth', bash: 'run a shell command' },
    },
  }, gating);

  // An on-topic skill pick rides the existing request and blocks once with the move to
  // make; the identical retry runs, so a route pick can never deadlock the work.
  reply = routing('skill:megai', 0.83);
  before = calls.length;
  let seen = noticed.length;
  const routeBlocked = await judged('bash', { command: 'node tools/run-flaky.mjs' });
  assert.equal(calls.length, before + 1, 'routing must not add a second request');
  assert.deepEqual(Object.keys(calls.at(-1).body.questions), ['object', 'route']);
  assert.equal(calls.at(-1).body.questions.route.type, 'choice');
  assert.equal(calls.at(-1).body.questions.route.criteria.as_written, 'run this exact bash call as written');
  assert.match(calls.at(-1).body.questions.route.criteria['skill:megai'], /flaky test/);
  assert.equal(calls.at(-1).body.questions.route.criteria['skill:ponytail'], undefined,
    'an unrelated catalog entry is not offered');
  assert.equal(calls.at(-1).body.questions.route.criteria['tool:mcp'], undefined,
    'an unrelated MCP tool is not offered');
  assert.match(calls.at(-1).body.state, /- skill:megai: focused verification for a flaky test/);
  assert.equal(routeBlocked.block, true);
  assert.match(routeBlocked.reason, /Jev route: load skill "megai" before repeating this bash call \(route 0\.83\)/);
  assert.match(routeBlocked.reason, /Repeated unchanged, it runs/);
  assert.equal(noticed.length, seen, 'a route block is its own report');
  assert.equal(await judged('bash', { command: 'node tools/run-flaky.mjs' }), undefined,
    'a repeated identical call must run rather than deadlock');
  assert.equal(noticed.length, seen, 'the route retry is silent');

  // `as_written` needs no action, a pick below the route threshold is not worth a round
  // trip, and a strong objection still wins over a route pick.
  reply = routing('as_written', 0.95);
  before = calls.length;
  seen = noticed.length;
  assert.equal(await judged('bash', { command: 'node tools/run-flaky.mjs 2' }), undefined,
    'the call as written runs');
  assert.ok(Object.keys(calls.at(-1).body.questions).includes('route'), 'the question is still asked');
  reply = routing('skill:megai', 0.69);
  assert.equal(await judged('bash', { command: 'node tools/run-flaky.mjs 3' }), undefined,
    '0.69 does not block');
  reply = routing('skill:megai', 0.7, 0.9);
  const objectionFirst = await judged('bash', { command: 'node tools/run-flaky.mjs 4' });
  assert.match(objectionFirst.reason, /must not run as written \(objection 0\.9\)/,
    'a strong objection is reported before the route');
  assert.equal(noticed.length, seen, 'neither the weak pick nor the objection block reports');

  // A missing route answer, JEV_ROUTE=0 and JEV_GATE_BLOCK=0 all leave the call alone.
  reply = { body: { answers: { object: { type: 'noul', noul: 0.05 } } } };
  assert.equal(await judged('bash', { command: 'node tools/run-flaky.mjs 5' }), undefined,
    'an unanswered route must not block');
  reply = routing('skill:megai', 0.99);
  process.env.JEV_ROUTE = '0';
  before = calls.length;
  assert.equal(await judged('bash', { command: 'node tools/run-flaky.mjs 6' }), undefined);
  assert.deepEqual(Object.keys(calls.at(-1).body.questions), ['object'],
    'JEV_ROUTE=0 asks the objection question only');
  assert.doesNotMatch(calls.at(-1).body.state, /could use instead/);
  delete process.env.JEV_ROUTE;
  seen = noticed.length;
  process.env.JEV_GATE_BLOCK = '0';
  assert.equal(await judged('bash', { command: 'node tools/run-flaky.mjs 7' }), undefined,
    'JEV_GATE_BLOCK=0 keeps the route advice and drops the block');
  assert.equal(noticed.length, seen + 1);
  assert.match(noticed.at(-1)[0], /Jev route: load skill "megai".*Re-check it against the request/);
  delete process.env.JEV_GATE_BLOCK;

  // The MCP half of the catalog: an on-topic gateway tool is offered for a discovery
  // call, and picked it routes the model there instead.
  const discovery = {
    ...gating,
    sessionManager: { getBranch: () => [
      { type: 'message', message: { role: 'user', content: 'find the code that builds the parser report' } },
    ] },
  };
  routeCatalog({
    systemPromptOptions: {
      skills: [],
      toolSnippets: {
        'mcp__graft': 'code discovery: find code and trace callers through the lazy graft server',
        mcp: 'MCP gateway: install, status, search, describe, auth',
        bash: 'run a shell command',
      },
    },
  }, discovery);
  reply = routing('tool:mcp__graft', 0.78);
  const mcpBlocked = await gate({ toolName: 'bash', toolCallId: 't3', input: { command: 'rg parser' } }, discovery);
  assert.equal(mcpBlocked.block, true);
  assert.match(mcpBlocked.reason,
    /Jev route: use the installed MCP tool "mcp__graft" before repeating this bash call/);

  // The catalog caps what is offered: 20 on-topic skills still fit the API limit.
  routeCatalog({
    systemPromptOptions: {
      skills: Array.from({ length: 20 }, (_, index) => ({
        name: `parser-skill-${index}`, description: 'parser report work',
      })),
    },
  }, discovery);
  reply = routing('as_written', 0.9);
  before = calls.length;
  assert.equal(await gate({ toolName: 'bash', toolCallId: 't4', input: { command: 'rg parser report' } }, discovery), undefined);
  const offered = Object.keys(calls.at(-1).body.questions.route.criteria);
  assert.deepEqual(offered.slice(0, 1), ['as_written']);
  assert.equal(offered.length, 7, 'as_written plus the six best skills');

  install('--remove');
  assert.ok(!existsSync(installed), 'the installer must remove its own asset');
  console.log('PASS: real installer and Pi loader; jev tool registered, request shape exact, key never leaked, the '
    + 'missing key asks the user once and honours a decline, and invalid-question, HTTP-error, non-JSON, no-answers, '
    + 'oversized-body, cancelled and timed-out paths all fail open without retrying or touching the network; the '
    + 'tool-call gate judges every call, blocks a strong objection once and fails open on '
    + 'timeout or error, and its route question blocks once on an on-topic skill or MCP pick while staying silent '
    + 'on as_written, a weak pick, a missing answer, JEV_ROUTE=0 and JEV_GATE_BLOCK=0');
} finally {
  server.close();
  for (const [name, value] of Object.entries(savedEnv)) {
    if (value === undefined) delete process.env[name];
    else process.env[name] = value;
  }
  if (path !== undefined) process.env.PATH = path;
  rmSync(temp, { recursive: true, force: true });
}

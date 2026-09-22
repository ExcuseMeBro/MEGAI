// The Laya decision tool: installed by the real installer, loaded by the real Pi
// resource loader, and driven through its real hooks. The extension spawns its real
// stdio bridge; the bridge imports the deterministic fake `laya` module from
// tests/fixtures, so every answer is scripted and nothing downloads or runs torch.
// No hosted service, credential or keychain is reachable — the legacy credential
// stub fails loudly if the extension ever asks for a key again.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

assert.ok(process.env.PI_PACKAGE_ROOT, 'Set PI_PACKAGE_ROOT to installed Pi');
const { DefaultResourceLoader } = await import(pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js')));
process.env.PI_OFFLINE = '1';
const ROOT = resolve('.');
const temp = mkdtempSync(join(tmpdir(), 'pi-laya-'));
const agent = join(temp, 'agent');
const fake = {
  loads: join(temp, 'loads.jsonl'), calls: join(temp, 'calls.jsonl'), script: join(temp, 'script.jsonl'),
  env: join(temp, 'env.jsonl'),
};
const KEPT = ['LAYA_DEVICE', 'LAYA_LANG', 'LAYA_PYTHON', 'LAYA_GATE', 'LAYA_GATE_BLOCK',
  'LAYA_ROUTE', 'LAYA_REPAIR', 'LAYA_LOG', 'LAYA_LOG_MAX_BYTES', 'LAYA_TIMEOUT_MS', 'LAYA_GATE_TIMEOUT_MS',
  'LAYA_GATE_THRESHOLD', 'LAYA_ROUTE_THRESHOLD', 'PYTHONPATH', 'MEGAI_HOSTED_KEY'];
const savedEnv = Object.fromEntries(KEPT.map((name) => [name, process.env[name]]));
const path = process.env.PATH;
// Every decision goes to the real bridge with the fake runtime on its PYTHONPATH.
process.env.PYTHONPATH = resolve('tests/fixtures/laya_fake');
process.env.LAYA_PYTHON = 'python3';
// A credential-shaped variable in the parent must not reach the local child.
process.env.MEGAI_HOSTED_KEY = 'must-not-leak';
process.env.LAYA_FAKE_ENV = 'MEGAI_HOSTED_KEY';
process.env.LAYA_FAKE_ENV_SEEN = fake.env;
process.env.LAYA_FAKE_LOADS = fake.loads;
// A simulated unreadable checkpoint lives in a file, so the test can clear it without
// restarting the session-scoped bridge (a child's environment is frozen at spawn).
const broken = join(temp, 'load-error.txt');
process.env.LAYA_FAKE_LOAD_ERROR_FILE = broken;
process.env.LAYA_FAKE_CALLS = fake.calls;
process.env.LAYA_FAKE_SCRIPT = fake.script;
process.env.LAYA_TIMEOUT_MS = '10000';
process.env.LAYA_GATE_TIMEOUT_MS = '150';
// `LAYA_LOG=0` keeps the suite out of the real ~/.megai/laya-calls.jsonl; the ledger
// cases below point LAYA_LOG at the temp directory instead.
process.env.LAYA_LOG = '0';

const lines = (path_) => (existsSync(path_) ? readFileSync(path_, 'utf8').split('\n').filter(Boolean) : []);
const rows = (path_) => lines(path_).map((line) => JSON.parse(line));
const direct = (...entries) => writeFileSync(fake.script, entries.map((entry) => `${JSON.stringify(entry)}\n`).join(''));
const read = (result) => JSON.parse(result.content[0].text);

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
const gating = {
  ...ctx,
  cwd: '/repo',
  sessionManager: { getBranch: () => [
    { type: 'message', message: { role: 'user', content: 'fix the flaky parser test' } },
    { type: 'message', message: { role: 'assistant', content: [{ type: 'text', text: 'reading it' }] } },
  ] },
  ui: { notify: (text, level) => gating.notices.push([text, level]) },
  notices: [],
};

const questions = {
  task_type: { type: 'choice', instructions: 'Which type?', criteria: { bug: 'a defect', chore: null } },
  effort: { type: 'score', instructions: 'How much of the repo?', criteria: ['one file', 'few files'] },
  needs_approval: { type: 'noul', instructions: 'Is this reserved?', criteria: { true: 'push to main', false: 'ordinary change' } },
};

try {
  install();
  const installedTool = join(agent, 'extensions/megai-laya/index.ts');
  const installedBridge = join(agent, 'extensions/megai-laya/bridge.py');
  assert.equal(readFileSync(installedTool, 'utf8'), readFileSync(resolve('pi-skill/laya/index.ts'), 'utf8'));
  assert.equal(readFileSync(installedBridge, 'utf8'), readFileSync(resolve('pi-skill/laya/bridge.py'), 'utf8'),
    'the bridge must ship next to the installed tool');
  const extensions = await load();
  const tools = new Map();
  for (const extension of extensions) {
    for (const [name, tool] of extension.tools) tools.set(name, tool.definition);
  }
  const laya = tools.get('laya');
  assert.ok(laya, 'the installed extension must register the laya tool');
  assert.ok(tools.get('sift'), 'the screen stays registered in the same extension');
  assert.ok(!/https?:\/\//.test(JSON.stringify(laya)), 'the tool must not describe an endpoint');
  const extension = extensions.find((item) => item.path.endsWith('extensions/megai-laya/index.ts'));
  const shutdown = extension.handlers.get('session_shutdown')?.[0];
  const gate = extension.handlers.get('tool_call')?.[0];
  const repair = extension.handlers.get('tool_result')?.[0];
  const routeCatalog = extension.handlers.get('before_agent_start')?.[0];
  assert.equal(typeof gate, 'function', 'the extension must register the tool-call gate');
  assert.equal(typeof repair, 'function', 'the extension must register the self-healing hook');
  assert.equal(typeof shutdown, 'function', 'the extension must register session_shutdown');
  assert.equal(typeof routeCatalog, 'function', 'the extension must cache the routing catalog');

  // A legacy credential is never consulted: the stub records any call and fails.
  mkdirSync(join(temp, 'bin'), { recursive: true });
  writeFileSync(join(temp, 'bin/security'),
    `#!/bin/sh\nprintf 'called\\n' >> '${join(temp, 'security-calls')}'\nexit 44\n`);
  chmodSync(join(temp, 'bin/security'), 0o755);
  process.env.PATH = join(temp, 'bin') + ':' + (path ?? '');
  const legacyKeyReads = () => (existsSync(join(temp, 'security-calls')) ? readFileSync(join(temp, 'security-calls'), 'utf8') : '');

  // Malformed questions are rejected before the bridge is even started.
  const invalid = read(await laya.execute('call-1', {
    state: 'fix the flaky test',
    questions: { ...questions, effort: { type: 'score', instructions: 'How much?', criteria: [] } },
  }, undefined, undefined, ctx));
  assert.equal(invalid.ok, false);
  assert.match(invalid.error, /invalid criteria for "effort"/);
  const noCriteria = read(await laya.execute('call-2', {
    state: 'fix the flaky test',
    questions: { task_type: { type: 'choice', instructions: 'Which type?' } },
  }, undefined, undefined, ctx));
  assert.equal(noCriteria.ok, false);
  assert.match(noCriteria.error, /criteria required for "task_type"/);
  const tooMany = read(await laya.execute('call-3', {
    state: 'fix the flaky test',
    questions: Object.fromEntries(Array.from({ length: 9 }, (_, index) => [`q${index}`, { type: 'noul', instructions: 'why' }])),
  }, undefined, undefined, ctx));
  assert.equal(tooMany.ok, false);
  assert.match(tooMany.error, /1-8 questions required/);
  const badId = read(await laya.execute('call-4', {
    state: 'fix the flaky test', questions: { '9bad': { type: 'noul', instructions: 'why' } },
  }, undefined, undefined, ctx));
  assert.equal(badId.ok, false);
  assert.match(badId.error, /invalid question id/);
  assert.equal(lines(fake.loads).length, 0, 'an invalid request must not start the local runtime');

  // A missing runtime is one actionable local error, and the next call starts one
  // fresh child instead of retrying in a loop. The bridge is session-scoped, so stop it
  // first — a warm child would simply ignore the interpreter change.
  shutdown();
  process.env.LAYA_PYTHON = join(temp, 'absent-python');
  const missing = read(await laya.execute('call-5', { state: 'fix the flaky test', questions }, undefined, undefined, ctx));
  assert.equal(missing.ok, false);
  assert.match(missing.error, /not installed|no such file|ENOENT/i);
  assert.match(missing.guidance, /do not retry in a loop/);
  process.env.LAYA_PYTHON = 'python3';
  writeFileSync(broken, 'checkpoint weights are unreadable\n');
  const failedLoad = read(await laya.execute('call-6', { state: 'fix the flaky test', questions }, undefined, undefined, ctx));
  assert.equal(failedLoad.ok, false);
  assert.match(failedLoad.error, /checkpoint weights are unreadable/);
  assert.equal(lines(fake.loads).length, 1, 'a load failure is attempted once, not retried');
  writeFileSync(broken, '');

  // A real call: exact request shape, typed answers, zero output tokens, local model.
  const before = lines(fake.calls).length;
  const result = await laya.execute('call-7', { state: 'fix the flaky test', questions }, undefined, undefined, ctx);
  assert.equal(read(result).ok, true);
  assert.equal(read(result).answers.needs_approval.noul, 0.05);
  assert.equal(read(result).answers.task_type.choice, 'bug');
  assert.equal(read(result).usage.output_tokens, 0);
  assert.equal(lines(fake.calls).length, before + 1);
  const call = rows(fake.calls).at(-1);
  assert.equal(call.route, 'english', 'the default route answers English state');
  assert.equal(call.repo, 'convaiinnovations/laya', 'and it is the configured local checkpoint');
  assert.equal(call.state, 'fix the flaky test', 'the state reaches the local process');
  assert.deepEqual(call.questions, {
    task_type: { type: 'choice', instructions: 'Which type?', criteria: { bug: 'a defect', chore: null } },
    effort: { type: 'score', instructions: 'How much of the repo?', criteria: ['one file', 'few files'] },
    needs_approval: { type: 'noul', instructions: 'Is this reserved?', criteria: { true: 'push to main', false: 'ordinary change' } },
  });
  assert.equal(legacyKeyReads(), '', 'no keychain read may happen');
  assert.ok(!/https?:\/\//.test(result.content[0].text), 'the tool output must not name an endpoint');

  // The other accepted criteria shapes are normalized before they reach the model.
  const shaped = read(await laya.execute('call-8', {
    state: 'fix the flaky test',
    questions: {
      task_type: { type: 'choice', instructions: 'Which type?', criteria: ['bug', 'chore'] },
      effort: { type: 'score', instructions: 'How much?', criteria: { one: 'one file', few: 'few files' } },
      needs_approval: { type: 'noul', instructions: 'Is this reserved?', criteria: ['no', 'yes'] },
    },
  }, undefined, undefined, ctx));
  assert.equal(shaped.ok, true);
  assert.deepEqual(rows(fake.calls).at(-1).questions, {
    task_type: { type: 'choice', instructions: 'Which type?', criteria: { bug: null, chore: null } },
    effort: { type: 'score', instructions: 'How much?', criteria: ['one', 'few'] },
    needs_approval: { type: 'noul', instructions: 'Is this reserved?', criteria: { no: null, yes: null } },
  });

  // One ledger row per decision: the local model identity, the answers and the
  // timing, never the state. `LAYA_LOG=0` is off, the ledger rolls at its cap.
  const ledger = join(temp, 'laya-calls.jsonl');
  const loadsBeforeLedger = lines(fake.loads).length;
  process.env.LAYA_LOG = ledger;
  const logged = await laya.execute('call-9', { state: 'fix the flaky test', questions }, undefined, undefined, ctx);
  const record = rows(ledger).at(-1);
  assert.match(record.id, /^[0-9a-f]{8}$/, 'every logged line carries a record id');
  assert.equal(record.id, read(logged).id, 'the id the caller sees is the logged record');
  assert.equal(record.source, 'tool');
  assert.equal(record.route, 'english', 'the ledger records the route that answered');
  assert.equal(record.model, 'convaiinnovations/laya', 'and the checkpoint identity behind it');
  assert.equal(record.runtime, 'local:laya', 'on the local runtime, never a host:port');
  assert.equal(record.answers.task_type.answer, 'bug');
  assert.equal(record.answers.task_type.confidence, 0.9);
  assert.deepEqual(record.answers.task_type.probabilities, { bug: 0.9, chore: 0.1 });
  assert.match(record.t, /^\d{4}-\d\d-\d\dT/);
  assert.ok(!readFileSync(ledger, 'utf8').includes('fix the flaky test'), 'the state must never be logged');
  assert.deepEqual(rows(fake.env).at(-1), { MEGAI_HOSTED_KEY: null },
    'a parent credential must never reach the local child');
  assert.ok(!/https?:\/\//.test(readFileSync(ledger, 'utf8')), 'no endpoint in the ledger');
  assert.equal(lines(fake.loads).length, loadsBeforeLedger, 'the whole session reuses one loaded bridge');
  const rowsBeforeOff = lines(ledger).length;
  process.env.LAYA_LOG = '0';
  await laya.execute('call-10', { state: 'fix the flaky test', questions }, undefined, undefined, ctx);
  assert.equal(lines(ledger).length, rowsBeforeOff, 'LAYA_LOG=0 appends nothing');
  process.env.LAYA_LOG = ledger;
  process.env.LAYA_LOG_MAX_BYTES = '1';
  await laya.execute('call-11', { state: 'fix the flaky test', questions }, undefined, undefined, ctx);
  assert.equal(lines(`${ledger}.1`).length, rowsBeforeOff, 'a ledger at the cap rolls to <file>.1');
  assert.equal(lines(ledger).length, 1, 'the call that crosses the cap opens the new ledger');
  delete process.env.LAYA_LOG_MAX_BYTES;

  // A deadline rejects the pending request but keeps the warm process: the next call
  // is answered by the same child and the late reply is dropped rather than misread.
  direct({ sleep_ms: 500 });
  process.env.LAYA_TIMEOUT_MS = '150';
  const slowCalls = lines(fake.calls).length;
  const timedOut = read(await laya.execute('call-12', { state: 'fix the flaky test', questions }, undefined, undefined, ctx));
  assert.equal(timedOut.ok, false);
  assert.match(timedOut.error, /timed out|cancelled/i);
  assert.equal(lines(fake.calls).length, slowCalls + 1, 'a timed-out request is not replayed');
  const loadsAfterTimeout = lines(fake.loads).length;
  direct({ answers: { task_type: { type: 'choice', choice: 'chore', probabilities: { chore: 0.8, bug: 0.2 }, confidence: 0.8 } } });
  const afterTimeout = read(await laya.execute('call-13', { state: 'fix the flaky test', questions }, undefined, undefined, ctx));
  assert.equal(afterTimeout.ok, true, `the warm local process must survive one slow request: ${JSON.stringify(afterTimeout)}`);
  assert.equal(afterTimeout.answers.task_type.choice, 'chore', 'the late reply must not be read as this answer');
  delete process.env.LAYA_TIMEOUT_MS;
  assert.equal(lines(fake.loads).length, loadsAfterTimeout, 'no reload after a timeout');

  // A caller cancellation is bounded too. Aborted before the request reaches the child
  // it sends nothing at all...
  direct({ sleep_ms: 500 });
  const controller = new AbortController();
  const cancelledCalls = lines(fake.calls).length;
  const pending = laya.execute('call-14', { state: 'fix the flaky test', questions }, controller.signal, undefined, ctx);
  controller.abort();
  const cancelled = read(await pending);
  assert.equal(cancelled.ok, false);
  assert.match(cancelled.error, /cancelled/i);
  assert.equal(lines(fake.calls).length, cancelledCalls, 'a cancellation before the write sends nothing');

  // ...and an in-flight one abandons its answer rather than replaying the request.
  const controller2 = new AbortController();
  const inFlight = laya.execute('call-15', { state: 'fix the flaky test', questions }, controller2.signal, undefined, ctx);
  await new Promise((resolve) => setTimeout(resolve, 60));
  controller2.abort();
  const abandoned = read(await inFlight);
  assert.equal(abandoned.ok, false);
  assert.match(abandoned.error, /cancelled/i);
  assert.equal(lines(fake.calls).length, cancelledCalls + 1, 'an in-flight cancellation is not replayed');

  // A crash is reported once, and the next call starts one fresh child.
  direct({ exit: 9 });
  const beforeCrash = lines(fake.loads).length;
  const crashed = read(await laya.execute('call-16', { state: 'fix the flaky test', questions }, undefined, undefined, ctx));
  assert.equal(crashed.ok, false);
  assert.match(crashed.error, /stopped|exited|code 9/i);
  direct({});
  const recovered = read(await laya.execute('call-17', { state: 'fix the flaky test', questions }, undefined, undefined, ctx));
  assert.equal(recovered.ok, true, 'a crashed child must not disable the tool');
  assert.equal(lines(fake.loads).length, beforeCrash + 1, 'exactly one fresh child is started');

  // The gate: report-only by default, and every answer is fail-open.
  const judged = (name, input) => gate({ toolName: name, toolCallId: 't1', input }, gating);
  gating.notices.length = 0;
  direct({});
  let gateCalls = lines(fake.calls).length;
  assert.equal(await judged('mcp', { tool: 'plane_workitem', args: { action: 'list' } }), undefined,
    'a call with no objection runs');
  assert.equal(lines(fake.calls).length, gateCalls + 1, 'exactly one local judgment per tool call');
  const judgment = rows(fake.calls).at(-1);
  assert.deepEqual(Object.keys(judgment.questions), ['object'], 'one question per call');
  assert.equal(judgment.questions.object.type, 'noul');
  assert.match(judgment.questions.object.instructions, /must not run as written/);
  assert.match(judgment.state, /fix the flaky parser test/, 'the judgment carries the goal');
  assert.match(judgment.state, /Tool call: mcp\(\{"tool":"plane_workitem"/, 'and the call itself');
  assert.equal(gating.notices.length, 0, 'a low objection is silent');

  // A strong objection is advice by default: the call runs and the warning is shown.
  const answering = (value) => ({ answers: { object: { type: 'noul', noul: value, confidence: 0.9 } } });
  direct(answering(0.9));
  assert.equal(await judged('bash', { command: 'rm -rf src' }), undefined,
    'blocking is off until the operator enables it');
  assert.equal(gating.notices.length, 1, 'the strong objection is reported');
  assert.match(gating.notices.at(-1)[0], /objection 0\.9/);
  assert.match(gating.notices.at(-1)[0], /Running it unchanged/);
  const reported = rows(fake.calls).at(-1);
  assert.match(reported.state, /rm -rf src/, 'the reported judgment is the call it judged');

  // LAYA_GATE_BLOCK=1 blocks the first call and lets an identical retry through.
  process.env.LAYA_GATE_BLOCK = '1';
  direct(answering(0.9));
  const blocked = await judged('bash', { command: 'rm -rf src' });
  assert.equal(blocked.block, true);
  assert.match(blocked.reason, /objection 0\.9/);
  assert.match(blocked.reason, /Repeated unchanged, it runs/);
  direct(answering(0.9));
  const seen = gating.notices.length;
  assert.equal(await judged('bash', { command: 'rm -rf src' }), undefined,
    'a repeated identical call must run rather than deadlock');
  assert.equal(gating.notices.length, seen + 1, 'the retry is reported and runs');
  assert.match(gating.notices.at(-1)[0], /Running it unchanged/);

  // The configured band is exact and inclusive.
  direct(answering(0.649));
  assert.equal(await judged('grep', { pattern: 'x' }), undefined, '0.649 does not block');
  direct(answering(0.65));
  assert.equal((await judged('grep', { pattern: 'x' })).block, true, 'exactly 0.65 blocks');
  process.env.LAYA_GATE_THRESHOLD = '0.8';
  direct(answering(0.75));
  assert.equal(await judged('grep', { pattern: 'y' }), undefined, 'LAYA_GATE_THRESHOLD retunes the band');
  delete process.env.LAYA_GATE_THRESHOLD;
  delete process.env.LAYA_GATE_BLOCK;

  // A failed, slow or missing judgment is not a verdict, and is not retried.
  const noticesBefore = gating.notices.length;
  direct({ error: 'inference exploded' });
  gateCalls = lines(fake.calls).length;
  assert.equal(await judged('bash', { command: 'ls' }), undefined, 'a failed judgment must not block');
  assert.equal(lines(fake.calls).length, gateCalls + 1, 'a failed judgment is not retried');
  assert.equal(gating.notices.length, noticesBefore, 'a failure is not a verdict');
  direct({ sleep_ms: 500 });
  assert.equal(await judged('edit', { path: 'a.ts' }), undefined,
    'a judgment slower than the gate deadline must fail open');
  process.env.LAYA_GATE = '0';
  gateCalls = lines(fake.calls).length;
  assert.equal(await judged('read', { path: 'a.ts' }), undefined);
  delete process.env.LAYA_GATE;
  assert.equal(await judged('laya', { state: 'x', questions }), undefined, 'the gate must not judge itself');
  assert.equal(lines(fake.calls).length, gateCalls, 'a switched-off or self call sends nothing');

  // Routing: an on-topic skill or MCP pick is reported by default and blocks once when
  // the operator enables blocking; `as_written`, a weak pick and an unrelated catalog
  // change nothing.
  routeCatalog({
    systemPromptOptions: {
      skills: [
        { name: 'megai', description: 'focused verification for a flaky test' },
        { name: 'ponytail', description: 'laziest solution for any coding task' },
      ],
      toolSnippets: { mcp: 'MCP gateway: install, status, search, describe, auth', bash: 'run a shell command' },
    },
  }, gating);
  const routing = (choice, weight, objection = 0.05) => ({
    answers: {
      object: { type: 'noul', noul: objection },
      route: { type: 'choice', choice, probabilities: { [choice]: weight }, confidence: weight },
    },
  });
  direct(routing('skill:megai', 0.83));
  gateCalls = lines(fake.calls).length;
  const routeNotices = gating.notices.length;
  assert.equal(await judged('bash', { command: 'node tools/run-flaky.mjs' }), undefined,
    'a route pick is advice while blocking is off');
  assert.equal(lines(fake.calls).length, gateCalls + 1, 'routing must not add a second request');
  const routed = rows(fake.calls).at(-1);
  assert.deepEqual(Object.keys(routed.questions), ['object', 'route']);
  assert.equal(routed.questions.route.type, 'choice');
  assert.equal(routed.questions.route.criteria.as_written, 'run this exact bash call as written');
  assert.match(routed.questions.route.criteria['skill:megai'], /flaky test/);
  assert.equal(routed.questions.route.criteria['skill:ponytail'], undefined, 'an unrelated skill is not offered');
  assert.equal(routed.questions.route.criteria['tool:mcp'], undefined, 'an unrelated MCP tool is not offered');
  assert.match(routed.state, /- skill:megai: focused verification for a flaky test/);
  assert.equal(gating.notices.length, routeNotices + 1);
  assert.match(gating.notices.at(-1)[0], /route.*skill "megai"/i);
  process.env.LAYA_GATE_BLOCK = '1';
  direct(routing('skill:megai', 0.83));
  const routeBlocked = await judged('bash', { command: 'node tools/run-flaky.mjs' });
  assert.equal(routeBlocked.block, true);
  assert.match(routeBlocked.reason, /load skill "megai"/);
  assert.match(routeBlocked.reason, /Repeated unchanged, it runs/);
  direct(routing('skill:megai', 0.83));
  assert.equal(await judged('bash', { command: 'node tools/run-flaky.mjs' }), undefined,
    'a repeated identical call must run rather than deadlock');
  delete process.env.LAYA_GATE_BLOCK;
  direct(routing('as_written', 0.95));
  assert.equal(await judged('bash', { command: 'node tools/run-flaky.mjs 2' }), undefined, 'as written runs');
  assert.ok(Object.keys(rows(fake.calls).at(-1).questions).includes('route'), 'the question is still asked');
  direct(routing('skill:megai', 0.69));
  assert.equal(await judged('bash', { command: 'node tools/run-flaky.mjs 3' }), undefined, 'a weak pick changes nothing');
  direct({ answers: { object: { type: 'noul', noul: 0.05 } } });
  assert.equal(await judged('bash', { command: 'node tools/run-flaky.mjs 4' }), undefined,
    'an unanswered route must not block');
  direct(routing('skill:megai', 0.99));
  process.env.LAYA_ROUTE = '0';
  gateCalls = lines(fake.calls).length;
  assert.equal(await judged('bash', { command: 'node tools/run-flaky.mjs 5' }), undefined);
  assert.deepEqual(Object.keys(rows(fake.calls).at(-1).questions), ['object'], 'LAYA_ROUTE=0 asks the objection only');
  assert.doesNotMatch(rows(fake.calls).at(-1).state, /could use instead/);
  delete process.env.LAYA_ROUTE;
  // The catalog caps what is offered: as_written plus the six best skills.
  routeCatalog({
    systemPromptOptions: {
      skills: Array.from({ length: 20 }, (_, index) => ({ name: `parser-skill-${index}`, description: 'parser report work' })),
    },
  }, gating);
  direct(routing('as_written', 0.9));
  await judged('bash', { command: 'rg parser report' });
  const offered = Object.keys(rows(fake.calls).at(-1).questions.route.criteria);
  assert.deepEqual(offered.slice(0, 1), ['as_written']);
  assert.equal(offered.length, 7, 'as_written plus the six best skills');

  // Self-healing: one next-move question per failed tool result, appended, never blocking.
  const failedCall = (over = {}) => ({
    toolName: 'bash', toolCallId: 'r1', isError: true, input: { command: 'gh pr create' },
    content: [{ type: 'text', text: 'HTTP 429 from the forge' }], ...over,
  });
  direct({ answers: { next_move: { type: 'choice', choice: 'wait', probabilities: { wait: 0.71 }, confidence: 0.71 } } });
  gateCalls = lines(fake.calls).length;
  const rescued = await repair(failedCall(), gating);
  assert.equal(lines(fake.calls).length, gateCalls + 1, 'exactly one request per failed call');
  const repairCall = rows(fake.calls).at(-1);
  assert.deepEqual(Object.keys(repairCall.questions), ['next_move'], 'one question per repair');
  assert.equal(repairCall.questions.next_move.type, 'choice');
  assert.deepEqual(Object.keys(repairCall.questions.next_move.criteria),
    ['retry', 'wait', 'change_parameters', 'switch_provider', 'escalate']);
  assert.match(repairCall.state, /fix the flaky parser test/, 'the repair carries the goal');
  assert.match(repairCall.state, /HTTP 429 from the forge/, 'and the failure text');
  assert.match(repairCall.state, /including this one: 1/);
  assert.deepEqual(rescued.content.at(-1),
    { type: 'text', text: 'Laya next move: wait — pause briefly and then retry the same call confidence 0.71.' });
  assert.equal(rescued.content[0].text, 'HTTP 429 from the forge', 'the raw failure stays first');
  assert.equal(rescued.block, undefined, 'the repair never blocks');
  direct({ answers: { next_move: { type: 'choice', choice: 'wait', confidence: 0.71 } } });
  await repair(failedCall(), gating);
  assert.match(rows(fake.calls).at(-1).state, /including this one: 2/, 'the attempt count follows the exact call');
  direct({});
  gateCalls = lines(fake.calls).length;
  assert.equal(await repair(failedCall({ isError: false }), gating), undefined);
  process.env.LAYA_REPAIR = '0';
  assert.equal(await repair(failedCall(), gating), undefined);
  delete process.env.LAYA_REPAIR;
  assert.equal(await repair(failedCall({ toolName: 'laya' }), gating), undefined);
  assert.equal(lines(fake.calls).length, gateCalls, 'only a real failure of another tool is repaired');
  direct({ error: 'inference exploded' });
  assert.equal(await repair(failedCall(), gating), undefined, 'a failed judgment must not touch the result');
  direct({ answers: { next_move: { type: 'choice', choice: 'nonsense' } } });
  assert.equal(await repair(failedCall(), gating), undefined, 'an unknown move is not reported');
  direct({});

  // Session shutdown closes the child and leaves nothing running; a later call starts
  // one fresh process.
  const loadedPids = [...new Set(rows(fake.loads).map((row) => row.pid))];
  assert.ok(loadedPids.length >= 1, 'the suite must have started at least one child');
  const alive = () => loadedPids.filter((pid) => {
    try { process.kill(pid, 0); return true; } catch { return false; }
  });
  assert.equal(alive().length, 1, 'one session uses exactly one live bridge process');
  await shutdown({}, gating);
  const deadline = Date.now() + 5_000;
  while (alive().length > 0 && Date.now() < deadline) await new Promise((tick) => setTimeout(tick, 20));
  assert.equal(alive().length, 0, 'session_shutdown must stop the local child');
  const afterShutdown = read(await laya.execute('call-18', { state: 'fix the flaky test', questions }, undefined, undefined, ctx));
  assert.equal(afterShutdown.ok, true, 'a later call starts a fresh child');
  await shutdown({}, gating);

  install('--remove');
  assert.ok(!existsSync(installedTool), 'the installer must remove its own asset');
  assert.ok(!existsSync(installedBridge), 'and the bridge with it');
  console.log('PASS: real installer, real Pi loader and the real stdio bridge with a deterministic local '
    + 'runtime; the laya tool answers typed choice/score/noul locally with zero output tokens, no key and no '
    + 'endpoint, validation and missing-runtime, load-error, timeout, cancellation and crash '
    + 'paths all fail open without a retry loop, one process serves the session and shutdown stops it, the '
    + 'ledger keeps probabilities without the state, and the gate is report-only by default, blocks once when '
    + 'explicitly enabled, retunes by threshold, routes to an on-topic skill and repairs a failed tool result');
} finally {
  for (const [name, value] of Object.entries(savedEnv)) {
    if (value === undefined) delete process.env[name];
    else process.env[name] = value;
  }
  if (path !== undefined) process.env.PATH = path;
  rmSync(temp, { recursive: true, force: true });
}

import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync, readFileSync, existsSync, realpathSync, rmSync, chmodSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { once } from 'node:events';
import test from 'node:test';
import { DatabaseSync } from 'node:sqlite';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const launcher = join(root, 'launcher.py');
const fixture = pathToFileURL(join(root, 'test/fixture.mjs')).href;
const env = { ...process.env, MEGAI_DURABLE_TESTING: '1', MEGAI_DURABLE_TEST_MODULE: fixture };
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(predicate) {
  const end = Date.now() + 10000;
  while (!predicate()) { assert(Date.now() < end, 'Timed out waiting for observed fixture state'); await delay(25); }
}
function start(args, options = {}) {
  const process = spawn('python3', ['-B', launcher, ...args], { env, ...options });
  let out = ''; let err = '';
  process.stdout?.on('data', data => { out += data; }); process.stderr?.on('data', data => { err += data; });
  const done = once(process, 'exit').then(([code, signal]) => ({ code, signal, out, err }));
  return { process, done, output: () => out };
}
async function run(task, command, extra = [], options) {
  return start([command, '--task', task, ...extra], options).done;
}
async function setup(t, behavior = {}) {
  const temp = mkdtempSync(join(realpathSync(tmpdir()), 'megai-durable-'));
  chmodSync(temp, 0o700);
  const task = join(temp, 'task');
  t.after(() => rmSync(temp, { recursive: true, force: true }));
  const init = await run(task, 'init', ['--cwd', temp, '--provider', 'faux', '--model', 'faux-1', '--thinking', 'off', '--allow-write']);
  assert.equal(init.code, 0, init.out + init.err);
  writeFileSync(join(task, 'fixture.json'), JSON.stringify(behavior), { mode: 0o600 });
  const prompt = join(temp, 'prompt'); writeFileSync(prompt, 'Disposable request', { mode: 0o600 });
  return { task, prompt };
}
function rows(path) { return readFileSync(path, 'utf8').trim().split('\n').length; }
function worker(task) { return Number(readFileSync(join(task, 'tool-started'), 'utf8')); }
async function killedWorker(t, task, prompt) {
  const active = start(['run', '--task', task, '--prompt-file', prompt, '--request-id', 'crash-1', '--max-restarts', '0']);
  t.after(() => { if (active.process.exitCode === null) active.process.kill('SIGTERM'); });
  await until(() => existsSync(join(task, 'tool-started')));
  process.kill(worker(task), 'SIGKILL');
  const ended = await active.done;
  assert.equal(ended.code, 2, ended.out + ended.err);
}

test('standalone admission, request deduplication and SQLite durability', { timeout: 20000 }, async t => {
  const { task, prompt } = await setup(t);
  const ready = await run(task, 'doctor'); assert.equal(ready.code, 0, ready.out + ready.err);
  assert.match(ready.out, /SQLite WAL\/FULL/);
  const first = await run(task, 'run', ['--prompt-file', prompt, '--request-id', 'same-id']);
  assert.equal(first.code, 0, first.out + first.err); assert.match(first.out, /FIXTURE_DONE/);
  const result = JSON.parse(readFileSync(join(task, 'result.json')));
  const second = await run(task, 'run', ['--prompt-file', prompt, '--request-id', 'same-id']);
  assert.equal(second.code, 0, second.out + second.err);
  assert.equal(JSON.parse(readFileSync(join(task, 'result.json'))).submission.id, result.submission.id);
  assert.equal(rows(join(task, 'model-calls')), 1, 'duplicate input must not invoke model again');
  writeFileSync(prompt, 'Different content');
  const collision = await run(task, 'run', ['--prompt-file', prompt, '--request-id', 'same-id']);
  assert.equal(collision.code, 1); assert.match(collision.out, /different content/);
  const cancelled = await run(task, 'cancel', ['--note', 'Discard the rejected collision; retain the original transcript.']);
  assert.equal(cancelled.code, 0, cancelled.out + cancelled.err);
  assert(!existsSync(join(task, 'active.json')));
  const fresh = await run(task, 'run', ['--prompt-file', prompt, '--request-id', '__proto__']);
  assert.equal(fresh.code, 0, fresh.out + fresh.err);
  const status = await run(task, 'status'); assert.equal(status.code, 0, status.out + status.err);
  assert.match(status.out, /offline/);
  const db = new DatabaseSync(join(task, 'state.sqlite'), { readOnly: true });
  assert.equal(db.prepare('PRAGMA integrity_check').get().integrity_check, 'ok'); db.close();
});

test('safe read resumes after real SIGKILL and original admission is preserved', { timeout: 20000 }, async t => {
  const { task, prompt } = await setup(t, { tool: 'read' });
  await killedWorker(t, task, prompt);
  assert.equal(rows(join(task, 'read-effects')), 1);
  writeFileSync(join(task, 'gate'), 'open');
  const resumed = await run(task, 'resume');
  assert.equal(resumed.code, 0, resumed.out + resumed.err); assert.match(resumed.out, /FIXTURE_DONE/);
  assert.equal(rows(join(task, 'read-effects')), 2, 'explicit safe read should replay');
  assert.equal(rows(join(task, 'model-calls')), 2, 'model tool intent must not be generated again');
});

test('unsafe interrupted effect blocks recovery; headless cannot authorize reconciliation', { timeout: 20000 }, async t => {
  const { task, prompt } = await setup(t, { tool: 'write' });
  await killedWorker(t, task, prompt);
  const blocked = await run(task, 'resume'); assert.equal(blocked.code, 2, blocked.out + blocked.err);
  assert.match(blocked.out, /Unsafe interrupted work/); assert.equal(rows(join(task, 'write-effects')), 1);
  const status = await run(task, 'status'); assert.match(status.out, /fixture-call/);
  const headless = await run(task, 'reconcile', ['--note', 'Effect confirmed once in disposable fixture.']);
  assert.equal(headless.code, 2); assert.match(headless.out, /Human terminal required/);
  // A PTY supplies the explicit human-command boundary, with a recorded note, not a model-callable tool.
  const script = 'import os,pty,subprocess,sys; a,b=pty.openpty(); r=subprocess.run(sys.argv[1:],stdin=b); os.close(a); os.close(b); sys.exit(r.returncode)';
  const pty = spawn('python3', ['-B', '-c', script, 'python3', '-B', launcher, 'reconcile', '--task', task,
    '--note', 'Effect confirmed once in disposable fixture; do not repeat it.'], { env });
  let out = ''; pty.stdout.on('data', data => { out += data; });
  assert.equal((await once(pty, 'exit'))[0], 0, out);
  const resumed = await run(task, 'resume'); assert.equal(resumed.code, 0, resumed.out + resumed.err);
  assert.equal(rows(join(task, 'write-effects')), 1, 'unsafe tool must never replay after reconciliation');
});

test('exclusive ownership survives supervisor death; status and explicit stop do not require a daemon', { timeout: 25000 }, async t => {
  const { task, prompt } = await setup(t, { tool: 'read' });
  const active = start(['run', '--task', task, '--prompt-file', prompt, '--request-id', 'owner-test']);
  await until(() => existsSync(join(task, 'tool-started')));
  const pid = worker(task);
  t.after(() => { try { process.kill(pid, 'SIGTERM'); } catch {} });
  assert.match((await run(task, 'status')).out, /running/);
  const second = await run(task, 'resume'); assert.equal(second.code, 2); assert.match(second.out, /already owned/);
  active.process.kill('SIGKILL'); await active.done;
  assert.equal((await run(task, 'resume')).code, 2, 'orphan worker still retains kernel lock');
  const stopped = await run(task, 'stop'); assert.equal(stopped.code, 0); assert.match(stopped.out, /stop-requested/);
  await until(() => { try { process.kill(pid, 0); return false; } catch { return true; } });
  writeFileSync(join(task, 'gate'), 'open');
  const resumed = await run(task, 'resume'); assert.equal(resumed.code, 0, resumed.out + resumed.err);
});

test('supervisor recovers a killed safe worker, but never loops on provider failure', { timeout: 25000 }, async t => {
  const { task, prompt } = await setup(t, { tool: 'read' });
  const active = start(['run', '--task', task, '--prompt-file', prompt, '--request-id', 'supervise']);
  await until(() => existsSync(join(task, 'tool-started')));
  writeFileSync(join(task, 'gate'), 'open');
  process.kill(worker(task), 'SIGKILL');
  const result = await active.done; assert.equal(result.code, 0, result.out + result.err);
  assert.match(result.out, /"event": "restart"/); assert.equal(rows(join(task, 'read-effects')), 2);
  const failed = await setup(t, { providerError: true });
  const error = await run(failed.task, 'run', ['--prompt-file', failed.prompt, '--request-id', 'provider-error']);
  assert.equal(error.code, 1, error.out + error.err); assert.doesNotMatch(error.out, /"event": "restart"/);
  assert.equal(rows(join(failed.task, 'model-calls')), 1);
});

test('restart budget is bounded, config drift and read-only policy fail closed', { timeout: 20000 }, async t => {
  const { task, prompt } = await setup(t, { startupCrash: true });
  const result = await run(task, 'run', ['--prompt-file', prompt, '--request-id', 'crash-budget']);
  assert.equal(result.code, 2); assert.equal(rows(join(task, 'startups')), 3); assert.match(result.out, /budget exhausted/);
  const normal = await setup(t);
  assert.equal((await run(normal.task, 'doctor')).code, 0);
  const config = JSON.parse(readFileSync(join(normal.task, 'config.json'))); config.allowWrite = false;
  writeFileSync(join(normal.task, 'config.json'), JSON.stringify(config));
  const drift = await run(normal.task, 'doctor'); assert.equal(drift.code, 1); assert.match(drift.out, /Config changed/);
  const readonly = await setup(t, { tool: 'write' });
  const readConfig = JSON.parse(readFileSync(join(readonly.task, 'config.json'))); readConfig.allowWrite = false;
  writeFileSync(join(readonly.task, 'config.json'), JSON.stringify(readConfig));
  const readResult = await run(readonly.task, 'run', ['--prompt-file', readonly.prompt, '--request-id', 'read-only']);
  assert.equal(readResult.code, 0, readResult.out + readResult.err);
  assert(!existsSync(join(readonly.task, 'write-effects')), 'disabled write must never execute');
});

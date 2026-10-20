import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { chmodSync, existsSync, linkSync, mkdirSync, mkdtempSync, readFileSync, realpathSync,
  rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { execFileSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import { LocalWorker } from '../pi-defaults/extensions/megai-local-worker/bridge.mjs';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const extensionPath = process.env.MEGAI_LOCAL_WORKER_EXTENSION || join(repo, 'pi-defaults/extensions/megai-local-worker/index.ts');
let piRoot = dirname(realpathSync(execFileSync('which', ['pi'], { encoding: 'utf8' }).trim()));
while (!existsSync(join(piRoot, 'package.json'))) piRoot = dirname(piRoot);
assert.equal(JSON.parse(readFileSync(join(piRoot, 'package.json'))).name, '@earendil-works/pi-coding-agent');
const { loadExtensions, createExtensionRuntime } = await import(pathToFileURL(join(piRoot, 'dist/core/extensions/index.js')));
const roots = [];
const oldHome = process.env.MEGAI_HOME;
after(() => { roots.forEach(root => rmSync(root, { recursive: true, force: true }));
  if (oldHome === undefined) delete process.env.MEGAI_HOME; else process.env.MEGAI_HOME = oldHome; });
const hash = value => createHash('sha256').update(value).digest('hex');
function json(path, value) { writeFileSync(path, JSON.stringify(value), { mode: 0o600 }); }
function fixture() {
  const base = mkdtempSync(join(realpathSync(tmpdir()), 'pi-local-worker-')); roots.push(base);
  const cwd = join(base, 'repo'); mkdirSync(cwd); const agentDir = join(base, 'agent'); mkdirSync(agentDir);
  const launcher = join(base, 'pi-durable');
  writeFileSync(launcher, `#!${process.execPath}
const fs = require('node:fs'); const path = require('node:path');
process.umask(0o077);
const args = process.argv.slice(2), command = args[0];
const option = key => args[args.indexOf(key)+1]; const task = option('--task');
const write = (name, data) => fs.writeFileSync(path.join(task, name), JSON.stringify(data), {mode:0o600});
if (process.env.MEGAI_DURABLE_TESTING || process.env.MEGAI_DURABLE_TEST_MODULE) throw Error('injection leaked');
fs.appendFileSync(${JSON.stringify(join(base, 'calls'))}, command+'\\n', {mode:0o600});
if (command === 'init') write('config.json', {schema:1,cwd:option('--cwd'),provider:option('--provider'),model:option('--model'),thinking:option('--thinking'),agentDir:option('--agent-dir'),allowWrite:false});
if (command === 'run') {
  const content = fs.readFileSync(option('--prompt-file'),'utf8');
  write('active.json',{requestId:option('--request-id'),content});
  write('result.json',{requestId:option('--request-id'),submission:{status:'done'},answer:'PRIVATE_ANSWER'});
}
if (command === 'doctor' && fs.existsSync(path.join(task,'fail-auth'))) { console.log(JSON.stringify({status:'error',message:'Provider not configured'})); process.exitCode=1; }
else console.log(JSON.stringify({status:command==='doctor'?'ready':command==='stop'?'stop-requested':'offline',unsafe:[],inspection:{secret:'PRIVATE_TRANSCRIPT'},owner:{runId:'owned-run',supervisorPid:123}}));
if (command === 'run' || command === 'resume') write(command+'-completed', {finished:true});
`, { mode: 0o700 });
  const options = { root: join(base, 'private'), cwd, launcher, agentDir, provider: 'exact-provider', model: 'exact-model', thinking: 'high' };
  return { base, cwd, options, worker: new LocalWorker(options), calls: () => existsSync(join(base, 'calls')) ? readFileSync(join(base, 'calls'), 'utf8').trim().split('\n') : [] };
}
async function completed(task, command) {
  const deadline = Date.now() + 5000;
  while (!existsSync(join(task, command + '-completed'))) {
    assert(Date.now() < deadline, 'Fixture did not finish');
    await new Promise(done => setTimeout(done, 20));
  }
}
async function instance(f) {
  process.env.MEGAI_HOME = join(f.base, 'extension-home');
  const messages = [], notices = [], confirmations = [];
  const runtime = createExtensionRuntime();
  runtime.sendMessage = (message, options) => messages.push({ message, options });
  runtime.getThinkingLevel = () => 'high';
  const loaded = await loadExtensions([extensionPath], f.cwd, undefined, runtime);
  assert.deepEqual(loaded.errors, []);
  const extension = loaded.extensions[0];
  const ctx = { cwd: f.cwd, hasUI: true, model: { provider: 'exact-provider', id: 'exact-model' },
    ui: { notify: (...args) => notices.push(args), confirm: async (...args) => { confirmations.push(args); return false; } } };
  return { extension, ctx, messages, notices, confirmations,
    command: (name, args = '') => extension.commands.get(name).handler(args, ctx) };
}

test('native Pi loads explicit commands only, without startup events, tools, workers or model changes', async () => {
  const f = fixture(), one = await instance(f);
  assert.deepEqual([...one.extension.commands.keys()], ['durable', 'durable-init', 'durable-status', 'durable-doctor', 'durable-run', 'durable-resume', 'durable-stop']);
  assert.equal(one.extension.tools.size, 0); assert.equal(one.extension.handlers.size, 0);
  assert.deepEqual(f.calls(), []); assert(!existsSync(join(f.base, 'extension-home')));
  await one.command('durable');
  assert.equal(one.messages[0].options.triggerTurn, false);
  assert.match(one.messages[0].message.content, /not Vercel Workflow World/);
  await one.command('durable-init', 'audit');
  assert.equal(one.confirmations.length, 1); assert.match(one.confirmations[0][1], /exact-provider\/exact-model/);
  assert.match(one.confirmations[0][1], /Thinking: high/);
  assert(!existsSync(join(f.base, 'extension-home')));
  one.ctx.hasUI = false;
  await one.command('durable-init', 'audit');
  assert.equal(one.confirmations.length, 1); assert.match(one.notices.at(-1)[0], /human UI confirmation/);
  await one.command('durable-run', 'audit req-1 Input');
  await one.command('durable-resume', 'audit'); await one.command('durable-stop', 'audit');
  assert.deepEqual(f.calls(), []); assert.deepEqual(one.ctx.model, { provider: 'exact-provider', id: 'exact-model' });
});

test('native human confirmations wire successful init/run/resume/stop and canceled/headless actions cannot launch', async () => {
  const f = fixture(), one = await instance(f);
  const env = { HOME: process.env.HOME, PI_CODING_AGENT_DIR: process.env.PI_CODING_AGENT_DIR };
  const bin = join(f.base, '.local/bin'); mkdirSync(bin, { recursive: true });
  writeFileSync(join(bin, 'pi-durable'), readFileSync(f.options.launcher), { mode: 0o700 });
  process.env.HOME = f.base; process.env.PI_CODING_AGENT_DIR = f.options.agentDir;
  try {
    one.ctx.ui.confirm = async (...args) => { one.confirmations.push(args); return true; };
    await one.command('durable-init', 'audit');
    assert.deepEqual(one.notices, []);
    const job = new LocalWorker({ ...f.options, root: join(f.base, 'extension-home/local-workers'), launcher: join(bin, 'pi-durable') });
    assert.equal(job.config('audit').thinking, 'high');
    await one.command('durable-doctor', 'audit');
    one.ctx.ui.confirm = async () => false;
    await one.command('durable-run', 'audit stable-1 Do not launch yet');
    assert(!f.calls().includes('run'));
    one.ctx.ui.confirm = async () => true;
    await one.command('durable-run', 'audit stable-1 Read AGENTS.md');
    await completed(job.task('audit'), 'run');
    await one.command('durable-resume', 'audit'); await completed(job.task('audit'), 'resume');
    one.ctx.hasUI = false;
    await one.command('durable-stop', 'audit'); assert(!f.calls().includes('stop'));
    one.ctx.hasUI = true; await one.command('durable-stop', 'audit'); assert(f.calls().includes('stop'));
    assert(one.messages.every(item => item.options.triggerTurn === false));
    assert(!one.messages.some(item => item.message.content.includes('PRIVATE_TRANSCRIPT')));
  } finally {
    for (const [key, value] of Object.entries(env)) { if (value === undefined) delete process.env[key]; else process.env[key] = value; }
  }
});

test('read-only init pins exact native selection; doctor/status emit metadata only and fail auth without fallback', async () => {
  const f = fixture(), { worker } = f;
  assert.equal((await worker.init('audit')).status, 'initialized');
  const task = worker.task('audit');
  const config = JSON.parse(readFileSync(join(task, 'config.json')));
  assert.deepEqual(config, { schema: 1, cwd: f.cwd, ...worker.selection, allowWrite: false });
  assert.equal((await worker.init('audit')).status, 'already-initialized');
  assert.equal(f.calls().filter(c => c === 'init').length, 1);
  const data = await worker.inspect('audit', true);
  assert.equal(data.status, 'ready'); assert.equal(data.allowWrite, false);
  assert(!JSON.stringify(data).includes('PRIVATE_TRANSCRIPT'));
  writeFileSync(join(task, 'fail-auth'), 'fixture');
  await assert.rejects(worker.inspect('audit', true), /Provider not configured/);
  const changed = new LocalWorker({ ...f.options, model: 'other-model' });
  await assert.rejects(changed.launch('audit', { requestId: 'new', prompt: 'No fallback' }), /Pi model differs/);
  await assert.rejects(changed.inspect('audit', true), /Pi model differs/);
  assert.equal((await changed.inspect('audit')).model, 'exact-model', 'inspection remains available after model drift');
});

test('private stable intent precedes spawn; retry is metadata-only, collisions fail; resume is explicit', async () => {
  const f = fixture(), { worker } = f; await worker.init('audit'); const task = worker.task('audit');
  const injectedBefore = { testing: process.env.MEGAI_DURABLE_TESTING, module: process.env.MEGAI_DURABLE_TEST_MODULE };
  process.env.MEGAI_DURABLE_TESTING = '1'; process.env.MEGAI_DURABLE_TEST_MODULE = 'malicious-fixture';
  let launch;
  try { launch = await worker.launch('audit', { requestId: 'request-001', prompt: 'Read files only; $(never shell)' }); }
  finally {
    for (const [key, value] of [['MEGAI_DURABLE_TESTING', injectedBefore.testing], ['MEGAI_DURABLE_TEST_MODULE', injectedBefore.module]]) {
      if (value === undefined) delete process.env[key]; else process.env[key] = value;
    }
  }
  assert.equal(launch.status, 'launched'); await completed(task, 'run');
  assert.equal((await worker.launch('audit', { requestId: 'request-001', prompt: 'Read files only; $(never shell)' })).status, 'already-requested');
  await assert.rejects(worker.launch('audit', { requestId: 'request-001', prompt: 'Different' }), /different content/);
  assert.equal(f.calls().filter(c => c === 'run').length, 1);
  assert(!JSON.stringify(await worker.inspect('audit')).includes('PRIVATE_ANSWER'));
  const fresh = new LocalWorker(f.options);
  assert.equal((await fresh.launch('audit', { resume: true })).status, 'launched'); await completed(task, 'resume');
  assert.equal(f.calls().filter(c => c === 'resume').length, 1);
  const receiptFile = join(task, `request-${hash('request-001')}.json`);
  const receipt = JSON.parse(readFileSync(receiptFile)); json(receiptFile, { ...receipt, schema: 99 });
  await assert.rejects(fresh.launch('audit', { resume: true }), /differs from bridge receipt/);
  await assert.rejects(worker.launch('audit', { requestId: 'request-001', prompt: 'Read files only; $(never shell)' }), /invalid receipt/);
  json(receiptFile, receipt);
  const active = JSON.parse(readFileSync(join(task, 'active.json'))); active.content = 'tampered'; json(join(task, 'active.json'), active);
  await assert.rejects(fresh.launch('audit', { resume: true }), /differs from bridge receipt/);
  assert.equal((await worker.stop('audit')).status, 'stop-requested');
});

test('failed spawn and incomplete init retain evidence and cannot be blindly retried', async () => {
  const f = fixture(), { worker } = f; await worker.init('audit'); const task = worker.task('audit');
  writeFileSync(f.options.launcher, '#!/nonexistent-local-worker-interpreter\n', { mode: 0o700 });
  await assert.rejects(worker.launch('audit', { requestId: 'uncertain', prompt: 'Inspect only' }), /ENOENT/);
  assert(existsSync(join(task, `request-${hash('uncertain')}.json`)));
  assert.equal((await worker.launch('audit', { requestId: 'uncertain', prompt: 'Inspect only' })).status, 'already-requested');
  await assert.rejects(worker.launch('audit', { resume: true }), /No active request/);
  mkdirSync(worker.task('partial'), { mode: 0o700 });
  await assert.rejects(worker.init('partial'), /ENOENT/);
});

test('bridge drives the real native SQLite worker and result with a disposable faux provider, no external model calls', { timeout: 20000 }, async () => {
  const f = fixture();
  const q = value => "'" + value.replaceAll("'", "'\\\"'\\\"'") + "'";
  const runtime = join(repo, 'pi-durable');
  writeFileSync(f.options.launcher, '#!/bin/sh\nexport MEGAI_DURABLE_TESTING=1\nexport MEGAI_DURABLE_TEST_MODULE=' + q(pathToFileURL(join(runtime, 'test/fixture.mjs')).href)
    + '\nexec python3 -B ' + q(join(runtime, 'launcher.py')) + ' "$@"\n', { mode: 0o700 });
  const job = new LocalWorker({ ...f.options, provider: 'faux', model: 'faux-1', thinking: 'off' });
  await job.init('real'); const task = job.task('real'); json(join(task, 'fixture.json'), {});
  assert.equal((await job.inspect('real', true)).status, 'ready');
  const launch = await job.launch('real', { requestId: 'real-001', prompt: 'Disposable read-only fixture' });
  assert.equal(launch.status, 'launched');
  const deadline = Date.now() + 10000;
  while (!existsSync(join(task, 'result.json')) || existsSync(join(task, 'active.json'))) {
    assert(Date.now() < deadline, 'Native worker did not settle'); await new Promise(done => setTimeout(done, 25));
  }
  const result = JSON.parse(readFileSync(join(task, 'result.json')));
  assert.equal(result.requestId, 'real-001'); assert.equal(result.submission.status, 'done');
  assert.match(JSON.stringify(result.answer), /FIXTURE_DONE/);
  assert.equal(readFileSync(join(task, 'model-calls'), 'utf8').trim().split('\n').length, 1);
  assert.equal((await job.launch('real', { requestId: 'real-001', prompt: 'Disposable read-only fixture' })).status, 'already-requested');
  assert.equal(job.config('real').allowWrite, false);
});

test('config escalation, unsafe names, nonprivate state, symlinks and cross-directory access fail closed', async () => {
  const f = fixture(), { worker } = f; await worker.init('audit'); const task = worker.task('audit');
  for (const name of ['../default', '.', 'a/b', '--write', 'A', 'a'.repeat(65)]) assert.throws(() => worker.task(name), /Worker name/);
  const other = join(f.base, 'other'); mkdirSync(other);
  assert.notEqual(new LocalWorker({ ...f.options, cwd: other }).task('audit'), task);
  const config = JSON.parse(readFileSync(join(task, 'config.json'))); config.allowWrite = true; json(join(task, 'config.json'), config);
  await assert.rejects(worker.launch('audit', { requestId: 'x', prompt: 'No write' }), /config changed/);
  json(join(task, 'bridge.json'), { schema: 1, configHash: hash(JSON.stringify(config)) });
  await assert.rejects(worker.launch('audit', { requestId: 'x', prompt: 'No write' }), /Only read-only/);
  const configPath = join(task, 'config.json'), hardlink = join(task, 'config-hardlink');
  linkSync(configPath, hardlink); assert.throws(() => worker.config('audit'), /Private bounded/); rmSync(hardlink);
  chmodSync(configPath, 0o644); assert.throws(() => worker.config('audit'), /Private bounded/);
  const alias = join(f.base, 'alias'); symlinkSync(f.options.root, alias);
  const unsafe = new LocalWorker({ ...f.options, root: alias });
  await assert.rejects(unsafe.init('new'), /Symlink refused/);
});

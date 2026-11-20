import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { once } from 'node:events';
import { mkdtempSync, mkdirSync, realpathSync, rmSync, writeFileSync, existsSync, chmodSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { tmpdir } from 'node:os';
import { execFileSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { piPackageRoot } from './pi-package.mjs';

const root = piPackageRoot();
const { createAgentSession, DefaultResourceLoader, ModelRuntime, SessionManager, SettingsManager } =
  await import(pathToFileURL(join(root, 'dist/index.js')));
const { fauxProvider, fauxAssistantMessage, InMemoryCredentialStore } =
  await import(pathToFileURL(join(dirname(root), 'pi-ai/dist/index.js')));
const extensionPath = fileURLToPath(new URL('../pi-defaults/opt-in/factory/index.ts', import.meta.url));
const project = 'factory-fixture';
const makeTask = (id, status, human = false, slug = project) => ({ id, status, human, project: slug });
const lockName = `factory-locks/${project}.lock`;

// Exercise the installed Pi SDK with its native faux model. Only this test process
// reroutes the fixed Brokan origin, to an ephemeral HTTP fixture rather than the live board.
async function fixture(t, { tasks = [makeTask(1, 'doing'), makeTask(2, 'todo')], repos = ['test/factory-fixture'],
  trusted = true, configured, parallel = false, origin = 'https://github.com/test/factory-fixture.git' } = {}) {
  const base = realpathSync(mkdtempSync(join(tmpdir(), 'pi-factory-sdk-')));
  const cwd = join(base, 'checkout'), agentDir = join(base, 'agent');
  const priorDir = process.env.PI_CODING_AGENT_DIR, originalFetch = globalThis.fetch;
  const sessions = [], reads = [], unexpected = [];
  const vars = ['PATH', 'PI_FACTORY_TEST_BASE', 'PI_FACTORY_TEST_URL'];
  const saved = vars.map(key => [key, process.env[key]]);
  t.after(() => {
    for (const session of sessions) session.dispose();
    globalThis.fetch = originalFetch;
    if (priorDir === undefined) delete process.env.PI_CODING_AGENT_DIR;
    else process.env.PI_CODING_AGENT_DIR = priorDir;
    for (const [key, value] of saved) { if (value === undefined) delete process.env[key]; else process.env[key] = value; }
    rmSync(base, { recursive: true, force: true });
    assert.deepEqual(unexpected, []);
  });
  process.env.PI_CODING_AGENT_DIR = agentDir;
  mkdirSync(cwd); mkdirSync(agentDir);
  execFileSync('git', ['init', '-q', cwd]);
  execFileSync('git', ['-C', cwd, 'remote', 'add', 'origin', origin]);
  if (configured !== undefined) {
    mkdirSync(join(cwd, '.pi'));
    writeFileSync(join(cwd, '.pi/project.json'), JSON.stringify({ brokanProject: configured }));
  }
  const state = { tasks, failed: undefined, gate: undefined, worker: undefined, version: 1 };
  const git = (dir, ...args) => execFileSync('git', ['-C', dir, ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
  const workerRoot = join(agentDir, 'factory-worktrees', project);
  if (parallel) {
    const bin = join(base, 'bin');
    mkdirSync(bin);
    const actualGit = execFileSync('which', ['git'], { encoding: 'utf8' }).trim();
    git(base, 'init', '-q', '--bare', 'remote.git');
    git(cwd, 'config', 'user.email', 'factory@example.invalid');
    git(cwd, 'config', 'user.name', 'Factory Fixture');
    git(cwd, 'switch', '-qc', 'dev');
    git(cwd, 'commit', '-qm', 'Fixture base', '--allow-empty');
    git(cwd, 'push', '-q', join(base, 'remote.git'), 'dev');
    writeFileSync(join(bin, 'git'), `#!/bin/sh
if [ "$1" = fetch ] && [ "$2" = --no-tags ] && [ "$3" = origin ] && [ "$#" = 4 ]; then
  exec ${JSON.stringify(actualGit)} fetch --no-tags "$PI_FACTORY_TEST_BASE/remote.git" "$4"
fi
exec ${JSON.stringify(actualGit)} "$@"
`);
    const workerFixture = fileURLToPath(new URL('./fixtures/pi-factory-worker.mjs', import.meta.url));
    const nativeArgs = [join(root, 'dist/bundle/cli.js'), '--offline', '--no-mcp', '--no-context-files', '--no-skills',
      '--no-extensions', '-e', fileURLToPath(new URL('./fixtures/pi-factory-native.ts', import.meta.url))];
    const args = parallel === 'native' ? nativeArgs : [workerFixture];
    writeFileSync(join(bin, 'pi'), `#!/bin/sh
exec ${[process.execPath, ...args].map(value => JSON.stringify(value)).join(' ')} "$@"
`);
    for (const file of ['git', 'pi']) chmodSync(join(bin, file), 0o700);
    process.env.PATH = `${bin}:${process.env.PATH}`;
    process.env.PI_FACTORY_TEST_BASE = base;
  }
  const server = createServer(async (req, res) => {
    const path = req.url;
    if (req.method !== 'GET') { unexpected.push(req.method); res.writeHead(405).end(); return; }
    if (parallel && path?.startsWith('/worker?')) {
      const params = new URL(path, 'http://127.0.0.1').searchParams;
      try {
        const result = await state.worker?.({ id: Number(params.get('id')), pid: Number(params.get('pid')), phase: params.get('phase') });
        res.writeHead(200).end(result ?? 'ready');
      } catch { res.writeHead(500).end(); }
      return;
    }
    reads.push(path);
    if (state.gate) await state.gate(path);
    if (path === state.failed) { res.writeHead(503).end(); return; }
    let body;
    if (path === '/api/changes') {
      body = { changes: `token-${state.version}` };
    } else if (path === `/api/board?project=${project}`) {
      body = { projects: [{ slug: project, archived: false, repos }, { slug: 'other', archived: false, repos: [] }], tasks: state.tasks };
    } else if (/^\/api\/tasks\/\d+$/.test(path)) {
      body = { task: state.tasks.find(task => task.id === Number(path.split('/').at(-1))) };
    } else { unexpected.push(path); res.writeHead(404).end(); return; }
    res.writeHead(200, { 'content-type': 'application/json' }).end(JSON.stringify(body));
  });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  if (parallel) process.env.PI_FACTORY_TEST_URL = `http://127.0.0.1:${server.address().port}`;
  t.after(() => new Promise(resolve => { server.close(resolve); server.closeAllConnections(); }));
  globalThis.fetch = (url, init) => {
    const target = new URL(url);
    assert.equal(target.origin, 'http://127.0.0.1:1317', 'no external HTTP');
    return originalFetch(`http://127.0.0.1:${server.address().port}${target.pathname}${target.search}`, init);
  };

  async function open(respond) {
    const calls = [], notices = [], errors = [], pendingNotices = [];
    const settingsManager = SettingsManager.inMemory({ compaction: { enabled: false } }, { projectTrusted: trusted });
    const resourceLoader = new DefaultResourceLoader({ cwd, agentDir, settingsManager,
      additionalExtensionPaths: [extensionPath], noSkills: true, noContextFiles: true, noPromptTemplates: true, noThemes: true });
    await resourceLoader.reload();
    assert.deepEqual(resourceLoader.getExtensions().errors, []);
    const modelRuntime = await ModelRuntime.create({ credentials: new InMemoryCredentialStore(),
      modelsPath: null, modelsStorePath: join(base, 'models-cache.json'), refreshOnCreate: false });
    const faux = fauxProvider({ models: [{ id: 'fixture', reasoning: true }] });
    modelRuntime.registerNativeProvider(faux.provider);
    const model = faux.getModel();
    const { session } = await createAgentSession({ cwd, agentDir, resourceLoader, settingsManager, modelRuntime,
      model, thinkingLevel: 'low', sessionManager: SessionManager.inMemory(cwd), noTools: 'all' });
    sessions.push(session);
    await session.bindExtensions({ mode: 'rpc', uiContext: {
      notify: message => {
        notices.push(message);
        for (const [predicate, resolve] of pendingNotices) if (predicate(message)) resolve(message);
      }, setStatus: () => {},
    }, abortHandler: () => { void session.abort(); }, onError: error => errors.push(error) });
    faux.setResponses(Array.from({ length: 32 }, () => async (context, { signal }) => {
      const text = context.messages.filter(message => message.role === 'user').at(-1)?.content;
      const prompt = typeof text === 'string' ? text : text?.map(block => block.text).join('\n');
      calls.push(prompt);
      return fauxAssistantMessage(await respond(prompt, calls.length, signal));
    }));
    const waitNotice = predicate => new Promise(resolve => {
      const previous = notices.find(predicate);
      if (previous) resolve(previous);
      else pendingNotices.push([predicate, resolve]);
    });
    return { session, calls, notices, errors, model, waitNotice };
  }
  const status = (id, value) => { state.tasks.find(task => task.id === id).status = value; };
  const deliver = (id, { push = true, cleanup = true, provenance = true } = {}) => {
    const branch = `task/factory-${project}-${id}`;
    const location = join(workerRoot, String(id));
    // Apply the prepared commit on the serial dev branch, changing its SHA as a rebase can.
    const prepared = git(cwd, 'rev-parse', branch);
    git(cwd, 'cherry-pick', branch);
    if (!provenance) git(cwd, 'commit', '--amend', '-qm', 'Unlinked commit');
    if (provenance) git(cwd, 'commit', '--amend', '--no-edit', '--trailer', `Factory-Prepared: ${prepared}`);
    const sha = git(cwd, 'rev-parse', 'HEAD');
    if (push) git(cwd, 'push', '-q', join(base, 'remote.git'), 'dev');
    if (cleanup) { git(cwd, 'worktree', 'remove', location); git(cwd, 'branch', '-D', branch); }
    return sha;
  };
  return { open, state, reads, status, deliver, worktree: id => join(workerRoot, String(id)), locked: () => existsSync(join(agentDir, lockName)) };
}

function settled(session) {
  return new Promise(resolve => {
    const unsubscribe = session.subscribe(event => {
      if (event.type === 'agent_settled') { unsubscribe(); resolve(event); }
    });
  });
}
function taskFor(prompt) { return Number(/factory-fixture#(\d+)/.exec(prompt)?.[1]); }
async function run(session, command = '/factory') {
  const end = settled(session);
  await session.prompt(command);
  return end;
}

const options = { timeout: 12_000 };
test('queue: board order, eligible identity, fresh read before each handoff and a refresh when the batch runs dry', options, async t => {
  const f = await fixture(t, { tasks: [makeTask(2, 'todo'), makeTask(1, 'doing'), makeTask(3, 'todo', true),
    makeTask(4, 'review'), makeTask(5, 'todo')] });
  const s = await f.open((prompt, count) => {
    const id = taskFor(prompt);
    if (count === 1) {
      assert.equal(id, 1);
      f.state.tasks.push(makeTask(6, 'doing'));
      f.state.tasks.find(task => task.id === 5).human = true;
    }
    f.status(id, 'review');
    return 'Handoff recorded.';
  });
  await run(s.session);
  // Task 6 was added mid-batch: the refresh picks it up; task 5 turned human and is skipped.
  assert.deepEqual(s.calls.map(taskFor), [1, 2, 6]);
  const board = `/api/board?project=${project}`;
  assert.deepEqual(f.reads, [board, '/api/tasks/1', '/api/tasks/1', '/api/tasks/2', '/api/tasks/2', '/api/tasks/5',
    board, '/api/tasks/6', '/api/tasks/6', board]);
  assert.deepEqual(s.errors, []);
  assert.ok(s.notices.some(x => x.includes('3 handed off. Queue exhausted.')));
  assert.equal(f.locked(), false);
  assert.equal(s.session.model.id, s.model.id);
  assert.equal(s.session.thinkingLevel, 'low');
});

test('entry: explicit plain prompt supports one task and done readback', options, async t => {
  const f = await fixture(t, { repos: [], configured: project });
  const s = await f.open(prompt => { f.status(taskFor(prompt), 'done'); return 'Already done.'; });
  await run(s.session, `factory run ${project}#2`);
  assert.deepEqual(s.calls.map(taskFor), [2]);
  assert.deepEqual(f.reads, [`/api/board?project=${project}`, '/api/tasks/2', '/api/tasks/2']);
  assert.equal(f.locked(), false);
});

test('scope: mismatched requested project or repository cannot dispatch', options, async t => {
  const f = await fixture(t, { origin: 'https://github.com/unrelated/factory-fixture.git' });
  const s = await f.open(() => assert.fail('no turn allowed'));
  await s.session.prompt('/factory other');
  assert.deepEqual(f.reads, []);
  await s.session.prompt('/factory');
  assert.equal(f.reads.length, 1);
  assert.ok(s.notices.some(x => x.includes('not linked')));
  assert.equal(s.calls.length, 0);
  assert.equal(f.locked(), false);
});

test('scope: untrusted checkout does not read Brokan', options, async t => {
  const f = await fixture(t, { trusted: false });
  const s = await f.open(() => assert.fail('no turn allowed'));
  await s.session.prompt('/factory');
  assert.deepEqual(f.reads, []);
  assert.ok(s.notices.some(x => x.includes('trusted project')));
});

test('scope: reject cross-project task data rather than execute it', options, async t => {
  const f = await fixture(t, { tasks: [makeTask(1, 'doing', false, 'other')] });
  const s = await f.open(() => assert.fail('no turn allowed'));
  await s.session.prompt('/factory');
  assert.ok(s.notices.some(x => x.includes('identity or state mismatch')));
  assert.equal(f.locked(), false);
});

test('idle: ordinary text never reads Brokan', options, async t => {
  const f = await fixture(t);
  const s = await f.open(() => 'Answer.');
  await s.session.prompt('What is a factory run in Brokan?');
  assert.deepEqual(s.calls, ['What is a factory run in Brokan?']);
  assert.deepEqual(f.reads, []);
  assert.equal(f.locked(), false);
});

test('retry: re-read same task, then stop before selecting another if unchanged', options, async t => {
  const f = await fixture(t);
  const s = await f.open(() => 'Work remains.');
  await run(s.session);
  assert.deepEqual(s.calls.map(taskFor), [1, 1, 1, 1]);
  assert.match(s.calls.at(-1), /Continue only/);
  assert.deepEqual(f.reads.slice(1), Array(5).fill('/api/tasks/1'));
  assert.ok(s.notices.some(x => x.includes('continuation limit reached')));
  assert.equal(f.locked(), false);
});

test('blocker: pause marker stops without touching another task', options, async t => {
  const f = await fixture(t);
  const s = await f.open(() => 'Required credential missing.\nFACTORY_PAUSE');
  await run(s.session, 'Brokandagi todo va doing tasklarni oxirigacha bajar.');
  assert.deepEqual(s.calls.map(taskFor), [1]);
  assert.ok(s.notices.some(x => x.includes('reported blocker')));
  assert.equal(f.locked(), false);
});

test('error: board readback failure cannot trigger continuation or next task', options, async t => {
  const f = await fixture(t);
  const s = await f.open(() => { f.state.failed = '/api/tasks/1'; return 'Handoff maybe happened.'; });
  await run(s.session);
  assert.deepEqual(s.calls.map(taskFor), [1]);
  assert.ok(s.notices.some(x => x.includes('Brokan response unavailable')));
  assert.equal(f.locked(), false);
});

for (const action of ['stop', 'abort', 'steer']) {
  test(`stop (${action}): native Pi interruption does not auto-continue`, options, async t => {
    const f = await fixture(t);
    const entered = Promise.withResolvers(), finish = Promise.withResolvers();
    const s = await f.open(async (_prompt, count, signal) => {
      if (count === 1) {
        signal.addEventListener('abort', () => finish.resolve(), { once: true });
        entered.resolve();
        await finish.promise;
      }
      return 'Stopped.';
    });
    t.after(() => finish.resolve());
    const task = run(s.session);
    await entered.promise;
    if (action === 'stop') await s.session.prompt('/factory stop');
    else if (action === 'abort') { const aborted = s.session.abort(); finish.resolve(); await aborted; }
    else await s.session.steer('Use this new direction.', undefined, { source: 'rpc' });
    finish.resolve();
    await task;
    assert.deepEqual(s.calls.map(taskFor), action === 'steer' ? [1, NaN] : [1]);
    assert.equal(f.locked(), false);
    assert.deepEqual(s.errors, []);
  });
}

test('lock: concurrent Factory session cannot read or dispatch same project', options, async t => {
  const f = await fixture(t);
  const entered = Promise.withResolvers(), finish = Promise.withResolvers();
  const first = await f.open(async () => { entered.resolve(); await finish.promise; return 'Blocked.\nFACTORY_PAUSE'; });
  const second = await f.open(() => assert.fail('no concurrent run'));
  t.after(() => finish.resolve());
  const task = run(first.session);
  await entered.promise;
  const previous = f.reads.slice();
  await second.session.prompt('/factory');
  assert.deepEqual(f.reads, previous);
  assert.ok(second.notices.some(x => x.includes('lock already held')));
  finish.resolve();
  await task;
  assert.equal(f.locked(), false);
});

test('stop: discovery cancellation releases the project lock without loading a task', options, async t => {
  const f = await fixture(t);
  const s = await f.open(() => assert.fail('no turn after stop'));
  const entered = Promise.withResolvers(), finish = Promise.withResolvers();
  f.state.gate = async () => { entered.resolve(); await finish.promise; };
  t.after(() => finish.resolve());
  const start = s.session.prompt('/factory');
  await entered.promise;
  assert.equal(f.locked(), true);
  await s.session.prompt('/factory stop');
  finish.resolve();
  await start;
  assert.deepEqual(f.reads, [`/api/board?project=${project}`]);
  assert.equal(f.locked(), false);
  assert.deepEqual(s.errors, []);
});

const parallelOptions = { timeout: 20_000, skip: process.platform === 'win32' };

test('parallel: five isolated workers per wave, then one verified delivery at a time', parallelOptions, async t => {
  const f = await fixture(t, { parallel: true, tasks: [makeTask(1, 'todo'), makeTask(2, 'todo'),
    makeTask(3, 'todo'), makeTask(4, 'todo'), makeTask(5, 'todo'), makeTask(6, 'doing'), makeTask(7, 'doing', true)] });
  const firstWave = Promise.withResolvers(), active = new Set(), seen = [], delivered = [];
  t.after(() => firstWave.resolve());
  let peak = 0;
  f.state.worker = async ({ id, pid, phase }) => {
    if (phase !== 'prompt') return;
    assert.ok(existsSync(join(f.worktree(id), '.git')));
    active.add(pid);
    seen.push(id);
    peak = Math.max(peak, active.size);
    if (seen.length === 5) {
      f.state.tasks.push(makeTask(8, 'todo'));
      firstWave.resolve();
    }
    if (id === 5) assert.deepEqual(delivered, [6, 1, 2, 3, 4]);
    await firstWave.promise;
    return 'ready';
  };
  const s = await f.open(prompt => {
    const id = taskFor(prompt);
    assert.match(prompt, /Factory parallel delivery/);
    assert.match(prompt, /independently verify the exact delivered commit is on origin\/dev/);
    for (const pid of active) assert.throws(() => process.kill(pid, 0), { code: 'ESRCH' });
    active.clear();
    assert.equal(seen.includes(id), true);
    const sha = f.deliver(id);
    f.status(id, 'review');
    delivered.push(id);
    return `Verified.\nFACTORY_DELIVERED ${sha}`;
  });
  await run(s.session, '/factory parallel');
  assert.equal(peak, 5);
  // Task 8 was added during the first wave and runs in a wave after the snapshot.
  assert.deepEqual(seen.toSorted((a, b) => a - b), [1, 2, 3, 4, 5, 6, 8]);
  assert.deepEqual(delivered, [6, 1, 2, 3, 4, 5, 8]);
  assert.deepEqual(s.errors, []);
  assert.ok(s.notices.some(x => x.includes('7 handed off. Queue exhausted.')));
  assert.equal(f.locked(), false);
  assert.equal(s.session.thinkingLevel, 'low');
});

test('parallel: explicit prompt selects width two; stop reaps workers and retains their worktrees', parallelOptions, async t => {
  const f = await fixture(t, { parallel: true, tasks: Array.from({ length: 5 }, (_, i) => makeTask(i + 1, 'todo')) });
  const entered = Promise.withResolvers(), finish = Promise.withResolvers(), pids = [];
  t.after(() => finish.resolve());
  f.state.worker = async ({ pid, phase }) => {
    if (phase !== 'prompt') return;
    pids.push(pid);
    if (pids.length === 2) entered.resolve();
    await finish.promise;
  };
  const s = await f.open(() => assert.fail('no model turn after stop'));
  const starting = s.session.prompt('factory run parallel 2');
  await entered.promise;
  assert.equal(f.locked(), true);
  await s.session.prompt('/factory stop');
  await starting;
  assert.equal(pids.length, 2);
  for (const pid of pids) assert.throws(() => process.kill(pid, 0), { code: 'ESRCH' });
  assert.ok(existsSync(f.worktree(1)));
  assert.ok(existsSync(f.worktree(2)));
  assert.equal(existsSync(f.worktree(3)), false);
  assert.deepEqual(s.calls, []);
  assert.equal(f.locked(), false);
  finish.resolve();
});

for (const problem of ['mismatch', 'interactive', 'uncommitted', 'pause']) {
  test(`parallel: worker ${problem} prevents delivery and further waves`, parallelOptions, async t => {
    const f = await fixture(t, { parallel: true, tasks: Array.from({ length: 3 }, (_, i) => makeTask(i + 1, 'todo')) });
    const pids = new Set(), prompts = [];
    f.state.worker = ({ id, pid, phase }) => {
      pids.add(pid);
      if (phase === 'state') return problem === 'mismatch' ? 'mismatch' : undefined;
      prompts.push(id);
      return problem;
    };
    const s = await f.open(() => assert.fail('no delivery on bad preparation'));
    await s.session.prompt('/factory parallel 2');
    await s.waitNotice(text => text.includes('Worktree retained if created.'));
    // An immediate status command verifies no next turn was queued.
    await s.session.prompt('/factory status');
    assert.ok(pids.size > 0);
    if (problem === 'mismatch') assert.equal(prompts.length, 0);
    else assert.ok(prompts.length > 0);
    const message = { mismatch: 'preserve the selected', interactive: 'interactive input',
      uncommitted: 'clean candidate', pause: 'ready candidate' }[problem];
    assert.ok(s.notices.some(x => x.includes(message)), s.notices.join('\n'));
    for (const pid of pids) assert.throws(() => process.kill(pid, 0), { code: 'ESRCH' });
    assert.equal(existsSync(f.worktree(3)), false);
    assert.deepEqual(s.calls, []);
    assert.equal(f.locked(), false);
  });
}

for (const problem of ['not-reviewed', 'not-pushed', 'not-cleaned', 'unrelated-receipt']) {
  test(`parallel: ${problem} readback stops before the next serial delivery`, parallelOptions, async t => {
    const f = await fixture(t, { parallel: true, tasks: [makeTask(1, 'todo'), makeTask(2, 'todo'), makeTask(3, 'todo')] });
    const s = await f.open(prompt => {
      assert.equal(taskFor(prompt), 1);
      if (problem !== 'not-reviewed') f.status(1, 'review');
      const sha = f.deliver(1, { push: problem !== 'not-pushed', cleanup: problem !== 'not-cleaned', provenance: problem !== 'unrelated-receipt' });
      return `Claimed.\nFACTORY_DELIVERED ${sha}`;
    });
    await run(s.session, '/factory parallel 2');
    assert.equal(s.calls.length, 1);
    assert.ok(s.notices.some(x => /not verified|Could not confirm/.test(x)), s.notices.join('\n'));
    assert.ok(existsSync(f.worktree(2)));
    assert.equal(existsSync(f.worktree(3)), false);
    assert.equal(f.locked(), false);
  });
}

test('parallel: invalid width is rejected without dispatch', parallelOptions, async t => {
  const f = await fixture(t);
  const s = await f.open(() => assert.fail('no turn allowed'));
  await s.session.prompt('/factory parallel 6');
  await s.session.prompt('factory run parallel 1');
  assert.deepEqual(f.reads, []);
  assert.equal(s.notices.filter(note => note.includes('Usage: /factory parallel [2-5]')).length, 2);
});


test('parallel: actual Pi RPC worker can prepare a committed candidate with a native faux model', parallelOptions, async t => {
  const f = await fixture(t, { parallel: 'native', tasks: [makeTask(1, 'doing')] });
  const s = await f.open(prompt => {
    assert.equal(taskFor(prompt), 1);
    assert.ok(existsSync(join(f.worktree(1), 'native-candidate.txt')));
    const sha = f.deliver(1);
    f.status(1, 'review');
    return `Native worker delivered.\nFACTORY_DELIVERED ${sha}`;
  });
  const finished = Promise.race([
    settled(s.session),
    s.waitNotice(text => text.includes('Worktree retained if created.')).then(error => assert.fail(error)),
  ]);
  await s.session.prompt('/factory parallel 2');
  await finished;
  assert.deepEqual(s.calls.map(taskFor), [1]);
  assert.equal(f.locked(), false);
});

const watchOptions = { timeout: 15_000 };
async function until(predicate, label, ms = 5000) {
  const end = Date.now() + ms;
  while (!predicate()) {
    if (Date.now() > end) assert.fail(`timed out waiting for ${label}`);
    await new Promise(resolve => setTimeout(resolve, 10));
  }
}
function fastWatch(t) {
  const prior = process.env.MEGAI_FACTORY_WATCH_SECONDS;
  process.env.MEGAI_FACTORY_WATCH_SECONDS = '0.05';
  t.after(() => { if (prior === undefined) delete process.env.MEGAI_FACTORY_WATCH_SECONDS; else process.env.MEGAI_FACTORY_WATCH_SECONDS = prior; });
}
const boards = reads => reads.filter(path => path.startsWith('/api/board')).length;

test('watch: idle session starts tasks added later and reads the board only when Brokan changed', watchOptions, async t => {
  fastWatch(t);
  const f = await fixture(t, { tasks: [makeTask(1, 'doing')] });
  const s = await f.open(prompt => { f.status(taskFor(prompt), 'review'); f.state.version++; return 'Handoff recorded.'; });
  await s.session.prompt('/factory watch');
  await until(() => s.calls.length === 1 && !f.locked() && f.reads.filter(p => p === '/api/changes').length >= 4, 'first task and idle polls');
  const before = boards(f.reads);
  await new Promise(resolve => setTimeout(resolve, 250));
  assert.equal(boards(f.reads), before, 'no board read while the change token is unchanged');
  f.state.tasks.push(makeTask(2, 'todo'));
  f.state.version++;
  await until(() => s.calls.length === 2, 'task added while watching');
  assert.deepEqual(s.calls.map(taskFor), [1, 2]);
  await until(() => !f.locked(), 'lock release after the batch');
  await s.session.prompt('/factory status');
  assert.ok(s.notices.some(x => x.startsWith('Factory: Watching, 0 skipped.')), s.notices.join('\n'));
  await s.session.prompt('/factory stop');
  assert.ok(s.notices.some(x => x.includes('Watch stopped.')));
  const polls = f.reads.length;
  await new Promise(resolve => setTimeout(resolve, 200));
  assert.equal(f.reads.length, polls, 'no polling after stop');
  assert.deepEqual(s.errors, []);
  assert.equal(s.session.thinkingLevel, 'low');
});

test('watch: a blocked task is skipped until it changes while the rest of the queue continues', watchOptions, async t => {
  fastWatch(t);
  const f = await fixture(t, { tasks: [{ ...makeTask(1, 'doing'), updated_at: 'a', comments: 0 }, makeTask(2, 'todo')] });
  let fixed = false;
  const s = await f.open(prompt => {
    const id = taskFor(prompt);
    if (id === 1 && !fixed) return 'Needs the vendor key.\nFACTORY_PAUSE';
    f.status(id, 'review');
    f.state.version++;
    return 'Handoff recorded.';
  });
  await s.session.prompt('factory watch');
  await until(() => s.calls.length === 2 && !f.locked(), 'blocked task then the next one');
  assert.deepEqual(s.calls.map(taskFor), [1, 2]);
  assert.ok(s.notices.some(x => x.includes('#1 skipped until it changes')), s.notices.join('\n'));
  await new Promise(resolve => setTimeout(resolve, 250));
  assert.equal(s.calls.length, 2, 'unchanged blocked task is not retried');
  fixed = true;
  f.state.tasks[0].comments = 1; // A new comment alone re-enables the task.
  f.state.version++;
  await until(() => s.calls.length === 3, 'retry after the task changed');
  assert.equal(taskFor(s.calls[2]), 1);
  await s.session.prompt('/factory stop');
  await until(() => !f.locked(), 'lock release');
});

test('watch: typed input ends watching; an invalid target never arms it', watchOptions, async t => {
  fastWatch(t);
  const f = await fixture(t, { tasks: [] });
  const s = await f.open(() => 'Answer.');
  await s.session.prompt(`/factory watch ${project}#2`);
  assert.ok(s.notices.some(x => x.includes('Usage: /factory watch')));
  assert.deepEqual(f.reads, []);
  await s.session.prompt('/factory watch');
  await until(() => f.reads.length >= 2, 'polling');
  await s.session.prompt('Explain the build failure');
  assert.ok(s.notices.some(x => x.includes('Watch stopped by new input')));
  const polls = f.reads.length;
  await new Promise(resolve => setTimeout(resolve, 200));
  assert.equal(f.reads.length, polls);
  assert.deepEqual(s.calls, ['Explain the build failure']);
  assert.equal(f.locked(), false);
});

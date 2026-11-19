import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { once } from 'node:events';
import { mkdtempSync, mkdirSync, realpathSync, rmSync, writeFileSync, existsSync } from 'node:fs';
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
  trusted = true, configured, origin = 'https://github.com/test/factory-fixture.git' } = {}) {
  const base = realpathSync(mkdtempSync(join(tmpdir(), 'pi-factory-sdk-')));
  const cwd = join(base, 'checkout'), agentDir = join(base, 'agent');
  const priorDir = process.env.PI_CODING_AGENT_DIR, originalFetch = globalThis.fetch;
  const sessions = [], reads = [], unexpected = [];
  t.after(() => {
    for (const session of sessions) session.dispose();
    globalThis.fetch = originalFetch;
    if (priorDir === undefined) delete process.env.PI_CODING_AGENT_DIR;
    else process.env.PI_CODING_AGENT_DIR = priorDir;
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
  const state = { tasks, failed: undefined, gate: undefined };
  const server = createServer(async (req, res) => {
    const path = req.url;
    if (req.method !== 'GET') { unexpected.push(req.method); res.writeHead(405).end(); return; }
    reads.push(path);
    if (state.gate) await state.gate(path);
    if (path === state.failed) { res.writeHead(503).end(); return; }
    let body;
    if (path === `/api/board?project=${project}`) {
      body = { projects: [{ slug: project, archived: false, repos }, { slug: 'other', archived: false, repos: [] }], tasks: state.tasks };
    } else if (/^\/api\/tasks\/\d+$/.test(path)) {
      body = { task: state.tasks.find(task => task.id === Number(path.split('/').at(-1))) };
    } else { unexpected.push(path); res.writeHead(404).end(); return; }
    res.writeHead(200, { 'content-type': 'application/json' }).end(JSON.stringify(body));
  });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(() => new Promise(resolve => { server.close(resolve); server.closeAllConnections(); }));
  globalThis.fetch = (url, init) => {
    const target = new URL(url);
    assert.equal(target.origin, 'http://127.0.0.1:1317', 'no external HTTP');
    return originalFetch(`http://127.0.0.1:${server.address().port}${target.pathname}${target.search}`, init);
  };

  async function open(respond) {
    const calls = [], notices = [], errors = [];
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
      notify: message => notices.push(message), setStatus: () => {},
    }, abortHandler: () => { void session.abort(); }, onError: error => errors.push(error) });
    faux.setResponses(Array.from({ length: 32 }, () => async (context, { signal }) => {
      const text = context.messages.filter(message => message.role === 'user').at(-1)?.content;
      const prompt = typeof text === 'string' ? text : text?.map(block => block.text).join('\n');
      calls.push(prompt);
      return fauxAssistantMessage(await respond(prompt, calls.length, signal));
    }));
    return { session, calls, notices, errors, model };
  }
  const status = (id, value) => { state.tasks.find(task => task.id === id).status = value; };
  return { open, state, reads, status, locked: () => existsSync(join(agentDir, lockName)) };
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
test('queue: fixed snapshot, board order, eligible identity and fresh read before each handoff', options, async t => {
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
  assert.deepEqual(s.calls.map(taskFor), [1, 2]);
  assert.deepEqual(f.reads, [`/api/board?project=${project}`, '/api/tasks/1', '/api/tasks/1', '/api/tasks/2', '/api/tasks/2', '/api/tasks/5']);
  assert.deepEqual(s.errors, []);
  assert.ok(s.notices.some(x => x.includes('2 handed off. Queue exhausted.')));
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

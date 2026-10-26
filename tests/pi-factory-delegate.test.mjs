import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, mkdtempSync, readdirSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { collectTasks, decodeTool, delegate, preflightPaseo, runWorker, selectTasks, workerPrompt } from '../pi-defaults/extensions/megai-factory/runner.mjs';

const ids = ['a'.repeat(32), 'b'.repeat(32), 'c'.repeat(32)];
const task = (id, status = 'in_progress') => ({ id, status, title: `Task ${id[0]}`, file_path: `MEGAI/Task ${id[0]}.md`,
  description: 'Implement feature; acceptance: focused test passes', file_modified: '2026-10-26T00:00:00Z' });
const reply = x => ({ content: [{ type: 'text', text: JSON.stringify(x) }] });

function fixture(rows = ids.slice(0, 2).map(id => task(id))) {
  const root = mkdtempSync(join(tmpdir(), 'factory-test-'));
  const cwd = join(root, 'MEGAI');
  const store = join(root, 'receipts');
  const calls = [], launched = [];
  let concurrent = 0, maxConcurrent = 0;
  const git = async (_cwd, args) => {
    calls.push(args);
    const key = args.join(' ');
    if (key === 'rev-parse --show-toplevel') return cwd;
    if (key === 'symbolic-ref --short HEAD') return 'dev';
    if (key === 'status --porcelain=v1') return '';
    if (key === 'remote get-url origin' || key === 'remote get-url --push origin') return 'https://github.com/example/MEGAI.git';
    if (key === 'worktree list --porcelain') return `worktree ${cwd}\nHEAD ${'f'.repeat(40)}\nbranch refs/heads/dev\n`;
    if (key === 'rev-parse dev') return 'f'.repeat(40);
    if (key.startsWith('branch --list')) return '';
    if (key.startsWith('worktree add')) return '';
    throw Error(`Unexpected Git call ${key}`);
  };
  const deps = { cwd, root: store, folder: 'MEGAI', selection: 'all', concurrency: 2,
    model: 'provider/model', thinking: 'high', git, preflight: async () => {},
    query: async args => reply({ items: rows, total: rows.length, truncated: false }),
    get: async ({ file_path }) => reply(rows.find(row => row.file_path === file_path)),
    start: async ({ file_path, status, if_file_modified }) => {
      const item = rows.find(row => row.file_path === file_path);
      assert.equal(if_file_modified, item.file_modified);
      item.status = status; item.file_modified = '2026-10-26T00:01:00Z';
      return reply(item);
    },
    launch: async ({ task: item, tree }) => {
      concurrent++; maxConcurrent = Math.max(maxConcurrent, concurrent);
      launched.push({ item, tree });
      await new Promise(resolve => setTimeout(resolve, 10));
      concurrent--;
      return { status: 'launched-unverified', agentId: item.id, workspaceId: `wks_${item.id}`, terminalId: `term_${item.id}` };
    },
  };
  return { deps, calls, launched, store, cleanup: () => rmSync(root, { recursive: true, force: true }), max: () => maxConcurrent };
}

test('complete Pellet pagination and explicit UUID selection; fail closed on changing/incomplete pages', async () => {
  let count = 0;
  const pages = [reply({ items: [task(ids[0])], total: 2, truncated: true, next_cursor: 'next' }),
    reply({ items: [task(ids[1])], total: 2, truncated: false })];
  const rows = await collectTasks(async args => {
    assert.equal(args.conditions[0].value, 'MEGAI');
    if (count === 1) assert.equal(args.cursor, 'next');
    return pages[count++];
  }, 'MEGAI');
  assert.deepEqual(selectTasks(rows, `${ids[1]},${ids[0]}`).map(x => x.id), [ids[1], ids[0]]);
  assert.deepEqual(selectTasks(rows, 'all').map(x => x.id), [ids[0], ids[1]]);
  assert.throws(() => selectTasks(rows, `${ids[0]},${ids[0]}`), /distinct/);
  assert.throws(() => selectTasks(rows, 'MEGAI-12'), /UUIDs/);
  await assert.rejects(collectTasks(async () => reply({ items: [task(ids[0])], total: 2, truncated: false }), 'MEGAI'), /count changed/);
  await assert.rejects(collectTasks(async () => reply({ items: [task(ids[0])], total: 2, truncated: true }), 'MEGAI'), /cursor/);
  assert.throws(() => decodeTool({ isError: true }), /query failed/);
});

test('independent reservations, serial Git preparation, concurrent workers, unchanged primary dev', async () => {
  const f = fixture([task(ids[0], 'open'), task(ids[1])]);
  try {
    const results = await delegate(f.deps);
    assert.deepEqual(results.map(x => x.status), ['launched-unverified', 'launched-unverified']);
    assert.equal(f.max(), 2);
    assert.equal(f.launched.length, 2);
    assert.notEqual(f.launched[0].tree, f.launched[1].tree);
    assert.deepEqual(f.calls.filter(x => x.slice(0, 2).join(' ') === 'worktree add').length, 2);
    assert.equal(readdirSync(f.store).length, 2);
    assert.equal(JSON.parse(readFileSync(join(f.store, `MEGAI-${ids[0]}.json`))).taskId, ids[0]);
    await assert.rejects(delegate(f.deps), /Previous\/uncertain delegated worker/);
    assert.equal(f.launched.length, 2, 'must never double-launch a task');
  } finally { f.cleanup(); }
});

test('five distinct tasks run concurrently; six workers are refused before mutation', async () => {
  const rows = Array.from({ length: 5 }, (_, i) => task(String(i + 1).repeat(32)));
  const f = fixture(rows);
  f.deps.concurrency = 5;
  try {
    const results = await delegate(f.deps);
    assert.equal(results.length, 5);
    assert(results.every(result => result.status === 'launched-unverified'));
    assert.equal(f.max(), 5);
    assert.equal(new Set(f.launched.map(worker => worker.tree)).size, 5);
    assert.equal(new Set(results.map(result => result.agentId)).size, 5);
    assert.equal(new Set(results.map(result => result.workspaceId)).size, 5);
    assert.equal(new Set(results.map(result => result.terminalId)).size, 5);
    assert.equal(readdirSync(f.store).length, 5);
  } finally { f.cleanup(); }

  const rejected = fixture(rows.map(row => ({ ...row })));
  rejected.deps.concurrency = 6;
  try {
    await assert.rejects(delegate(rejected.deps), /Concurrency must be 1–5/);
    assert.equal(rejected.launched.length, 0);
    assert.equal(existsSync(rejected.store), false);
  } finally { rejected.cleanup(); }
});

test('fail closed before mutation for foreign, stale, ambiguous and acceptance-free tasks', async () => {
  for (const change of [
    f => { f.deps.folder = 'OTHER'; },
    f => { f.deps.get = async () => reply({ ...task(ids[0]), depends_on: [{ id: ids[1] }] }); },
    f => { f.deps.get = async () => reply({ ...task(ids[0]), description: '' }); },
    f => { f.deps.query = async () => reply({ items: [{ ...task(ids[0]), file_path: 'OTHER/escape.md' }], total: 1, truncated: false }); },
    f => { const original = f.deps.git; f.deps.git = async (...args) => args[1].join(' ') === 'status --porcelain=v1' ? ' M foreign' : original(...args); },
  ]) {
    const f = fixture([task(ids[0])]);
    // Last case can reject on dirty dev without needing to evaluate fallback.
    change(f);
    try { await assert.rejects(delegate(f.deps)); assert.equal(f.launched.length, 0); assert.equal(existsSync(f.store), false); }
    finally { f.cleanup(); }
  }
});

test('Pellet drift after worktree preparation blocks worker and retains receipt', async () => {
  const f = fixture([task(ids[0])]);
  const original = f.deps.get;
  let calls = 0;
  f.deps.get = async (...args) => {
    const result = await original(...args);
    return ++calls === 2 ? reply({ ...JSON.parse(result.content[0].text), file_modified: 'drifted' }) : result;
  };
  try {
    const [result] = await delegate(f.deps);
    assert.equal(result.status, 'blocked');
    assert.match(result.reason, /task drift/);
    assert.equal(f.launched.length, 0);
    assert.equal(readdirSync(f.store).length, 1);
  } finally { f.cleanup(); }
});

test('Paseo preflight validates reachable native Pi and exact selected model/thinking before Git writes', async () => {
  const calls = [];
  const paseo = async (_cwd, args) => {
    calls.push(args);
    if (args.join(' ') === 'status --json') return JSON.stringify({ connectedDaemon: 'reachable', providers: [{ provider: 'pi', available: true }] });
    if (args.join(' ') === 'provider models pi --json') return JSON.stringify([{ id: 'provider/model', thinkingOptionIds: ['high'] }]);
    throw Error('unexpected CLI');
  };
  await preflightPaseo('provider/model', 'high', paseo);
  await assert.rejects(preflightPaseo('provider/other', 'high', paseo), /not available/);
  await assert.rejects(preflightPaseo('provider/model', 'low', paseo), /thinking/);
  assert.equal(calls.length, 6);
});

test('real launcher creates a visible Paseo workspace, native Pi agent and terminal in its own worktree', async () => {
  const root = mkdtempSync(join(tmpdir(), 'factory-paseo-'));
  const tree = join(root, 'task-tree');
  const calls = [], agents = [], workspaces = [], terminals = [];
  const terminalId = '12345678-1234-1234-1234-123456789abc';
  const agentId = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
  const paseo = async (cwd, args) => {
    calls.push({ cwd, args });
    const key = args.slice(0, 2).join(' ');
    if (key === 'workspace create') {
      workspaces.push({ workspaceId: 'wks_task_1', cwd: tree, isolation: 'local', background: false });
      return JSON.stringify({ workspaceId: 'wks_task_1' });
    }
    if (key === 'workspace ls') return JSON.stringify(workspaces);
    if (key === 'agent run') {
      agents.push({ Id: agentId, Cwd: tree, Provider: 'pi', Model: 'provider/model', Thinking: 'high', Status: 'running' });
      return JSON.stringify({ agentId });
    }
    if (key === 'agent inspect') return JSON.stringify(agents[0]);
    if (key === 'agent ls') return JSON.stringify([{ id: agentId, cwd: tree, status: 'running' }]);
    if (key === 'terminal create') {
      terminals.push({ id: terminalId, workspaceId: 'wks_task_1', cwd: tree });
      return JSON.stringify({ terminalId });
    }
    if (key === 'terminal ls') return JSON.stringify(terminals);
    throw Error(`Unexpected Paseo call ${key}`);
  };
  try {
    const result = await runWorker({ task: task(ids[0]), tree, model: 'provider/model', thinking: 'high',
      receipt: join(root, 'receipt.json'), paseo });
    assert.equal(result.status, 'launched-unverified');
    assert.equal(result.agentId, agentId);
    assert.equal(result.workspaceId, 'wks_task_1');
    assert.equal(result.terminalId, terminalId);
    const created = calls.find(x => x.args.slice(0, 2).join(' ') === 'workspace create');
    assert.deepEqual(created.args.slice(0, 4), ['workspace', 'create', '--isolation', 'local']);
    assert(created.args.includes('--no-background'));
    assert.equal(created.args[created.args.indexOf('--path') + 1], tree);
    const launched = calls.find(x => x.args.slice(0, 2).join(' ') === 'agent run');
    assert(launched.args.includes('--no-wait'));
    assert.equal(launched.args[launched.args.indexOf('--workspace') + 1], 'wks_task_1');
    assert.equal(launched.args[launched.args.indexOf('--cwd') + 1], tree);
    assert.equal(launched.args[launched.args.indexOf('--provider') + 1], 'pi');
    assert.equal(launched.args[launched.args.indexOf('--model') + 1], 'provider/model');
    assert.equal(launched.args[launched.args.indexOf('--thinking') + 1], 'high');
    assert.match(launched.args.at(-1), /Implement ONLY/);
    assert(!calls.some(x => x.args.includes('stop') || x.args.includes('archive') || x.args.includes('kill')));
    assert.equal(readdirSync(root).filter(x => x.endsWith('jsonl')).length, 1);
    const events = readFileSync(result.log, 'utf8');
    assert.match(events, /wks_task_1/);
    assert.match(events, new RegExp(agentId));
    assert.match(events, new RegExp(terminalId));
  } finally { rmSync(root, { recursive: true, force: true }); }
});

test('uncertain Paseo launch retains workspace evidence and never invents an agent or kills a session', async () => {
  const root = mkdtempSync(join(tmpdir(), 'factory-paseo-error-'));
  const calls = [];
  const paseo = async (_cwd, args) => {
    calls.push(args);
    if (args[0] === 'workspace' && args[1] === 'create') return JSON.stringify({ workspaceId: 'wks_task_1' });
    if (args[0] === 'workspace' && args[1] === 'ls') return JSON.stringify([{ workspaceId: 'wks_task_1', cwd: root, isolation: 'local', background: false }]);
    if (args[0] === 'agent' && args[1] === 'run') throw Error('connection lost after possible launch');
    throw Error('must not retry or remove');
  };
  try {
    await assert.rejects(runWorker({ task: task(ids[0]), tree: root, model: 'provider/model', thinking: 'high',
      receipt: join(root, 'receipt.json'), paseo }), /connection lost/);
    assert.equal(calls.filter(x => x[0] === 'agent' && x[1] === 'run').length, 1);
    assert(!calls.some(x => ['stop', 'archive', 'kill', 'delete'].includes(x[1])));
    assert.match(readFileSync(join(root, 'receipt-paseo.jsonl'), 'utf8'), /wks_task_1/);
  } finally { rmSync(root, { recursive: true, force: true }); }
});

test('one worker failure retains its receipt without blocking independent work', async () => {
  const f = fixture();
  f.deps.launch = async ({ task: item }) => { if (item.id === ids[0]) throw Error('worker launch failed'); return { status: 'launched-unverified' }; };
  try {
    const results = await delegate(f.deps);
    assert.equal(results[0].status, 'blocked');
    assert.match(results[0].reason, /worker launch failed/);
    assert.equal(results[1].status, 'launched-unverified');
    assert.equal(readdirSync(f.store).length, 2);
    assert.match(workerPrompt(task(ids[0])), /Do not deliver to dev, push, publish/);
  } finally { f.cleanup(); }
});

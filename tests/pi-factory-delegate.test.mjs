import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, mkdtempSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync, chmodSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { collectTasks, decodeTool, delegate, runWorker, selectTasks, workerPrompt } from '../pi-defaults/extensions/megai-factory/runner.mjs';

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
    model: 'provider/model', thinking: 'high', git,
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
      return { status: 'finished-unverified' };
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
    assert.deepEqual(results.map(x => x.status), ['finished-unverified', 'finished-unverified']);
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

test('real launcher isolates Pi-Bolt argv, cwd, session ID and private log without invoking a model', async () => {
  const root = mkdtempSync(join(tmpdir(), 'factory-spawn-'));
  const bin = join(root, 'bin'); const tree = join(root, 'tree');
  mkdirSync(bin); mkdirSync(tree);
  const path = join(bin, 'pi-bolt');
  writeFileSync(path, '#!/bin/sh\nprintf "%s\\n" "$PWD" "$@"\n'); chmodSync(path, 0o700);
  const old = process.env.PATH;
  process.env.PATH = `${bin}:${old}`;
  try {
    const result = await runWorker({ task: task(ids[0]), tree, model: 'provider/model', thinking: 'high',
      receipt: join(root, 'receipt.json') });
    assert.equal(result.status, 'finished-unverified');
    const log = readFileSync(result.log, 'utf8');
    assert.match(log, new RegExp(tree));
    assert.match(log, new RegExp(`factory-${ids[0]}`));
    assert.match(log, /--no-mcp/);
    assert.match(log, /provider\/model/);
    assert.match(log, /Implement ONLY/);
    assert.equal(readdirSync(root).filter(x => x.endsWith('jsonl')).length, 1);
  } finally { process.env.PATH = old; rmSync(root, { recursive: true, force: true }); }
});

test('one worker failure retains its receipt without blocking independent work', async () => {
  const f = fixture();
  f.deps.launch = async ({ task: item }) => { if (item.id === ids[0]) throw Error('worker launch failed'); return { status: 'finished-unverified' }; };
  try {
    const results = await delegate(f.deps);
    assert.equal(results[0].status, 'blocked');
    assert.match(results[0].reason, /worker launch failed/);
    assert.equal(results[1].status, 'finished-unverified');
    assert.equal(readdirSync(f.store).length, 2);
    assert.match(workerPrompt(task(ids[0])), /Do not deliver to dev, push, publish/);
  } finally { f.cleanup(); }
});

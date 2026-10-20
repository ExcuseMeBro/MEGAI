import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, readdirSync, rmSync, realpathSync, symlinkSync, linkSync, chmodSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync, spawnSync } from 'node:child_process';
import { DatabaseSync } from 'node:sqlite';
import { CommandReceipts } from '../pi-defaults/extensions/megai-command-receipts/receipts.mjs';
const bases = [];
after(() => bases.forEach(path => rmSync(path, { recursive: true, force: true })));
function fixture() {
  const base = realpathSync(mkdtempSync(join(tmpdir(), 'pi-command-receipts-'))); bases.push(base);
  const cwd = join(base, 'repo'); mkdirSync(cwd); execFileSync('git', ['init', '-q', cwd]);
  const options = { root: join(base, 'private'), cwd, projectId: '59005e36-ecd4-46ed-bb42-f779858b20ce',
    taskId: '8fa7a469-da42-4494-98ef-f80736c3f810', sessionId: 'session-one' };
  return { base, options, store: new CommandReceipts(options) };
}
const ok = () => ({ content: [{ type: 'text', text: 'SECRET_OUTPUT' }], details: { secret: 'SECRET_OUTPUT' } });
test('committed duplicate survives new store/session; only hashes and metadata persist', async () => {
  const f = fixture(); let calls = 0;
  const action = () => { calls++; return ok(); };
  const args = { command: 'SECRET_ARGUMENT', timeout: 10 };
  const first = await f.store.execute('logical-id', 'bash', args, action);
  const second = await new CommandReceipts({ ...f.options, sessionId: 'session-two' })
    .execute('logical-id', 'bash', { timeout: 10, command: 'SECRET_ARGUMENT' }, action);
  assert.equal(calls, 1); assert.equal(first.replayed, false); assert.equal(second.replayed, true);
  assert.equal(second.value, undefined); assert.equal(second.receipt.sessionId, 'session-one');
  assert.equal(second.receipt.state, 'completed');
  assert.equal(statSync(f.store.directory).mode & 0o777, 0o700);
  for (const name of readdirSync(f.store.directory)) {
    const path = join(f.store.directory, name);
    assert.equal(statSync(path).mode & 0o077, 0);
    const bytes = readFileSync(path);
    assert.equal(bytes.includes(Buffer.from('SECRET_ARGUMENT')), false);
    assert.equal(bytes.includes(Buffer.from('SECRET_OUTPUT')), false);
  }
});
test('same ID changed args/tool/cwd refuses, and distinct task/repository scopes stay independent', async () => {
  const f = fixture(); let calls = 0; const action = () => { calls++; return ok(); };
  await f.store.execute('id', 'bash', { command: 'one' }, action);
  await assert.rejects(() => f.store.execute('id', 'bash', { command: 'two' }, action), /mismatch/);
  await assert.rejects(() => f.store.execute('id', 'edit', { command: 'one' }, action), /mismatch/);
  const subdir = join(f.options.cwd, 'sub'); mkdirSync(subdir);
  await assert.rejects(() => new CommandReceipts({ ...f.options, cwd: subdir })
    .execute('id', 'bash', { command: 'one' }, action), /mismatch/);
  const other = new CommandReceipts({ ...f.options, taskId: '00000000-0000-4000-8000-000000000001' });
  await other.execute('id', 'bash', { command: 'one' }, action);
  const g = fixture(); await g.store.execute('id', 'bash', { command: 'one' }, action);
  assert.equal(calls, 3);
});
test('competing same ID blocks; independent ID completes while original action awaits', async () => {
  const f = fixture(); let release; let calls = 0;
  const pending = f.store.execute('held', 'bash', {}, async () => {
    calls++; await new Promise(resolve => { release = resolve; }); return ok();
  });
  const other = new CommandReceipts(f.options);
  await assert.rejects(() => other.execute('held', 'bash', {}, ok), /running or uncertain/);
  assert.equal((await other.execute('independent', 'bash', {}, ok)).receipt.state, 'completed');
  release(); await pending; assert.equal(calls, 1);
});
test('failed nested result replays failure; throw/cancel retains uncertainty with no replay', async () => {
  const f = fixture(); let calls = 0;
  const failed = await f.store.execute('failed', 'bash', {}, () => { calls++; return { ...ok(), isError: true }; });
  assert.equal(failed.receipt.state, 'failed');
  assert.equal((await f.store.execute('failed', 'bash', {}, ok)).receipt.state, 'failed');
  await assert.rejects(() => f.store.execute('throw', 'bash', {}, () => { calls++; throw new Error('SECRET_ERROR'); }), /SECRET_ERROR/);
  assert.equal(f.store.status('throw').state, 'uncertain');
  await assert.rejects(() => f.store.execute('throw', 'bash', {}, ok), /uncertain/);
  const controller = new AbortController();
  await assert.rejects(() => f.store.execute('aborted', 'bash', {}, () => { calls++; controller.abort(); return ok(); }, controller.signal));
  assert.equal(f.store.status('aborted').state, 'uncertain');
  await assert.rejects(() => f.store.execute('aborted', 'bash', {}, ok), /uncertain/);
  await assert.rejects(() => f.store.execute('pre-aborted', 'bash', {}, ok, controller.signal));
  assert.equal(f.store.status('pre-aborted'), null); assert.equal(calls, 3);
  assert.equal(readFileSync(f.store.path).includes(Buffer.from('SECRET_ERROR')), false);
});
test('real exited worker after external effect leaves durable running record and blocks replay', async () => {
  const f = fixture(), effect = join(f.base, 'effect');
  const module = new URL('../pi-defaults/extensions/megai-command-receipts/receipts.mjs', import.meta.url).href;
  const script = `import { CommandReceipts } from ${JSON.stringify(module)};
    import { writeFileSync } from 'node:fs';
    await new CommandReceipts(${JSON.stringify(f.options)}).execute('lost', 'bash', {}, () => {
      writeFileSync(${JSON.stringify(effect)}, 'effect'); process.exit(0);
    });`;
  const child = spawnSync(process.execPath, ['--input-type=module', '-e', script], { encoding: 'utf8', timeout: 10000 });
  assert.equal(child.status, 0, child.stderr); assert.equal(readFileSync(effect, 'utf8'), 'effect');
  assert.equal(f.store.status('lost').state, 'running');
  await assert.rejects(() => f.store.execute('lost', 'bash', {}, () => { throw new Error('must not dispatch'); }), /uncertain/);
});
test('invalid identities/JSON/tools/non-Git directories refuse before dispatch', async () => {
  const f = fixture();
  assert.throws(() => new CommandReceipts({ ...f.options, taskId: 'not-a-task' }), /UUID/);
  assert.throws(() => new CommandReceipts({ ...f.options, cwd: f.base }));
  await assert.rejects(() => f.store.execute('../escape', 'bash', {}, ok), /Invalid/);
  await assert.rejects(() => f.store.execute('id', 'durable_execute', {}, ok), /unsupported/);
  await assert.rejects(() => f.store.execute('id', 'bash', { invalid: undefined }, ok), /JSON/);
  await assert.rejects(() => f.store.execute('id', 'bash', { command: 'x'.repeat(65536) }, ok), /64 KiB/);
  assert.equal(f.store.status('id'), null);
});
test('symlink/directory/file permissions, hardlinks and unknown/corrupt schema fail closed', async () => {
  const f = fixture();
  const link = join(f.base, 'linked'); symlinkSync(f.options.root, link);
  assert.throws(() => new CommandReceipts({ ...f.options, root: link }), /symlink/);
  chmodSync(f.store.directory, 0o755); assert.throws(() => f.store.status('id'), /private/);
  chmodSync(f.store.directory, 0o700); f.store.status('id');
  chmodSync(f.store.path, 0o644); assert.throws(() => f.store.status('id'), /private/);
  chmodSync(f.store.path, 0o600);
  const db = new DatabaseSync(f.store.path); db.exec('PRAGMA user_version=99'); db.close();
  assert.throws(() => f.store.status('id'), /schema/);
  const g = fixture(); writeFileSync(g.store.path, 'not SQLite', { mode: 0o600 });
  assert.throws(() => g.store.status('id'));
  const h = fixture(); symlinkSync(f.store.path, h.store.path);
  assert.throws(() => h.store.status('id'), /regular file/);
  const i = fixture(); linkSync(f.store.path, i.store.path);
  assert.throws(() => i.store.status('id'), /regular file/);
  const j = fixture(); symlinkSync(f.store.path, j.store.path + '-journal');
  assert.throws(() => j.store.status('id'), /regular file/);
});
test('malformed completed receipt never authorizes replay', async () => {
  const f = fixture(); await f.store.execute('id', 'bash', {}, ok);
  const db = new DatabaseSync(f.store.path); db.exec("UPDATE receipts SET state='completed',finished=NULL"); db.close();
  await assert.rejects(() => f.store.execute('id', 'bash', {}, ok), /Malformed receipt row/);
});

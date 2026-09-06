import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { exportSnapshot, mergeTask } from '../lib/asana_plane_snapshot.mjs';
import { isPublicAddress, publicTarget } from '../lib/asana_plane_files.mjs';

function fixture({ brokenStories = false, truncatedSubtasks = false } = {}) {
  const task = { gid: '10', name: 'Synthetic', num_subtasks: 1, completed: true, modified_at: '2020-01-01', memberships: [{ project: { gid: '1' } }, { project: { gid: '2' } }] };
  const child = { gid: '11', name: 'Child', num_subtasks: 0, parent: { gid: '10' }, completed: true, modified_at: '2020-01-01' };
  const orphan = { gid: '12', name: 'My Tasks only', num_subtasks: 0, memberships: [], modified_at: '2020-01-01' };
  const calls = [];
  return { calls, async call(name, args = {}) {
    calls.push({ name, args });
    if (name === 'get_me') return { data: { gid: '100', workspaces: [{ gid: '123' }] } };
    if (name === 'get_projects') return { data: [{ gid: args.archived ? '2' : '1', archived: args.archived }], next_page: null };
    if (name === 'get_project') return { data: { gid: args.project_id, sections: [], task_counts: { num_tasks: 1 } } };
    if (name === 'get_tasks') return { data: [task], next_page: null };
    if (name === 'get_my_tasks') return { data: [orphan], next_page: null };
    if (name === 'get_task') return { data: args.task_id === '10' ? { ...task, subtasks: truncatedSubtasks ? [] : [child] } : child };
    if (name === 'get_task_stories') {
      if (brokenStories) throw new Error('synthetic read failure');
      return { data: [{ gid: '99', text: 'Original comment', created_at: '2020-01-01', created_by: { gid: '100' } }], next_page: null };
    }
    if (name === 'get_attachments') return { data: [], next_page: null };
    throw new Error('Unexpected call');
  } };
}
function root() { return fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()), 'megai-snapshot-test-')); }

test('export preserves archives, multi-home identity, nested completion, unprojected tasks and comments; resume reuses cached reads', async () => {
  const dir = root(); const client = fixture();
  try {
    const m = await exportSnapshot(client, dir, { sourceWorkspace: '123', concurrency: 2 });
    assert.equal(m.export_complete, true); assert.deepEqual(m.tasks.sort(), ['10','11','12']);
    assert.equal(m.projects.length, 2); assert.equal(m.projects[1].archived, true);
    assert.equal(JSON.parse(fs.readFileSync(path.join(dir, 'source/tasks/11.json'))).completed, true);
    assert.equal(JSON.parse(fs.readFileSync(path.join(dir, 'source/tasks/10.json'))).memberships.length, 2);
    assert.equal(JSON.parse(fs.readFileSync(path.join(dir, 'source/stories/10.json')))[0].text, 'Original comment');
    assert.equal(fs.existsSync(path.join(dir, 'export.lock')), false);
    const previous = client.calls.length;
    const resumed = await exportSnapshot(client, dir, { sourceWorkspace: '123' });
    assert.equal(resumed.export_complete, true);
    const resumedCalls = client.calls.slice(previous);
    assert.ok(resumedCalls.some(call => call.name === 'get_projects'));
    assert.ok(resumedCalls.some(call => call.name === 'get_tasks'));
    assert.ok(!resumedCalls.some(call => call.name === 'get_task_stories'));
    assert.equal(resumed.full_account_export_complete, false);
    assert.equal(resumed.coverage_gaps.length, 2);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});
test('read failure and truncated subtasks prevent a complete migration claim', async () => {
  for (const options of [{ brokenStories: true }, { truncatedSubtasks: true }]) {
    const dir = root();
    try {
      const m = await exportSnapshot(fixture(options), dir, { sourceWorkspace: '123' });
      assert.equal(m.export_complete, false); assert.ok(m.gaps.length > 0);
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  }
});
test('non-paginated user-directory tool is an explicit coverage gap, not proof of a full account export', async () => {
  const dir = root(); const client = fixture(); const originalCall = client.call;
  client.catalog = [{ name: 'get_users' }];
  client.call = (name, args) => name === 'get_users' ? Promise.resolve({ data: [{ gid: '100' }] }) : originalCall(name, args);
  try {
    const result = await exportSnapshot(client, dir, { sourceWorkspace: '123' });
    assert.equal(result.export_complete, true); assert.equal(result.full_account_export_complete, false);
    assert.ok(result.coverage_gaps.some(gap => gap.kind === 'user_directory_pagination_not_exposed'));
    assert.equal(result.tasks.length, 3);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});
test('equal-sized task shapes preserve the union of fields', () => {
  const tasks = new Map(); const gaps = [];
  mergeTask(tasks, { gid: '1', name: 'Name' }, gaps);
  mergeTask(tasks, { gid: '1', notes: 'Notes' }, gaps);
  assert.equal(tasks.get('1').name, 'Name'); assert.equal(tasks.get('1').notes, 'Notes');
});
test('dead same-host owned locks recover but foreign locks remain blocked', async () => {
  const dir = root();
  try {
    fs.writeFileSync(path.join(dir, 'export.lock'), JSON.stringify({ pid: 2147483647, host: os.hostname(), id: 'stale' }), { mode: 0o600 });
    assert.equal((await exportSnapshot(fixture(), dir, { sourceWorkspace: '123' })).export_complete, true);
    assert.ok(fs.readdirSync(dir).some(name => name.startsWith('export.lock.stale-')));
    fs.writeFileSync(path.join(dir, 'export.lock'), JSON.stringify({ pid: 2147483647, host: 'foreign', id: 'stale' }), { mode: 0o600 });
    await assert.rejects(exportSnapshot(fixture(), dir, { sourceWorkspace: '123' }), /ownership/);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});
test('explicit source binding and one-run lock fail closed', async () => {
  const dir = root();
  try {
    await assert.rejects(exportSnapshot(fixture(), dir), /explicit source/);
    await assert.rejects(exportSnapshot(fixture(), dir, { sourceWorkspace: '124' }), /differs/);
    fs.writeFileSync(path.join(dir, 'export.lock'), JSON.stringify({ pid: process.pid, host: os.hostname(), id: 'other' }), { mode: 0o600 });
    await assert.rejects(exportSnapshot(fixture(), dir, { sourceWorkspace: '123' }), /already running/);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});
test('attachment DNS pinning rejects private, mapped, mixed, credential and downgrade targets', async () => {
  for (const address of ['127.0.0.1','10.0.0.1','169.254.169.254','100.64.0.1','192.168.1.1','172.16.0.1','::1','::ffff:127.0.0.1','fc00::1','fe80::1','2001:db8::1','2001::1','2001:0000::1','2001:20::1','2002:7f00:1::','3fff::1']) assert.equal(isPublicAddress(address), false, address);
  assert.equal(isPublicAddress('8.8.8.8'), true); assert.equal(isPublicAddress('2606:4700:4700::1111'), true);
  for (const value of ['http://example.com/a','https://user:pass@example.com/a','https://example.com:8443/a','https://localhost/a']) await assert.rejects(publicTarget(value));
  await assert.rejects(publicTarget('https://example.com/a', async () => [{ address: '8.8.8.8', family: 4 },{ address: '127.0.0.1', family: 4 }]), /Private/);
  const target = await publicTarget('https://example.com/a', async () => [{ address: '8.8.8.8', family: 4 }]);
  assert.equal(target.records[0].address, '8.8.8.8');
});

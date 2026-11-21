import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { once } from 'node:events';
import { mkdtempSync, readFileSync, realpathSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { addLesson, feedback, forgetLesson, lessonsPrompt, parseLessons, readLessons, recordFeedback } from '../pi-defaults/opt-in/factory/lessons.mjs';
import { RoutineError, lastSlot, loadState, nextSlot, parseConfig, slotKey, taskDescription, taskLimit, tick } from '../pi-defaults/opt-in/factory/routines.mjs';

const dir = (t) => {
  const path = realpathSync(mkdtempSync(join(tmpdir(), 'pi-factory-routines-')));
  t.after(() => rmSync(path, { recursive: true, force: true }));
  return path;
};
const c = (id, author, body, created_at = '2026-11-21T10:00:00Z') => ({ id, author, body, created_at });

test('lessons: only the user\'s comments after an agent note count; pending resets on each agent note', () => {
  const list = [c(1, 'me', 'scope'), c(2, 'pi', 'done'), c(3, 'me', 'fix A'), c(4, 'agent', 'fixed A'), c(5, 'me', 'fix B'), c(6, 'me', '  ')];
  const { all, pending } = feedback(list);
  assert.deepEqual(all.map((x) => x.id), [3, 5]);
  assert.deepEqual(pending.map((x) => x.id), [5]);
  assert.deepEqual(feedback([c(1, 'me', 'scope only')]).all, []);
  assert.deepEqual(feedback('not a list').all, []);
  assert.deepEqual(feedback([{ id: 'x', author: 'me', body: 'bad' }, c(2, 'pi', 'ok'), c(3, 'me', 'good')]).all.map((x) => x.id), [3], 'malformed comments are dropped');
});

test('lessons: saved once per comment, edited by hand or command, newest shown within a budget', async (t) => {
  const agentDir = dir(t);
  const list = [c(1, 'pi', 'done'), c(2, 'me', 'Run the e2e suite\n before review.', '2026-11-20T08:00:00Z')];
  assert.equal(await recordFeedback(agentDir, 'proj', 'proj#7', list), 1);
  assert.equal(await recordFeedback(agentDir, 'proj', 'proj#7', list), 0, 'same comment is not repeated');
  await addLesson(agentDir, 'proj', 'Prefer small PR-sized commits.');
  let text = await readLessons(agentDir, 'proj');
  assert.match(text, /^# Lessons — proj/);
  assert.deepEqual(parseLessons(text).map((line) => line.replace(/^- \S+ · /, '')),
    ['proj#7 (c2): Run the e2e suite before review.', 'manual: Prefer small PR-sized commits.']);
  assert.equal(await forgetLesson(agentDir, 'proj', 2), parseLessons(text)[1]);
  await assert.rejects(forgetLesson(agentDir, 'proj', 5), /No lesson 5/);
  await assert.rejects(addLesson(agentDir, 'proj', '   '), /Usage/);
  text = await readLessons(agentDir, 'proj');
  assert.equal(parseLessons(text).length, 1);
  assert.match(lessonsPrompt('proj', text), /# Project lessons \(proj\)\n[\s\S]*Run the e2e suite before review/);
  assert.equal(lessonsPrompt('proj', ''), '');
  const many = Array.from({ length: 30 }, (_, i) => `- lesson ${i}`).join('\n');
  const shown = parseLessons(lessonsPrompt('proj', many));
  assert.equal(shown.length, 20);
  assert.equal(shown.at(-1), '- lesson 29', 'newest kept');
  assert.equal(parseLessons(lessonsPrompt('proj', many, 20, 40)).length, 3, 'character budget');
  await assert.rejects(readLessons(agentDir, '../etc'), /Invalid project/);
});

test('routines: config is validated with clear messages', () => {
  const ok = parseConfig(JSON.stringify({ routines: [{ id: 'deps', project: 'p', title: 'Deps', every: 'weekly', day: 'mon', maxDiffLines: 50 }] }));
  assert.deepEqual(ok[0], { id: 'deps', project: 'p', title: 'Deps', description: '', every: 'weekly', day: 'mon', at: '09:00',
    maxDiffLines: 50, priority: 'low', enabled: true });
  const bad = [
    ['{', /not valid JSON/], ['{}', /"routines" array/],
    [{ id: 'Bad', project: 'p', title: 'x', every: 'daily' }, /id must be/],
    [{ id: 'a', project: 'p', title: 'x', every: 'hourly' }, /every must be/],
    [{ id: 'a', project: 'p', title: 'x', every: 'weekly' }, /day must be/],
    [{ id: 'a', project: 'p', title: 'x', every: 'daily', at: '9:00' }, /HH:MM/],
    [{ id: 'a', project: 'p', title: 'x', every: 'daily', maxDiffLines: 0 }, /maxDiffLines/],
    [{ id: 'a', project: 'all', title: 'x', every: 'daily' }, /project must be/],
  ];
  for (const [value, message] of bad) {
    const text = typeof value === 'string' ? value : JSON.stringify({ routines: [value] });
    assert.throws(() => parseConfig(text), (error) => error instanceof RoutineError && message.test(error.message), text);
  }
  const twice = { id: 'a', project: 'p', title: 'x', every: 'daily' };
  assert.throws(() => parseConfig(JSON.stringify({ routines: [twice, twice] })), /Duplicate routine p\/a/);
});

test('routines: daily and weekly slots in local time', () => {
  const daily = { every: 'daily', at: '09:00' };
  const weekly = { every: 'weekly', day: 'mon', at: '09:00' };
  const thu = new Date(2026, 10, 19, 8, 30); // Thursday 08:30
  assert.equal(slotKey(lastSlot(daily, thu)), '2026-11-18T09:00');
  assert.equal(slotKey(lastSlot(daily, new Date(2026, 10, 19, 9, 0))), '2026-11-19T09:00');
  assert.equal(slotKey(lastSlot(weekly, thu)), '2026-11-16T09:00');
  assert.equal(slotKey(nextSlot(weekly, thu)), '2026-11-23T09:00');
  assert.equal(slotKey(lastSlot(weekly, new Date(2026, 10, 16, 8, 59))), '2026-11-09T09:00');
  assert.equal(slotKey(lastSlot(weekly, new Date(2026, 10, 16, 9, 0))), '2026-11-16T09:00');
});

async function brokan(t) {
  const state = { tasks: [], next: 100, writes: [] };
  const server = createServer(async (req, res) => {
    let body = '';
    for await (const chunk of req) body += chunk;
    const url = new URL(req.url, 'http://x');
    const json = (value) => res.writeHead(200, { 'content-type': 'application/json' }).end(JSON.stringify(value));
    if (req.method === 'GET' && url.pathname === '/api/board') return json({ tasks: state.tasks.filter((x) => x.project === url.searchParams.get('project')) });
    if (req.method === 'POST' && url.pathname === '/api/tasks') {
      const input = JSON.parse(body);
      const task = { id: state.next++, project: input.project, title: input.title, description: input.description, priority: input.priority, status: 'todo', tags: [] };
      state.tasks.push(task);
      state.writes.push(['POST', input]);
      return json(task);
    }
    const patch = /^\/api\/tasks\/(\d+)$/.exec(url.pathname);
    if (req.method === 'PATCH' && patch) {
      const task = state.tasks.find((x) => x.id === Number(patch[1]));
      task.tags = JSON.parse(body).tags.split(',');
      state.writes.push(['PATCH', task.id, task.tags]);
      return json(task);
    }
    res.writeHead(404).end();
  });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const original = globalThis.fetch;
  globalThis.fetch = (url, init) => {
    const target = new URL(url);
    assert.equal(target.origin, 'http://127.0.0.1:1317');
    return original(`http://127.0.0.1:${server.address().port}${target.pathname}${target.search}`, init);
  };
  t.after(() => { globalThis.fetch = original; server.close(); server.closeAllConnections(); });
  return state;
}

test('routines: due slots add one tagged todo task, an open one is never duplicated, run forces one', async (t) => {
  const agentDir = dir(t);
  const board = await brokan(t);
  assert.deepEqual(await tick(agentDir, {}), { created: [], skipped: [] }, 'no config: nothing, no HTTP');
  assert.deepEqual(board.writes, []);
  writeFileSync(join(agentDir, 'routines.json'), JSON.stringify({ routines: [
    { id: 'deps', project: 'p', title: 'Weekly deps', every: 'weekly', day: 'mon', at: '09:00', description: 'Bump deps.', maxDiffLines: 200 },
    { id: 'off', project: 'p', title: 'Disabled', every: 'daily', enabled: false },
    { id: 'other', project: 'q', title: 'Other project', every: 'daily' },
  ] }));
  const mon = new Date(2026, 10, 16, 10, 0);
  let result = await tick(agentDir, { project: 'p', now: mon });
  assert.deepEqual(result.created, [{ key: 'p/deps', task: 100, slot: '2026-11-16T09:00' }]);
  assert.deepEqual(board.tasks[0].tags, ['routine', 'routine:deps']);
  assert.match(board.tasks[0].description, /^Bump deps\.\n\n---\nRoutine `deps` \(weekly on mon at 09:00\)[\s\S]*within 200 changed lines/);
  assert.equal(board.tasks[0].priority, 'low');
  assert.deepEqual(taskLimit(await loadState(agentDir), 'p', 100), { lines: 200, label: 'routine p/deps' });
  assert.equal(taskLimit(await loadState(agentDir), 'q', 100), undefined, 'limit is bound to its project');

  result = await tick(agentDir, { project: 'p', now: new Date(2026, 10, 18, 12, 0) });
  assert.deepEqual(result, { created: [], skipped: [] }, 'same slot is handled once');

  // Next week the previous task is still open: skipped for that slot, not duplicated.
  board.tasks[0].status = 'review';
  result = await tick(agentDir, { project: 'p', now: new Date(2026, 10, 23, 9, 30) });
  assert.deepEqual(result.skipped, [{ key: 'p/deps', task: 100, slot: '2026-11-23T09:00' }]);
  assert.equal(board.tasks.length, 1);

  board.tasks[0].status = 'done';
  result = await tick(agentDir, { now: new Date(2026, 10, 24, 9, 30), force: 'deps' });
  assert.deepEqual(result.created.map((x) => x.task), [101]);
  await assert.rejects(tick(agentDir, { force: 'nope' }), /No routine nope/);
  // An untagged open task Factory created still counts as open (a failed tag write never duplicates).
  board.tasks[1].tags = [];
  result = await tick(agentDir, { now: new Date(2026, 10, 30, 9, 30) });
  assert.deepEqual(result.skipped.map((x) => x.task), [101]);
  assert.deepEqual(result.created.map((x) => x.key), ['q/other'], 'other project in a full tick');
  assert.equal(board.tasks.length, 3);
  assert.equal(JSON.parse(readFileSync(join(agentDir, 'routines-state.json'), 'utf8')).routines['p/off'], undefined, 'disabled never runs');
});

test('routines: a concurrent tick in another session is reported busy, not duplicated', async (t) => {
  const agentDir = dir(t);
  await brokan(t);
  writeFileSync(join(agentDir, 'routines.json'), JSON.stringify({ routines: [{ id: 'a', project: 'p', title: 'A', every: 'daily' }] }));
  writeFileSync(join(agentDir, 'routines.lock'), '1\n');
  const result = await tick(agentDir, { now: new Date(2026, 10, 16, 10, 0) });
  assert.equal(result.busy, true);
  assert.deepEqual(result.created, []);
});

test('routines: task text without a limit has no counter-metric line', () => {
  const text = taskDescription({ id: 'a', title: 'Clean flaky tests', description: '', every: 'daily', at: '07:00' }, '2026-11-16T07:00');
  assert.match(text, /^Clean flaky tests\n/);
  assert.doesNotMatch(text, /Counter-metric/);
});

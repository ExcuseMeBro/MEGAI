import assert from 'node:assert/strict';
import { test } from 'node:test';
import { mkdtemp, rm, symlink, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { dependencies, evalSummary, formatReceipt, readiness, records, requiredChecks, task, taskNumber } from '../agent/extensions/megai-factory-flow/core.mjs';
import { loadEval } from '../agent/extensions/megai-factory-flow/reader.mjs';

const project = 'demo';
const stub = (id, more = {}) => ({ id, project, status: 'todo', human: false, description: '', comments: 0, updated_at: '2026-01-01T00:00:00Z', ...more });
const comment = (id, value) => ({ id, task_id: 1, body: 'Factory-Flow: ' + JSON.stringify({ v: 1, ...value }) });
const wait = { kind: 'wait', key: 'client', type: 'decision', blocked: 'Contract', question: 'Which client?', recommendation: 'Use the fixture', next: 'Check a dry run' };
const answer = { kind: 'answer', key: 'client', answer: 'Use the fixture' };
const a = '1'.repeat(40), b = '2'.repeat(40);
const receipt = { kind: 'receipt', stage: 'remote-verified', sha: a, remote: 'origin/example', remoteHead: b, checks: [{ name: 'test', status: 'pass' }, { name: 'lint', status: 'pass' }] };

test('validate project identity and parse declarations without partial results', () => {
  assert.equal(taskNumber('demo#4', project), 4);
  for (const ref of ['other#4', 'demo#04', 'demo#9999999999999999', 'demo#2/../4']) assert.throws(() => taskNumber(ref, project));
  assert.throws(() => task(stub(4, { project: 'other' }), project));
  assert.throws(() => task(stub(4, { human: 'false' }), project));
  assert.deepEqual(dependencies('A short note\nFactory depends-on: demo#2 demo#3\n', project), [2, 3]);
  for (const invalid of ['demo#2 demo#2', 'demo#2 not-a-reference', '']) assert.throws(() => dependencies('Factory depends-on: '+invalid, project));
  assert.throws(() => requiredChecks('Factory required-checks: test test'));
});

test('handoffs close only on a valid later answer for the same task and key', () => {
  assert.deepEqual([...records([comment(1, wait)], 1).active.keys()], ['client']);
  const state = records([comment(2, answer), comment(1, wait)], 1);
  assert.equal(state.active.size, 0);
  assert.deepEqual(state.answered.get('client'), { wait: { v: 1, ...wait }, answer: answer.answer });
  for (const invalid of [
    [comment(1, answer)], [comment(1, wait), comment(2, wait)], [comment(1, wait), comment(1, answer)],
    [{ ...comment(1, wait), task_id: 2 }], [comment(1, { ...wait, question: 'A\u001b[8m' })],
    [{ ...comment(1, wait), body: 'Factory-Flow: {bad JSON}' }],
  ]) assert.throws(() => records(invalid, 1));
});

test('readiness refuses unresolved, unknown, invalid, cyclic, human or unverified work', () => {
  const root = stub(1, { description: 'Factory depends-on: demo#2' });
  const deps = new Map([[1, root], [2, stub(2, { status: 'review', description: 'Factory depends-on: demo#3' })], [3, stub(3, { status: 'todo' })]]);
  const clean = records([], 1);
  assert.deepEqual(readiness(root, deps, clean), ['demo#3 todo']);
  deps.set(3, stub(3, { status: 'done', description: 'Factory depends-on: demo#1' }));
  assert.deepEqual(readiness(root, deps, clean), ['cycle at demo#1']);
  deps.set(3, stub(3, { status: 'done' }));
  assert.deepEqual(readiness(root, deps, clean), []);
  assert.match(readiness(root, deps, null).join(), /not verified/);
  assert.match(readiness(root, deps, records([comment(1, wait)], 1)).join(), /needs decision: client/);
  assert.match(readiness(root, deps, records([comment(1, { ...wait, type:'resource' })], 1)).join(), /waiting for resource\/check/);
  assert.match(readiness({ ...root, human: true }, deps, clean).join(), /not an agent-owned/);
  deps.delete(3);
  assert.match(readiness(root, deps, clean).join(), /unknown demo#3/);
  deps.set(2, stub(2, { status: 'done', description: 'Factory depends-on: other#3' }));
  assert.match(readiness(root, deps, clean).join(), /invalid dependency/);
});

test('a receipt is scoped to the exact SHA and all required gates, with no silent fallback', () => {
  const state = records([comment(1, receipt)], 1);
  const required = requiredChecks('Factory required-checks: test lint');
  assert.match(formatReceipt(state, a, required).join(), /Remote attestation \(not re-fetched\): origin\/example/);
  assert.doesNotMatch(formatReceipt(state, a, []).join(), /Remote attestation/);
  assert.match(formatReceipt(state, a, [...required, 'build']).join(), /Required checks missing: build/);
  assert.doesNotMatch(formatReceipt(state, a, [...required, 'build']).join(), /Remote attestation/);
  assert.match(formatReceipt(state, b, required).join(), /no receipt for this exact SHA/);
  assert.throws(() => formatReceipt(state, a.slice(0,7), required));
  const checks = [{ name:'test', status:'pass' }, { name:'lint', status:'wait' }];
  assert.throws(() => records([comment(1, { ...receipt, checks })], 1));
  assert.throws(() => records([comment(1, { ...receipt, stage:'candidate', checks })], 1));
  const candidate = { kind:'receipt', stage:'candidate', sha:a, checks };
  assert.match(formatReceipt(records([comment(1, receipt), comment(2, candidate)], 1), a, required).join(), /pending: lint.*not attested/s);
});

const evalInput = () => {
  const base = { base:a, fixture:'3'.repeat(64), setup:'4'.repeat(64), accepted:true, regressions:0, ms:1000, usdMicros:10 };
  return { v:1, arms:['original','candidate'], cases:[
    { id:'first', runs:[{...base, arm:'original'}, {...base, arm:'candidate', ms:700, usdMicros:8}] },
    { id:'second', runs:[{...base, arm:'original', ms:500}, {...base, arm:'candidate', ms:900, regressions:1, usdMicros:null}] },
  ] };
};

test('paired eval separates quality and regressions, wins, timing and complete cost pairs', () => {
  assert.deepEqual(evalSummary(evalInput()), { pairs: 2, costPairs: 1, summary: [
    { arm:'original', accepted:2, regressions:0, medianMs:750, faster:1, medianUsdMicros:10 },
    { arm:'candidate', accepted:1, regressions:1, medianMs:800, faster:1, medianUsdMicros:8 },
  ] });
  for (const change of [{base:b}, {fixture:'5'.repeat(64)}, {setup:'6'.repeat(64)}, {ms:0}, {arm:'original'}, {usdMicros:undefined}]) {
    const value = evalInput(); Object.assign(value.cases[0].runs[1], change);
    assert.throws(() => evalSummary(value));
  }
  const value = evalInput(); value.cases[0].runs[0].usdMicros = null;
  assert.deepEqual(evalSummary(value).summary.map(arm => arm.medianUsdMicros), [null, null]);
});

test('eval only accepts bounded regular JSON files', async t => {
  const root = await mkdtemp(join(tmpdir(), 'factory-flow-parser-'));
  t.after(() => rm(root, { recursive:true, force:true }));
  await writeFile(join(root, 'sample.json'), '{"v":1}');
  await symlink(join(root, 'sample.json'), join(root, 'link.json'));
  await writeFile(join(root, 'oversize.json'), ' '.repeat(256*1024+1));
  assert.deepEqual(await loadEval(root, 'sample.json'), {v:1});
  for (const path of ['.', 'link.json', 'oversize.json', 'missing.json']) await assert.rejects(loadEval(root, path));
});

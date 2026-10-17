import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, readFileSync, mkdirSync, symlinkSync, rmSync, chmodSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { DurableStore } from '../pi-defaults/extensions/megai-durable-workflow/store.mjs';

const projectId = '59005e36-ecd4-46ed-bb42-f779858b20ce';
const taskId = 'a59bc58a-2990-4083-9e2a-8530fa0c2269';
const temporaryRoots = [];
after(() => temporaryRoots.forEach(path => rmSync(path, { recursive: true, force: true })));
function fixture() {
  const base = mkdtempSync(join(tmpdir(), 'pi-durable-')); temporaryRoots.push(base);
  const repo = join(base, 'repo'); mkdirSync(repo);
  const git = (...args) => execFileSync('git', ['-C', repo, ...args], { encoding: 'utf8' });
  git('init', '-q'); git('config', 'user.email', 'test@example.invalid'); git('config', 'user.name', 'Test');
  writeFileSync(join(repo, 'code.txt'), 'original\n'); git('add', '.'); git('commit', '-qm', 'base');
  const root = join(base, 'private');
  const store = () => new DurableStore({ root, cwd: repo, sessionId: 'session-one' });
  return { base, repo, root, git, store };
}
const checkpoint = { projectId, taskId, expectedRevision: 0, phase: 'verify', summary: 'Implementation saved; tests pending', nextAction: 'Run the focused test', uncertainOperations: [] };

test('checkpoint survives a new store and restores without replaying actions', () => {
  const f = fixture();
  const saved = f.store().checkpoint(checkpoint);
  assert.equal(saved.revision, 1);
  const nextSession = new DurableStore({ root: f.root, cwd: f.repo, sessionId: 'session-two' });
  const resumed = nextSession.resume(taskId);
  assert.equal(resumed.checkpoint.nextAction, 'Run the focused test');
  assert.equal(resumed.checkpoint.projectId, projectId);
  assert.equal(resumed.readOnly, true);
  assert.equal(resumed.sourceCurrent, true);
  assert.equal(nextSession.getCheckpoint(taskId).revision, 1);
});

function knowledge(f) {
  const path = join(f.base, 'evidence.txt'); writeFileSync(path, 'tests passed with exact assertions\n');
  const sha256 = createHash('sha256').update(readFileSync(path)).digest('hex');
  return { projectId, taskId, title: 'Bounded retries', content: 'Reconcile writes before a retry.',
    evidence: [{ path, sha256, observation: 'A public-interface test preserved the record after restart.' }] };
}

test('only reviewed and explicitly promoted evidence-backed knowledge can be recalled', () => {
  const f = fixture(), store = f.store();
  const candidate = store.stage(knowledge(f));
  assert.deepEqual(store.search('retries'), []);
  assert.throws(() => store.promote(candidate.id, 1), /Reviewed candidate required/);
  const report = join(f.base, 'review.txt'); writeFileSync(report, 'Reviewed artifact and supported repository scope.');
  const reviewed = store.review(candidate.id, 1, report);
  assert.equal(reviewed.state, 'reviewed');
  assert.deepEqual(store.search('retries'), []);
  const approved = store.promote(candidate.id, reviewed.revision);
  assert.equal(approved.approval.actor, 'user-ui');
  assert.equal(f.store().search('retries')[0].content, 'Reconcile writes before a retry.');
  store.revoke(candidate.id, approved.revision);
  assert.deepEqual(store.search('retries'), []);
});

test('stale checkpoint revisions, wrong project, dirty source and uncertain operations require reconciliation', () => {
  const f = fixture(), store = f.store();
  store.checkpoint({ ...checkpoint, uncertainOperations: ['Remote write result unknown'] });
  assert.equal(store.resume(taskId).canContinue, false);
  assert.throws(() => f.store().checkpoint(checkpoint), /Stale checkpoint revision/);
  assert.throws(() => store.checkpoint({ ...checkpoint, expectedRevision: 1,
    projectId: '00000000-0000-4000-8000-000000000001' }), /Plane project mismatch/);
  writeFileSync(join(f.repo, 'code.txt'), 'changed bytes\n');
  assert.equal(store.resume(taskId).sourceCurrent, false);
  const fresh = store.checkpoint({ ...checkpoint, expectedRevision: 1 });
  assert.equal(fresh.revision, 2);
  assert.equal(store.resume(taskId).canContinue, true);
  writeFileSync(join(f.repo, 'code.txt'), 'different bytes, same Git status\n');
  assert.equal(store.resume(taskId).sourceCurrent, false);
});

test('checkpoints survive an actual subprocess restart and linked worktrees share the repository scope', () => {
  const f = fixture(); f.store().checkpoint(checkpoint);
  const child = execFileSync(process.execPath, ['--input-type=module', '-e',
    `import { DurableStore } from ${JSON.stringify(new URL('../pi-defaults/extensions/megai-durable-workflow/store.mjs', import.meta.url).href)};
     console.log(JSON.stringify(new DurableStore({root:process.argv[1],cwd:process.argv[2],sessionId:'new-process'}).resume(process.argv[3])));`,
    f.root, f.repo, taskId], { encoding: 'utf8' });
  assert.equal(JSON.parse(child).checkpoint.nextAction, 'Run the focused test');
  const worktree = join(f.base, 'linked'); f.git('worktree', 'add', '-qb', 'other', worktree);
  assert.equal(new DurableStore({ root: f.root, cwd: worktree, sessionId: 'linked-session' }).resume(taskId).canContinue, true);
  const foreign = fixture();
  const foreignStore = new DurableStore({ root: f.root, cwd: foreign.repo, sessionId: 'foreign' });
  assert.equal(foreignStore.getCheckpoint(taskId), null);
  assert.throws(() => foreignStore.resume(taskId), /not found/);
});

test('evidence is mandatory and evidence/report/source tampering blocks approval and recall', () => {
  const f = fixture(), store = f.store(), input = knowledge(f);
  assert.throws(() => store.stage({ ...input, evidence: [] }), /Evidence required/);
  assert.throws(() => store.stage({ ...input, evidence: [{ ...input.evidence[0], sha256: 'a'.repeat(64) }] }), /hash mismatch/);
  const candidate = store.stage(input), report = join(f.base, 'review.txt');
  writeFileSync(report, 'supported review');
  store.review(candidate.id, 1, report);
  writeFileSync(report, 'tampered review');
  assert.throws(() => store.promote(candidate.id, 2), /Review hash mismatch/);
  writeFileSync(report, 'supported review');
  store.promote(candidate.id, 2);
  writeFileSync(input.evidence[0].path, 'tampered evidence');
  assert.throws(() => store.search('retries'), /Evidence hash mismatch/);
  const another = store.stage(knowledge(f));
  writeFileSync(join(f.repo, 'code.txt'), 'new source');
  assert.throws(() => store.review(another.id, 1, report), /Source changed/);
});

test('unsafe paths, oversized records, corruption and interrupted lock fail closed without replacing data', () => {
  const f = fixture(), store = f.store();
  store.checkpoint(checkpoint);
  const symlink = join(f.base, 'unsafe'); symlinkSync(f.root, symlink);
  assert.throws(() => new DurableStore({ root: symlink, cwd: f.repo, sessionId: 'bad' }), /Symlink refused/);
  const evidence = knowledge(f), artifactLink = join(f.base, 'artifact-link');
  symlinkSync(evidence.evidence[0].path, artifactLink);
  assert.throws(() => store.stage({ ...evidence, evidence: [{ ...evidence.evidence[0], path: artifactLink }] }), /Symlink refused/);
  assert.throws(() => store.resume('../escape'), /UUID/);
  mkdirSync(join(store.directory, '.lock'));
  assert.throws(() => store.checkpoint({ ...checkpoint, expectedRevision: 1 }), /Store busy/);
  assert.equal(store.getCheckpoint(taskId).revision, 1);
  const path = join(store.directory, `w-${taskId}.json`);
  writeFileSync(path, '{broken json');
  assert.throws(() => store.getCheckpoint(taskId), /JSON/);
  assert.equal(readFileSync(path, 'utf8'), '{broken json');
  writeFileSync(path, 'x'.repeat(4 * 1024 * 1024 + 1));
  assert.throws(() => store.getCheckpoint(taskId), /Oversized record/);
});

test('a reviewed lesson cannot change content without invalidating its review binding', () => {
  const f = fixture(), store = f.store(), candidate = store.stage(knowledge(f));
  const report = join(f.base, 'report.txt'); writeFileSync(report, 'supported review');
  store.review(candidate.id, 1, report);
  const path = join(store.directory, `k-${candidate.id}.json`), altered = JSON.parse(readFileSync(path));
  altered.content = 'Unreviewed replacement'; writeFileSync(path, JSON.stringify(altered));
  assert.throws(() => store.promote(candidate.id, 2), /stale review binding/);
});

test('private store requirements and empty review report fail closed', () => {
  const f = fixture(), store = f.store(), candidate = store.stage(knowledge(f));
  const report = join(f.base, 'report.txt'); writeFileSync(report, '');
  assert.throws(() => store.review(candidate.id, 1, report), /must not be empty/);
  assert.throws(() => new DurableStore({ root: 'relative-root', cwd: f.repo, sessionId: 'test' }), /absolute path/);
  chmodSync(store.directory, 0o755);
  assert.throws(() => store.listKnowledge(), /private and user-owned/);
  assert.throws(() => store.knowledge(candidate.id), /private and user-owned/);
});

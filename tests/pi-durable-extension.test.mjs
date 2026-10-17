import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, realpathSync, existsSync, rmSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { pathToFileURL, fileURLToPath } from 'node:url';

let piRoot = dirname(realpathSync(execFileSync('which', ['pi'], { encoding: 'utf8' }).trim()));
while (!existsSync(join(piRoot, 'package.json'))) piRoot = dirname(piRoot);
assert.equal(JSON.parse(readFileSync(join(piRoot, 'package.json'))).name, '@earendil-works/pi-coding-agent');
const { loadExtensions, createExtensionRuntime } = await import(pathToFileURL(join(piRoot, 'dist/core/extensions/index.js')));
const extensionPath = process.env.MEGAI_DURABLE_EXTENSION || resolve(dirname(fileURLToPath(import.meta.url)), '../pi-defaults/extensions/megai-durable-workflow/index.ts');
const projectId = '59005e36-ecd4-46ed-bb42-f779858b20ce', taskId = 'a59bc58a-2990-4083-9e2a-8530fa0c2269';
const temporaryRoots = [];
const previousHome = process.env.MEGAI_HOME;
after(() => {
  if (previousHome === undefined) delete process.env.MEGAI_HOME; else process.env.MEGAI_HOME = previousHome;
  temporaryRoots.forEach(path => rmSync(path, { recursive: true, force: true }));
});
function fixture() {
  const base = mkdtempSync(join(tmpdir(), 'pi-durable-ui-')), repo = join(base, 'repo'); mkdirSync(repo);
  temporaryRoots.push(base);
  const git = (...args) => execFileSync('git', ['-C', repo, ...args]);
  git('init', '-q'); git('config', 'user.email', 'test@example.invalid'); git('config', 'user.name', 'Test');
  writeFileSync(join(repo, 'code.txt'), 'source\n'); git('add', '.'); git('commit', '-qm', 'base');
  process.env.MEGAI_HOME = join(base, 'shared');
  const report = join(base, 'review.txt'); writeFileSync(report, 'Human inspected exact test evidence and scoped lesson.');
  const evidence = join(base, 'test.txt'); writeFileSync(evidence, 'test outcome: PASS\n');
  return { base, repo, report, evidence, git };
}
async function instance(f, sessionId = 'session-one') {
  const notifications = [], messages = [], confirmations = [];
  const runtime = createExtensionRuntime();
  runtime.sendMessage = (message, options) => messages.push({ message, options });
  const loaded = await loadExtensions([extensionPath], f.repo, undefined, runtime);
  assert.deepEqual(loaded.errors, []);
  assert.equal(loaded.extensions.length, 1);
  const extension = loaded.extensions[0];
  const ctx = { cwd: f.repo, mode: 'tui', hasUI: true, sessionManager: { getSessionId: () => sessionId },
    ui: { notify: (message, kind) => notifications.push({ message, kind }), confirm: async (...args) => {
      confirmations.push(args); return true;
    } } };
  return { extension, ctx, notifications, messages, confirmations,
    tool: async (name, params) => (await extension.tools.get(name).definition.execute('test-call', params, undefined, undefined, ctx)).details,
    command: async (name, args) => extension.commands.get(name).handler(args, ctx) };
}
function input(f) {
  return { action: 'stage', projectId, taskId, title: 'Evidence-based retries', content: 'Reconcile before retry.',
    evidence: [{ path: f.evidence, sha256: createHash('sha256').update(readFileSync(f.evidence)).digest('hex'), observation: 'The tested CLI persisted and loaded the checkpoint.' }] };
}

test('real Pi loader exposes tools and restores saved data into a new session without replay', async () => {
  const f = fixture(), first = await instance(f);
  assert.deepEqual([...first.extension.tools.keys()], ['workflow_checkpoint', 'knowledge_candidate']);
  assert.equal(first.extension.handlers.size, 0, 'no startup hooks, mutation replay or background loops');
  assert.equal(existsSync(join(f.base, 'shared/durable-workflow')), false);
  await first.tool('workflow_checkpoint', { action: 'save', projectId, taskId, expectedRevision: 0,
    phase: 'review', summary: 'Saved after tests', nextAction: 'Review diff', uncertainOperations: [] });
  const fresh = await instance(f, 'session-two');
  const data = await fresh.tool('workflow_checkpoint', { action: 'load', taskId });
  assert.equal(data.checkpoint.sessionId, 'session-one');
  assert.equal(data.checkpoint.nextAction, 'Review diff');
  assert.equal(data.canContinue, true);
  await fresh.command('workflow-resume', taskId);
  assert.equal(fresh.messages.length, 1);
  assert.equal(fresh.messages[0].options.triggerTurn, false);
  assert.match(fresh.messages[0].message.content, /Historical checkpoint data/);
  assert.equal((await first.tool('workflow_checkpoint', { action: 'list' }))[0].revision, 1);
});

test('checkpoint repository selection saves and resumes from a non-Git umbrella', async () => {
  const f = fixture(), one = await instance(f);
  one.ctx.cwd = f.base;
  const params = { action: 'save', repositoryPath: f.repo, projectId, taskId, expectedRevision: 0,
    phase: 'tested', summary: 'Explicit repo', nextAction: 'Revalidate source', uncertainOperations: [] };
  await assert.doesNotReject(() => one.tool('workflow_checkpoint', params),
    'checkpoint repository selection must save from a non-Git umbrella');
  const resumed = await one.tool('workflow_checkpoint', { action: 'load', repositoryPath: f.repo, taskId });
  assert.equal(resumed.canContinue, true);
  assert.equal(resumed.checkpoint.repository, join(realpathSync(f.repo), '.git'));
  assert.equal((await one.tool('workflow_checkpoint', { action: 'list', repositoryPath: f.repo }))[0].revision, 1);
  await assert.rejects(() => one.tool('workflow_checkpoint', params), /Stale checkpoint revision/);
  writeFileSync(join(f.repo, 'code.txt'), 'drift\n');
  assert.equal((await one.tool('workflow_checkpoint', { action: 'load', repositoryPath: f.repo, taskId })).canContinue, false);
});

test('checkpoint repository selection rejects invalid paths without fallback or store writes', async () => {
  const f = fixture(), one = await instance(f);
  for (const repositoryPath of ['', 'repo', '~/repo', join(f.base, 'missing'), f.base, join(f.repo, 'code.txt')]) {
    await assert.rejects(() => one.tool('workflow_checkpoint', { action: 'list', repositoryPath }),
      /repositoryPath|Checkpoint repository unavailable/);
    assert.equal(existsSync(join(f.base, 'shared/durable-workflow')), false);
  }
  one.ctx.cwd = f.base;
  await assert.rejects(() => one.tool('workflow_checkpoint', { action: 'list' }), /Checkpoint repository unavailable/);
  assert.equal(existsSync(join(f.base, 'shared/durable-workflow')), false);
});

test('checkpoint repository selection remains scoped to the explicitly selected repository', async () => {
  const f = fixture(), one = await instance(f), other = fixture();
  // Both repositories use the same private store, but must not share checkpoint records.
  await one.tool('workflow_checkpoint', { action: 'save', repositoryPath: f.repo, projectId, taskId,
    expectedRevision: 0, phase: 'test', summary: 'one repo', nextAction: 'inspect', uncertainOperations: [] });
  assert.deepEqual(await one.tool('workflow_checkpoint', { action: 'list', repositoryPath: other.repo }), []);
  await assert.rejects(() => one.tool('workflow_checkpoint', { action: 'load', repositoryPath: other.repo, taskId }),
    /Checkpoint not found in this repository/);
});

test('only two explicit user command confirmations enable knowledge recall', async () => {
  const f = fixture(), one = await instance(f);
  const candidate = await one.tool('knowledge_candidate', input(f));
  assert.deepEqual(await one.tool('knowledge_candidate', { action: 'search', query: 'retries' }), []);
  await assert.rejects(() => one.tool('knowledge_candidate', { action: 'promote', id: candidate.id }), /Unsupported knowledge action/);
  await one.command('knowledge-promote', candidate.id);
  assert.match(one.notifications.at(-1).message, /Reviewed candidate required/);
  assert.equal(one.confirmations.length, 0);
  await one.command('knowledge-review', `${candidate.id} ${f.report}`);
  assert.equal((await one.tool('knowledge_candidate', { action: 'get', id: candidate.id })).state, 'reviewed');
  assert.equal(one.confirmations.length, 1);
  assert.match(one.confirmations[0][1], /Reconcile before retry/);
  assert.deepEqual(await one.tool('knowledge_candidate', { action: 'search', query: 'retries' }), []);
  await one.command('knowledge-promote', candidate.id);
  assert.equal(one.confirmations.length, 2);
  const two = await instance(f, 'session-two');
  assert.equal((await two.tool('knowledge_candidate', { action: 'search', query: 'retries' }))[0].approval.actor, 'user-ui');
  await two.command('knowledge-revoke', candidate.id);
  assert.deepEqual(await two.tool('knowledge_candidate', { action: 'search', query: 'retries' }), []);
});

test('no UI and canceled confirmation cannot review or promote', async () => {
  const f = fixture(), one = await instance(f), candidate = await one.tool('knowledge_candidate', input(f));
  one.ctx.hasUI = false;
  await one.command('knowledge-review', `${candidate.id} ${f.report}`);
  await one.command('knowledge-promote', candidate.id);
  assert.equal(one.confirmations.length, 0);
  assert.equal((await one.tool('knowledge_candidate', { action: 'get', id: candidate.id })).state, 'candidate');
  one.ctx.hasUI = true; one.ctx.ui.confirm = async () => false;
  await one.command('knowledge-review', `${candidate.id} ${f.report}`);
  assert.equal((await one.tool('knowledge_candidate', { action: 'get', id: candidate.id })).state, 'candidate');
  one.ctx.ui.confirm = async () => true;
  await one.command('knowledge-review', `${candidate.id} ${f.report}`);
  one.ctx.ui.confirm = async () => false;
  await one.command('knowledge-promote', candidate.id);
  assert.equal((await one.tool('knowledge_candidate', { action: 'get', id: candidate.id })).state, 'reviewed');
});

test('tampering during confirmation and concurrent revocation block publication', async () => {
  const f = fixture(), one = await instance(f), candidate = await one.tool('knowledge_candidate', input(f));
  one.ctx.ui.confirm = async () => { writeFileSync(f.report, 'changed report'); return true; };
  await one.command('knowledge-review', `${candidate.id} ${f.report}`);
  assert.match(one.notifications.at(-1).message, /Review report changed/);
  assert.equal((await one.tool('knowledge_candidate', { action: 'get', id: candidate.id })).state, 'candidate');
  one.ctx.ui.confirm = async () => true;
  await one.command('knowledge-review', `${candidate.id} ${f.report}`);
  const second = await instance(f, 'concurrent-session');
  one.ctx.ui.confirm = async () => { await second.command('knowledge-revoke', candidate.id); return true; };
  await one.command('knowledge-promote', candidate.id);
  assert.match(one.notifications.at(-1).message, /revision changed/);
  assert.equal((await one.tool('knowledge_candidate', { action: 'get', id: candidate.id })).state, 'revoked');
});

test('report changes after UI recheck but during source capture refuse review publication', async () => {
  const f = fixture(), one = await instance(f), candidate = await one.tool('knowledge_candidate', input(f));
  const gitPath = realpathSync(execFileSync('which', ['git'], { encoding: 'utf8' }).trim());
  const binaries = join(f.base, 'bin'); mkdirSync(binaries);
  const marker = join(f.base, 'armed');
  writeFileSync(join(binaries, 'git'), `#!${process.execPath}\n
const { existsSync, writeFileSync, unlinkSync } = require('node:fs');
const { spawnSync } = require('node:child_process');
const args = process.argv.slice(2);
if (args.includes('rev-parse') && args.includes('HEAD') && existsSync(${JSON.stringify(marker)})) {
  writeFileSync(${JSON.stringify(f.report)}, 'Different unconfirmed report bytes');
  unlinkSync(${JSON.stringify(marker)});
}
const child = spawnSync(${JSON.stringify(gitPath)}, args, { stdio: 'inherit' });
process.exit(child.status ?? 1);\n`, { mode: 0o700 });
  one.ctx.ui.confirm = async () => { writeFileSync(marker, 'armed'); return true; };
  const previousPath = process.env.PATH;
  try {
    process.env.PATH = `${binaries}:${previousPath}`;
    await one.command('knowledge-review', `${candidate.id} ${f.report}`);
  } finally { process.env.PATH = previousPath; }
  assert.equal((await one.tool('knowledge_candidate', { action: 'get', id: candidate.id })).state, 'candidate',
    'review must not publish bytes different from the confirmed report');
  assert.match(one.notifications.at(-1).message, /report.*(changed|mismatch)/i);
});

test('evidence and source drift after review refuse promotion', async () => {
  const f = fixture(), one = await instance(f), candidate = await one.tool('knowledge_candidate', input(f));
  await one.command('knowledge-review', `${candidate.id} ${f.report}`);
  writeFileSync(join(f.repo, 'code.txt'), 'new source\n');
  await one.command('knowledge-promote', candidate.id);
  assert.match(one.notifications.at(-1).message, /Source changed/);
  writeFileSync(f.evidence, 'changed evidence');
  await one.command('knowledge-promote', candidate.id);
  assert.match(one.notifications.at(-1).message, /Evidence hash mismatch/);
  assert.equal((await one.tool('knowledge_candidate', { action: 'get', id: candidate.id })).state, 'reviewed');
});

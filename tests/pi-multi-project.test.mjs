import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, realpathSync, existsSync, rmSync, symlinkSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { pathToFileURL, fileURLToPath } from 'node:url';

let piRoot = dirname(realpathSync(execFileSync('which', ['pi'], { encoding: 'utf8' }).trim()));
while (!existsSync(join(piRoot, 'package.json'))) piRoot = dirname(piRoot);
const { loadExtensions, createExtensionRuntime } = await import(pathToFileURL(join(piRoot, 'dist/core/extensions/index.js')));
const extensionPath = process.env.MEGAI_DURABLE_EXTENSION || resolve(dirname(fileURLToPath(import.meta.url)), '../pi-defaults/extensions/megai-durable-workflow/index.ts');
const projectId = '59005e36-ecd4-46ed-bb42-f779858b20ce', taskId = 'a59bc58a-2990-4083-9e2a-8530fa0c2269';
const roots = [], previousHome = process.env.MEGAI_HOME;
after(() => {
  if (previousHome === undefined) delete process.env.MEGAI_HOME; else process.env.MEGAI_HOME = previousHome;
  roots.forEach(p => rmSync(p, { recursive: true, force: true }));
});
const git = (cwd, ...args) => execFileSync('git', ['-C', cwd, ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
function fixture() {
  const base = mkdtempSync(join(tmpdir(), 'pi-multi-')), root = join(base, 'project');
  roots.push(base); mkdirSync(root); mkdirSync(join(root, '.pi'));
  const manifest = join(root, '.pi/project.json');
  writeFileSync(manifest, JSON.stringify({ layout: 'multi', planeProject: 'TEST', repositories: ['api', 'web'] }));
  for (const name of ['api', 'web']) {
    const repo = join(root, name); mkdirSync(repo); git(repo, 'init', '-q');
    git(repo, 'config', 'user.email', 'test@example.invalid'); git(repo, 'config', 'user.name', 'Test');
    writeFileSync(join(repo, 'source.txt'), 'base\n'); git(repo, 'add', '.'); git(repo, 'commit', '-qm', 'base');
  }
  const store = join(base, 'private'); process.env.MEGAI_HOME = store;
  return { base, root, manifest, store };
}
async function instance(cwd) {
  const runtime = createExtensionRuntime(), notifications = [];
  const loaded = await loadExtensions([extensionPath], cwd, undefined, runtime);
  assert.deepEqual(loaded.errors, []);
  const extension = loaded.extensions[0];
  const ctx = { cwd, hasUI: true, sessionManager: { getSessionId: () => 'multi-test' },
    ui: { confirm: async () => true, notify: message => notifications.push(message) } };
  return { notifications,
    tool: async (name, params) => (await extension.tools.get(name).definition.execute('call', params, undefined, undefined, ctx)).details,
    command: async (name, args) => extension.commands.get(name).handler(args, ctx) };
}
const save = { action: 'save', projectId, taskId, expectedRevision: 0, phase: 'tested', summary: 'two repositories', nextAction: 'revalidate', uncertainOperations: [] };

test('multi project checkpoint works from non-Git coordination cwd without selecting one component', async () => {
  const f = fixture(), one = await instance(f.root);
  await assert.doesNotReject(() => one.tool('workflow_checkpoint', save), 'configured multi project must checkpoint without root Git');
  const result = await one.tool('workflow_checkpoint', { action: 'load', taskId });
  assert.equal(result.canContinue, true);
  assert.equal(result.checkpoint.source.kind, 'multi');
  assert.equal(result.checkpoint.source.repositories.length, 2);
  assert.equal(result.checkpoint.repository, realpathSync(f.root));
  assert.equal(existsSync(join(f.root, '.git')), false, 'never initialize the coordination root');
  const fresh = await instance(f.base);
  assert.equal((await fresh.tool('workflow_checkpoint', { action: 'load', taskId, repositoryPath: f.root })).canContinue, true);
  await assert.rejects(() => one.tool('workflow_checkpoint', save), /Stale checkpoint revision/);
});

test('multi project explicit manifest takes precedence over an unborn wrapper Git repo', async () => {
  const f = fixture(); git(f.root, 'init', '-q');
  const head = readFileSync(join(f.root, '.git/HEAD'), 'utf8'), one = await instance(f.root);
  await assert.doesNotReject(() => one.tool('workflow_checkpoint', save), 'multi manifest must not snapshot unborn wrapper Git HEAD');
  assert.equal((await one.tool('workflow_checkpoint', { action: 'load', taskId })).canContinue, true);
  assert.equal(readFileSync(join(f.root, '.git/HEAD'), 'utf8'), head);
});

test('multi project changes in either component, manifest or root policy require reconciliation', async () => {
  const f = fixture(), one = await instance(f.root);
  writeFileSync(join(f.root, 'AGENTS.md'), 'local project safety\n');
  await one.tool('workflow_checkpoint', save);
  for (const name of ['api', 'web']) {
    writeFileSync(join(f.root, name, 'source.txt'), 'changed\n');
    assert.equal((await one.tool('workflow_checkpoint', { action: 'load', taskId })).canContinue, false);
    writeFileSync(join(f.root, name, 'source.txt'), 'base\n');
  }
  assert.equal((await one.tool('workflow_checkpoint', { action: 'load', taskId })).canContinue, true);
  writeFileSync(join(f.root, 'AGENTS.md'), 'changed safety\n');
  assert.equal((await one.tool('workflow_checkpoint', { action: 'load', taskId })).canContinue, false);
  writeFileSync(join(f.root, 'AGENTS.md'), 'local project safety\n');
  writeFileSync(f.manifest, readFileSync(f.manifest, 'utf8') + '\n');
  assert.equal((await one.tool('workflow_checkpoint', { action: 'load', taskId })).canContinue, false);
});

test('multi project malformed, missing, duplicate and escaping components fail closed without fallback', async () => {
  for (const names of [[], ['missing'], ['.'], ['../outside'], ['api', 'api'], ['alias'], ['unborn']]) {
    const f = fixture(), one = await instance(f.root);
    mkdirSync(join(f.base, 'outside')); symlinkSync(join(f.base, 'outside'), join(f.root, 'alias'));
    mkdirSync(join(f.root, 'unborn')); git(join(f.root, 'unborn'), 'init', '-q');
    // A wrapper Git repo must never make an invalid component inherit its root.
    git(f.root, 'init', '-q');
    writeFileSync(f.manifest, JSON.stringify({ layout: 'multi', repositories: names }));
    await assert.rejects(() => one.tool('workflow_checkpoint', { action: 'list' }));
    assert.equal(existsSync(join(f.store, 'durable-workflow')), false);
  }
  const f = fixture(), one = await instance(f.root);
  writeFileSync(f.manifest, '{bad json');
  await assert.rejects(() => one.tool('workflow_checkpoint', { action: 'list' }));
  assert.equal(existsSync(join(f.store, 'durable-workflow')), false);
});

test('multi project does not discover undeclared siblings or share component checkpoint scope', async () => {
  const f = fixture(), one = await instance(f.root);
  mkdirSync(join(f.root, 'undeclared')); // Intentionally not a Git repository.
  await one.tool('workflow_checkpoint', save);
  const component = await instance(join(f.root, 'api'));
  assert.deepEqual(await component.tool('workflow_checkpoint', { action: 'list' }), []);
  await assert.rejects(() => component.tool('workflow_checkpoint', { action: 'load', taskId }), /Checkpoint not found/);
  const other = fixture();
  process.env.MEGAI_HOME = f.store;
  assert.deepEqual(await (await instance(other.root)).tool('workflow_checkpoint', { action: 'list' }), []);
});

test('multi project knowledge retains explicit review and whole-vector source validation', async () => {
  const f = fixture(), one = await instance(f.root), evidence = join(f.base, 'test.txt'), report = join(f.base, 'review.txt');
  writeFileSync(evidence, 'PASS'); writeFileSync(report, 'Inspected vector-bound evidence');
  const candidate = await one.tool('knowledge_candidate', { action: 'stage', projectId, taskId, title: 'vector evidence', content: 'Revalidate every component.',
    evidence: [{ path: evidence, sha256: createHash('sha256').update('PASS').digest('hex'), observation: 'two-component fixture passes' }] });
  assert.deepEqual(await one.tool('knowledge_candidate', { action: 'search', query: 'vector' }), []);
  await one.command('knowledge-review', `${candidate.id} ${report}`);
  writeFileSync(join(f.root, 'web/source.txt'), 'different source\n');
  await one.command('knowledge-promote', candidate.id);
  assert.match(one.notifications.at(-1), /Source changed/);
  writeFileSync(join(f.root, 'web/source.txt'), 'base\n');
  await one.command('knowledge-promote', candidate.id);
  assert.equal((await one.tool('knowledge_candidate', { action: 'search', query: 'vector' })).length, 1);
});

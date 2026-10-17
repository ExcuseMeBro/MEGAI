import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, existsSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
const directory = process.env.MEGAI_DURABLE_EXTENSION ? dirname(process.env.MEGAI_DURABLE_EXTENSION)
  : resolve(dirname(fileURLToPath(import.meta.url)), '../pi-defaults/extensions/megai-durable-workflow');
const { DurableStore } = await import(pathToFileURL(join(directory, 'store.mjs')));

test('multi snapshot is read-only; case aliases share project scope on insensitive filesystems', () => {
  const base = mkdtempSync(join(tmpdir(), 'pi-multi-case-'));
  try {
    const cwd = join(base, 'Collection'), alternate = join(base, 'collection'), component = join(cwd, 'Component'), root = join(base, 'private');
    mkdirSync(cwd); mkdirSync(join(cwd, '.pi')); mkdirSync(component);
    writeFileSync(join(cwd, '.pi/project.json'), JSON.stringify({ layout: 'multi', repositories: ['Component'] }));
    const git = (...args) => execFileSync('git', ['-C', component, ...args], { stdio: 'pipe' });
    git('init', '-q'); git('config', 'user.name', 'Test'); git('config', 'user.email', 'test@example.invalid');
    writeFileSync(join(component, 'source.txt'), 'base\n'); git('add', '.'); git('commit', '-qm', 'base');
    const one = new DurableStore({ root, cwd, sessionId: 'read-only-fixture' }), snapshot = one.snapshot();
    assert.equal(snapshot.kind, 'multi');
    assert.equal(snapshot.repositories.length, 1);
    assert.equal(existsSync(root), false);
    assert.equal(existsSync(join(cwd, '.git')), false);
    if (existsSync(alternate)) {
      const two = new DurableStore({ root, cwd: alternate, sessionId: 'case-alias' });
      assert.equal(two.repo.scope, one.repo.scope);
      assert.deepEqual(two.snapshot(), snapshot);
    }
    assert.equal(existsSync(root), false);
  } finally { rmSync(base, { recursive: true, force: true }); }
});

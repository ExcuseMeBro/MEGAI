#!/usr/bin/env node
// Load and expand the delivery commands through the installed Pi runtime, offline.
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

assert.ok(process.env.PI_PACKAGE_ROOT, 'Set PI_PACKAGE_ROOT to the installed Pi package');
const { DefaultResourceLoader, SettingsManager } = await import(
  pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js')));
const { expandPromptTemplate } = await import(
  pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/core/prompt-templates.js')));
const temp = mkdtempSync(join(tmpdir(), 'pi-delivery-prompts-'));
try {
  process.env.PI_OFFLINE = '1';
  const loader = new DefaultResourceLoader({
    cwd: temp, agentDir: join(temp, 'agent'),
    settingsManager: SettingsManager.inMemory({ packages: [] }),
    noExtensions: true, noSkills: true, noThemes: true, noContextFiles: true,
    noPromptTemplates: true,
    additionalPromptTemplatePaths: ['mdev', 'prdev'].map(
      name => resolve(`pi-defaults/prompts/${name}.md`)),
  });
  await loader.reload();
  const { prompts, diagnostics } = loader.getPrompts();
  assert.deepEqual(diagnostics, []);
  assert.deepEqual(prompts.map(p => p.name).sort(), ['mdev', 'prdev']);
  const mdev = expandPromptTemplate('/mdev', prompts);
  const prdev = expandPromptTemplate('/prdev', prompts);
  for (const text of [mdev, prdev]) {
    assert.match(text, /megai queue/);
    assert.match(text, /--remote-dev/);
    assert.match(text, /parent\s+self-review/);
    assert.match(text, /non-force push/);
    assert.doesNotMatch(text, /^(<<<<<<<|=======|>>>>>>>)/m);
  }
  assert.match(mdev, /local `dev` ahead of remote `dev` as a delivery-only row/);
  assert.match(mdev, /uncommitted work remains an\s+explicit unfinished row/);
  assert.match(mdev, /all-repo acceptance and one atomic reservation/);
  assert.match(mdev, /pi-workflow cleanup/);
  assert.match(prdev, /necessary non-force push of verified `dev`/);
  assert.match(prdev, /rev-list --count <main-sha>\.\.<dev-sha>/);
  assert.match(prdev, /never a reason to create a duplicate PR/);
  assert.match(prdev, /After an uncertain create, look up that same identity/);
  assert.match(prdev, /does not|never authorizes/);
  console.log('PASS: /mdev and /prdev load and expand with scoped delivery safeguards');
} finally {
  rmSync(temp, { recursive: true, force: true });
}

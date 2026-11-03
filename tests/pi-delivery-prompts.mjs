#!/usr/bin/env node
import './pi-package.mjs';
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
    assert.match(text, /Brokan/);
    assert.match(text, /self-review/);
    assert.match(text, /git ls-remote/);
    assert.match(text, /:refs\/heads\/dev`/);
    assert.match(text, /evidence graph/);
    assert.match(text, /(Do not run|no) `pi-workflow`, (use )?Plane MCP\/REST/);
    assert.doesNotMatch(text, /git push[^`\n]*(?:--force|--mirror|--all|\s-f\b)/);
    assert.doesNotMatch(text, /^(<<<<<<<|=======|>>>>>>>)/m);
  }
  assert.match(mdev, /does not authorize main/);
  assert.match(mdev, /standing-approval/);
  assert.match(mdev, /Never ask "should I merge\/push\/clean up\?"/);
  assert.match(mdev, /git worktree list --porcelain/);
  assert.match(mdev, /source-current formal PASS/);
  assert.match(mdev, /git rebase dev/);
  assert.match(mdev, /are \*\*not\*\* blockers/);
  assert.match(mdev, /git merge --ff-only task\/<slug>/);
  assert.match(mdev, /non-force push `git push <remote> dev`/);
  assert.match(mdev, /git worktree remove <path>/);
  assert.match(mdev, /git branch -d task\/<slug>/);
  assert.match(mdev, /git push <remote> --delete task\/<slug>/);
  assert.doesNotMatch(mdev, /auto-merge\/rebase|Unknown\/unrelated ahead commits/);
  assert.match(mdev, /wip\/<date>-<slug>/);
  assert.match(mdev, /`kill <PID>`/);
  assert.match(mdev, /never broad `pkill`\/`killall`/);
  assert.doesNotMatch(mdev, /Never terminate a user's session/);
  assert.doesNotMatch(mdev, /pi-workflow cleanup/);
  assert.match(prdev, /does not authorize merging or pushing `main`/);
  assert.match(prdev, /rev-list --count <main-sha>\.\.<dev-sha>/);
  assert.match(prdev, /never create a duplicate/);
  assert.match(prdev, /\(no force\)/);
  assert.match(prdev, /Agent-written on behalf of the user/);
  assert.match(prdev, /A PR is not main delivery/);
  console.log('PASS: /mdev and /prdev load and expand with scoped delivery safeguards');
} finally {
  rmSync(temp, { recursive: true, force: true });
}

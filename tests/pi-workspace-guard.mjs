// Native Pi hooks and real Git fixtures; no agents, network or daemon mutations.
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, realpathSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

assert.ok(process.env.PI_PACKAGE_ROOT, 'PI_PACKAGE_ROOT must identify installed Pi');
const { DefaultResourceLoader, SettingsManager } = await import(pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js')));
const temp = realpathSync(mkdtempSync(join(tmpdir(), 'workspace-guard-')));
const oldHome = process.env.PASEO_HOME;
const root = join(temp, 'PROJECTS/demo');
const paseo = join(temp, 'paseo');
const managed = join(paseo, 'worktrees/hash/task');
const sibling = join(temp, 'PROJECTS/demo-pi');
let cases = 0;
try {
  mkdirSync(root, { recursive: true });
  const git = (...args) => execFileSync('git', ['-C', root, ...args], { stdio: 'pipe' });
  git('init', '-q');
  git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'base', '--allow-empty');
  git('worktree', 'add', '-qb', 'task', managed);
  git('worktree', 'add', '-qb', 'pi', sibling);
  mkdirSync(join(paseo, 'projects'), { recursive: true });
  process.env.PASEO_HOME = paseo;
  const projects = [
    { projectId: 'prj-main', rootPath: root, archivedAt: null },
    { projectId: 'prj-duplicate', rootPath: sibling, archivedAt: null },
  ];
  const workspaces = [
    { workspaceId: 'wks-managed', projectId: 'prj-main', cwd: managed, worktreeRoot: managed, kind: 'worktree', isPaseoOwnedWorktree: true, archivedAt: null },
    { workspaceId: 'wks-primary', projectId: 'prj-main', cwd: root, kind: 'local_checkout', isPaseoOwnedWorktree: false, archivedAt: null },
    { workspaceId: 'wks-duplicate', projectId: 'prj-duplicate', cwd: sibling, kind: 'worktree', isPaseoOwnedWorktree: false, archivedAt: null },
  ];
  const save = (name, data) => writeFileSync(join(paseo, 'projects', name + '.json'), JSON.stringify(data));
  save('projects', projects); save('workspaces', workspaces);
  const loader = new DefaultResourceLoader({ cwd: root, agentDir: join(temp, 'agent'),
    settingsManager: SettingsManager.inMemory({ packages: [] }),
    additionalExtensionPaths: [process.env.MEGAI_TEST_GUARD || resolve('pi-skill/workspace-guard/index.ts')],
  });
  await loader.reload();
  const loaded = loader.getExtensions();
  assert.deepEqual(loaded.errors, []);
  assert.equal(loaded.extensions.length, 1);
  const extension = loaded.extensions[0];
  assert.ok(extension.handlers.has('tool_call'));
  const check = async (toolName, input, blocked, cwd = root) => {
    const before = structuredClone(input);
    let result;
    for (const hook of extension.handlers.get('tool_call')) result = await hook({ toolName, input }, { cwd });
    assert.equal(Boolean(result?.block), blocked, `${toolName}: ${JSON.stringify(input)}: ${result?.reason}`);
    assert.deepEqual(input, before, 'Guard never silently rewrites arguments');
    cases++;
  };
  const valid = { isolation: 'worktree', projectId: 'prj-main', worktreeSlug: 'new-task', baseBranch: 'pi' };
  // This exact accidental route created the real duplicate project.
  await check('mcp', { tool: 'paseo_create_workspace', args: { isolation: 'local', path: sibling } }, true);
  for (const cwd of [root, sibling, managed]) {
    await check('paseo_create_workspace', valid, false, cwd);
    await check('mcp', { tool: 'paseo_create_workspace', args: valid }, false, cwd);
    await check('mcp__paseo', { tool: 'create-workspace', args: JSON.stringify(valid) }, false, cwd);
    await check('paseo_create_workspace', { ...valid, projectId: 'prj-duplicate' }, true, cwd);
  }
  for (const args of [{}, { isolation: 'worktree' }, { ...valid, path: root }, { ...valid, worktreeSlug: '../escape' }, { ...valid, worktreeSlug: '/tmp/escape' }]) {
    await check('paseo_create_workspace', args, true);
    await check('mcp', { server: 'paseo', tool: 'create_workspace', args: JSON.stringify(args) }, true);
  }
  for (const args of [{}, { workspaceId: 'wks-primary' }, { workspaceId: 'wks-duplicate' }, { workspaceId: 'missing' }]) await check('paseo_create_agent', args, true);
  await check('paseo_create_agent', { workspaceId: 'wks-managed', provider: 'pi/existing-model', settings: { thinkingOptionId: 'high' } }, false);
  await check('mcp', { tool: 'paseo/create_workspace', args: '{broken' }, true);
  await check('mcp', { tool: 'create_workspace', args: 'null' }, true);
  await check('multi_tool_use.parallel', { tool_uses: [{ recipient_name: 'functions.mcp', parameters: { tool: 'paseo_create_workspace', args: { isolation: 'local', path: sibling } } }] }, true);
  await check('multi_tool_use.parallel', { tool_uses: [{ recipient_name: 'functions.read', parameters: { path: 'anything' } }] }, false, '/missing');
  for (const command of ['git worktree add ../demo-pi pi', 'git -C /repo worktree add ../copy pi', 'git clone local ../demo-copy', 'paseo workspace create --path ../demo-pi', 'paseo --json project create ../demo-pi', 'paseo clone repo']) await check('bash', { command }, true);
  for (const [name, input] of [['read', { path: 'anything' }], ['bash', { command: 'git worktree list --porcelain' }], ['mcp', { search: 'create_workspace' }], ['mcp', { action: 'ui-messages', tool: 'paseo_create_workspace' }], ['mcp', { server: 'plane', tool: 'create_workspace' }]]) await check(name, input, false, '/missing/not-a-repo');
  assert.deepEqual([...extension.handlers.keys()], ['tool_call'], 'No startup work or model/provider hooks');
  workspaces[0].archivedAt = '2026-01-01'; save('workspaces', workspaces);
  await check('paseo_create_agent', { workspaceId: 'wks-managed' }, true);
  workspaces[0].archivedAt = null; workspaces[0].cwd = sibling; save('workspaces', workspaces);
  await check('paseo_create_agent', { workspaceId: 'wks-managed' }, true);
  save('projects', [...projects, { ...projects[0], projectId: 'prj-ambiguous' }]);
  await check('paseo_create_workspace', valid, true);
  save('projects', projects.slice(1));
  await check('paseo_create_workspace', valid, true);
  save('projects', {});
  await check('paseo_create_workspace', valid, true);
  rmSync(join(paseo, 'projects/projects.json'));
  await check('paseo_create_workspace', valid, true);
  // Exercise the actual audit command with real Git and a fixture-only CLI.
  git('worktree', 'remove', sibling);
  const external = join(temp, 'external/worktree');
  git('worktree', 'add', '-qb', 'external', external);
  save('projects', [projects[0]]);
  workspaces[0].cwd = managed;
  const cliDir = join(temp, 'bin'); mkdirSync(cliDir);
  writeFileSync(join(cliDir, 'paseo'), '#!/usr/bin/env node\nconst fs=require("node:fs"); process.stdout.write(fs.readFileSync(process.env.PASEO_FIXTURE_DIR+"/live-"+process.argv[3]+".json"));\n', { mode: 0o700 });
  writeFileSync(join(temp, 'live-project.json'), JSON.stringify([{ projectId: 'prj-main', name: 'demo', path: root }]));
  const audit = rows => {
    save('workspaces', rows);
    writeFileSync(join(temp, 'live-workspace.json'), JSON.stringify(rows.map(row => ({ workspaceId: row.workspaceId, cwd: row.cwd, project: 'demo', isolation: 'worktree' }))));
    return spawnSync(process.execPath, [resolve('tests/workspace-layout-live.mjs'), '--root', root], {
      encoding: 'utf8', env: { ...process.env, PATH: cliDir + ':' + process.env.PATH, PASEO_FIXTURE_DIR: temp }, timeout: 10000,
    });
  };
  const validAudit = audit([workspaces[0]]);
  assert.equal(validAudit.status, 0, validAudit.stdout + validAudit.stderr);
  for (const row of [
    { ...workspaces[0], workspaceId: 'wks-missing', cwd: join(temp, 'missing') },
    { ...workspaces[0], workspaceId: 'wks-external', cwd: external, worktreeRoot: external, isPaseoOwnedWorktree: false },
  ]) {
    const result = audit([workspaces[0], row]);
    assert.equal(result.status, 1, 'Audit falsely passed bad active workspace: ' + result.stdout + result.stderr);
  }
  console.log(`PASS: ${cases} native Pi hook cases + 3 full audit CLI regressions; real Git identity, missing/unmanaged layout rejection, no argument changes or startup I/O.`);
} finally {
  if (oldHome === undefined) delete process.env.PASEO_HOME; else process.env.PASEO_HOME = oldHome;
  rmSync(temp, { recursive: true, force: true });
}

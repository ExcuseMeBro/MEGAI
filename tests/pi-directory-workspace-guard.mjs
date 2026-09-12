// Regression: native Pi hook and identity CLI, isolated non-Git registry fixtures.
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync, realpathSync, symlinkSync } from 'node:fs';
import { execFileSync, spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

assert.ok(process.env.PI_PACKAGE_ROOT, 'PI_PACKAGE_ROOT must identify installed Pi');
const { DefaultResourceLoader, SettingsManager } = await import(pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js')));
const temp = realpathSync(mkdtempSync(join(tmpdir(), 'directory-review-')));
const oldHome = process.env.PASEO_HOME;
const root = join(temp, 'ADAM');
const home = join(temp, 'paseo');
const guard = resolve('pi-skill/workspace-guard/index.ts');
const cli = resolve('pi-skill/workspace-guard/identity.mjs');
let cases = 0;
try {
  mkdirSync(root);
  mkdirSync(join(home, 'projects'), { recursive: true });
  process.env.PASEO_HOME = home;
  const projects = [{ projectId: 'prj-directory', kind: 'non_git', rootPath: root, archivedAt: null }];
  const rows = [{ workspaceId: 'wks-directory', projectId: 'prj-directory', cwd: root,
    kind: 'directory', isPaseoOwnedWorktree: false, worktreeRoot: null, archivedAt: null }];
  const save = (name, value) => writeFileSync(join(home, 'projects', name + '.json'), JSON.stringify(value));
  save('projects', projects); save('workspaces', rows);
  const sentinel = join(root, 'migration-config.txt');
  writeFileSync(sentinel, 'review-only data; no migration execution\n');
  const loader = new DefaultResourceLoader({ cwd: root, agentDir: join(temp, 'agent'),
    settingsManager: SettingsManager.inMemory({ packages: [] }), additionalExtensionPaths: [guard] });
  await loader.reload();
  const loaded = loader.getExtensions();
  assert.deepEqual(loaded.errors, []);
  assert.equal(loaded.extensions.length, 1);
  const extension = loaded.extensions[0];
  const check = async (toolName, input, expected, cwd = root) => {
    const original = structuredClone(input);
    let result;
    for (const hook of extension.handlers.get('tool_call')) result = await hook({ toolName, input }, { cwd });
    assert.equal(Boolean(result?.block), expected,
      `directory reviewer launch must not require Git: ${toolName}: ${JSON.stringify(input)}: ${result?.reason}`);
    assert.deepEqual(input, original, 'Arguments must remain unchanged');
    cases++;
  };
  const agent = { workspaceId: 'wks-directory', provider: 'pi/existing-model',
    labels: { 'megai.access': 'read-only' }, settings: { thinkingOptionId: 'high' } };
  // Original symptom: a uniquely registered directory reviewer is rejected before launch.
  await check('paseo_create_agent', agent, false);
  const workspace = { isolation: 'local', projectId: 'prj-directory', path: root, title: 'Read-only migration review' };
  await check('paseo_create_workspace', workspace, false);
  await check('paseo_create_workspace', { isolation: 'local', projectId: 'prj-directory' }, false);
  await check('mcp', { tool: 'paseo_create_agent', args: JSON.stringify(agent) }, false);
  await check('mcp__paseo', { tool: 'create-agent', args: agent }, false);
  await check('multi_tool_use.parallel', { tool_uses: [{ recipient_name: 'functions.mcp', parameters: { tool: 'paseo_create_agent', args: agent } }] }, false);
  for (const invalid of [{ ...agent, labels: {} }, { ...agent, labels: { 'megai.access': 'write' } },
    { ...agent, labels: { 'megai.access': true } }, { ...agent, provider: 'codex/anything' },
    { ...agent, workspaceId: 'unknown' }]) await check('paseo_create_agent', invalid, true);
  for (const patch of [{ projectId: 'other' }, { path: temp }, { isolation: 'worktree' },
    { branchName: 'task' }, { baseBranch: 'main' }, { mode: 'branch-off' }, { worktreeSlug: 'new' },
    { branch: 'main' }, { prNumber: 1 }, { forge: 'github' }]) {
    await check('paseo_create_workspace', { ...workspace, ...patch }, true);
  }
  await check('paseo_create_project', { path: root }, true);
  const result = spawnSync(process.execPath, [cli, '--root', root], { encoding: 'utf8', timeout: 10000 });
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(JSON.parse(result.stdout), { root, checkout: root, commonDir: null,
    projectId: 'prj-directory', kind: 'directory' });
  const alias = join(temp, 'alias'); symlinkSync(root, alias);
  await check('paseo_create_agent', agent, false, alias);
  for (const patch of [{ archivedAt: '2026-01-01' }, { projectId: 'other' }, { cwd: temp },
    { kind: 'local_checkout' }, { isPaseoOwnedWorktree: true }, { worktreeRoot: root }]) {
    save('workspaces', [{ ...rows[0], ...patch }]); await check('paseo_create_agent', agent, true);
  }
  save('workspaces', rows);
  for (const invalid of [[], {}, [...projects, { ...projects[0], projectId: 'duplicate' }],
    [{ ...projects[0], kind: 'git' }], [{ ...projects[0], archivedAt: '2026-01-01' }]]) {
    save('projects', invalid); await check('paseo_create_agent', agent, true);
  }
  save('projects', projects);
  writeFileSync(join(root, '.git'), 'gitdir: /missing/broken-checkout\n');
  await check('paseo_create_agent', agent, true);
  rmSync(join(root, '.git'));
  mkdirSync(join(root, '.git')); // Corrupt Git cannot become a directory exception.
  await check('paseo_create_agent', agent, true);
  rmSync(join(root, '.git'), { recursive: true });
  // Nested real Git retains its own identity; never inherit umbrella access.
  const component = join(root, 'main-be'); mkdirSync(component);
  execFileSync('git', ['-C', component, 'init', '-q']);
  await check('paseo_create_agent', agent, true, component);
  // A true directory still works after the negative fixtures, without mutations.
  await check('paseo_create_agent', agent, false);
  assert.equal(readFileSync(sentinel, 'utf8'), 'review-only data; no migration execution\n');
  assert.deepEqual(JSON.parse(readFileSync(join(home, 'projects/projects.json'))), projects);
  assert.deepEqual(JSON.parse(readFileSync(join(home, 'projects/workspaces.json'))), rows);
  assert.deepEqual([...extension.handlers.keys()], ['tool_call'], 'No startup/model/auth hooks');
  console.log(`PASS: ${cases} native directory hook cases and actual identity CLI; Git/cross-project/ambiguous guards retained.`);
} finally {
  if (oldHome === undefined) delete process.env.PASEO_HOME; else process.env.PASEO_HOME = oldHome;
  rmSync(temp, { recursive: true, force: true });
}

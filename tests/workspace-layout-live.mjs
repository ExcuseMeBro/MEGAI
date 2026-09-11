// Explicit local read-only acceptance probe: actual daemon CLI plus Git/disk.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { dirname, basename, resolve } from 'node:path';
import { gitIdentity, projectIdentity, registry, validateWorkspace } from '../pi-skill/workspace-guard/identity.mjs';

assert.equal(process.argv.length, 4, 'Usage: node tests/workspace-layout-live.mjs --root PRIMARY');
assert.equal(process.argv[2], '--root');
const root = resolve(process.argv[3]);
const identity = await projectIdentity(root);
assert.equal(identity.root, root, 'Probe must target the canonical primary');
const query = args => JSON.parse(execFileSync('paseo', ['--json', ...args], { encoding: 'utf8', timeout: 10000, maxBuffer: 2 * 1024 * 1024 }));
const projects = query(['project', 'ls']);
const workspaces = query(['workspace', 'ls']);
assert.ok(Array.isArray(projects) && Array.isArray(workspaces), 'Unsupported live Paseo response');
const records = await registry('workspaces');
const problems = [];
const related = [];
for (const project of projects) {
  if (typeof project.path !== 'string') throw new Error('Missing live project path');
  let git;
  try { git = await gitIdentity(project.path); } catch {
    if (dirname(project.path) === dirname(root) && basename(project.path).startsWith(basename(root) + '-')) problems.push('Stale sibling project: ' + project.projectId);
    continue;
  }
  if (git.commonDir === identity.commonDir) related.push(project);
}
if (related.length !== 1 || related[0]?.projectId !== identity.projectId) problems.push('Canonical Git repository has multiple/missing live Paseo projects: ' + related.map(p => p.projectId).join(','));
const fields = execFileSync('git', ['-C', root, 'worktree', 'list', '--porcelain', '-z'], { encoding: 'utf8' }).split('\0');
for (const field of fields.filter(value => value.startsWith('worktree '))) {
  const checkout = field.slice(9);
  if (dirname(checkout) === dirname(root) && basename(checkout).startsWith(basename(root) + '-')) problems.push('Sibling checkout: ' + checkout);
}
let checked = 0;
for (const workspace of workspaces) {
  const matching = records.filter(row => row.workspaceId === workspace.workspaceId && !row.archivedAt);
  const associated = matching.some(row => related.some(project => project.projectId === row.projectId))
    || related.some(project => project.name === workspace.project);
  let git;
  try { git = await gitIdentity(workspace.cwd); } catch {
    if (associated) problems.push('Unreadable active project workspace: ' + workspace.workspaceId);
    continue;
  }
  if (git.commonDir !== identity.commonDir) {
    if (associated) problems.push('Active workspace points at a different Git repository: ' + workspace.workspaceId);
    continue;
  }
  checked++;
  if (matching.length !== 1 || matching[0].cwd !== workspace.cwd || matching[0].projectId !== identity.projectId) problems.push('Wrong canonical workspace association: ' + workspace.workspaceId);
  const canonical = projects.find(p => p.projectId === identity.projectId);
  if (workspace.project !== canonical?.name) problems.push('Live daemon grouping mismatch: ' + workspace.workspaceId);
  if (git.checkout !== identity.root) {
    try {
      await validateWorkspace(workspace.workspaceId, identity);
      if (workspace.isolation !== 'worktree') throw new Error('Live workspace is not isolated');
    } catch (error) { problems.push('Unmanaged active worktree: ' + workspace.workspaceId + ': ' + error.message); }
  }
}
assert.ok(checked > 0, 'No live canonical workspace observed');
console.log(JSON.stringify({ status: problems.length ? 'FAIL' : 'PASS', root, projectId: identity.projectId, checkedWorkspaces: checked, problems }, null, 2));
process.exitCode = problems.length ? 1 : 0;

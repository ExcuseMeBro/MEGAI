// Read-only identity lookup. No daemon/config writes, network or startup work.
import { execFile } from 'node:child_process';
import { readFile, realpath } from 'node:fs/promises';
import { homedir } from 'node:os';
import { join, relative, isAbsolute, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { promisify } from 'node:util';

const exec = promisify(execFile);
export const paseoHome = () => resolve(process.env.PASEO_HOME || join(homedir(), '.paseo'));

async function git(cwd, args) {
  const env = { ...process.env };
  for (const key of ['GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE']) delete env[key];
  const result = await exec('git', ['-C', cwd, ...args], { env, timeout: 5000, maxBuffer: 1024 * 1024 });
  return result.stdout;
}

export async function gitIdentity(cwd) {
  const fields = (await git(cwd, ['worktree', 'list', '--porcelain', '-z'])).split('\0');
  if (!fields[0]?.startsWith('worktree ') || fields.includes('bare')) throw new Error('A non-bare Git project is required');
  const root = await realpath(fields[0].slice(9));
  const commonDir = await realpath((await git(cwd, ['rev-parse', '--path-format=absolute', '--git-common-dir'])).replace(/\n$/, ''));
  const checkout = await realpath((await git(cwd, ['rev-parse', '--show-toplevel'])).replace(/\n$/, ''));
  return { root, commonDir, checkout };
}

export async function registry(name, home = paseoHome()) {
  if (!['projects', 'workspaces'].includes(name)) throw new Error('Unknown registry');
  const value = JSON.parse(await readFile(join(home, 'projects', name + '.json'), 'utf8'));
  const key = name === 'projects' ? 'projectId' : 'workspaceId';
  if (!Array.isArray(value) || value.some(row => !row || typeof row !== 'object' || Array.isArray(row)
      || typeof row[key] !== 'string' || !row[key]
      || (row.archivedAt != null && typeof row.archivedAt !== 'string'))
      || new Set(value.map(row => row[key])).size !== value.length) throw new Error(`Malformed Paseo ${name} registry`);
  return value;
}

export async function projectIdentity(cwd, home = paseoHome()) {
  const identity = await gitIdentity(cwd);
  const projects = await registry('projects', home);
  const matches = [];
  for (const project of projects) {
    if (project.archivedAt || typeof project.rootPath !== 'string') continue;
    let root;
    try { root = await realpath(project.rootPath); } catch { continue; }
    if (root === identity.root) matches.push(project);
  }
  if (matches.length !== 1 || typeof matches[0].projectId !== 'string' || !matches[0].projectId) {
    throw new Error('Canonical Git primary must have exactly one active Paseo project; reconcile registration, never create a sibling project');
  }
  return { ...identity, projectId: matches[0].projectId };
}

export async function validateWorkspace(workspaceId, identity, home = paseoHome()) {
  const rows = (await registry('workspaces', home)).filter(row => row.workspaceId === workspaceId && !row.archivedAt);
  if (rows.length !== 1) throw new Error('Explicit active workspaceId is missing or ambiguous');
  const row = rows[0];
  if (row.projectId !== identity.projectId || row.kind !== 'worktree' || row.isPaseoOwnedWorktree !== true || typeof row.cwd !== 'string' || typeof row.worktreeRoot !== 'string') {
    throw new Error('Delegate workspace must be a Paseo-managed worktree of the canonical project');
  }
  const actual = await gitIdentity(row.cwd);
  const managedRoot = await realpath(join(home, 'worktrees'));
  const location = relative(managedRoot, actual.checkout);
  if (!location || location === '..' || location.startsWith('../') || isAbsolute(location)
      || actual.root !== identity.root || actual.commonDir !== identity.commonDir
      || actual.checkout === identity.root || await realpath(row.worktreeRoot) !== actual.checkout) {
    throw new Error('Workspace filesystem/Git identity does not match its managed canonical registration');
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  if (process.argv.length !== 4 || process.argv[2] !== '--root') {
    console.error('Usage: node identity.mjs --root EXISTING_GIT_CHECKOUT');
    process.exitCode = 2;
  } else {
    try { console.log(JSON.stringify(await projectIdentity(process.argv[3]))); }
    catch (error) { console.error('BLOCKED: ' + error.message); process.exitCode = 2; }
  }
}

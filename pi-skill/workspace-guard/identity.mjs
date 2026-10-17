// Read-only project identity from Git and explicit local project configuration.
// No external workspace registry, daemon, or network access.
import { execFile } from 'node:child_process';
import { readFile, realpath, lstat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { dirname, join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { promisify } from 'node:util';

const exec = promisify(execFile);
async function git(cwd, ...args) {
  const env = { ...process.env, LC_ALL: 'C' };
  for (const key of ['GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE']) delete env[key];
  const result = await exec('git', ['-C', cwd, ...args], { env, timeout: 5000, maxBuffer: 1024 * 1024 });
  return result.stdout.trimEnd();
}

export async function gitIdentity(cwd) {
  const fields = (await git(cwd, 'worktree', 'list', '--porcelain', '-z')).split('\0');
  if (!fields[0]?.startsWith('worktree ') || fields.includes('bare')) throw new Error('A non-bare Git project is required');
  const root = await realpath(fields[0].slice(9));
  const commonDir = await realpath(await git(cwd, 'rev-parse', '--path-format=absolute', '--git-common-dir'));
  const checkout = await realpath(await git(cwd, 'rev-parse', '--show-toplevel'));
  return { root, commonDir, checkout };
}

async function configAt(path) {
  let data;
  try { data = JSON.parse(await readFile(join(path, '.pi/project.json'), 'utf8')); }
  catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error; // Malformed or unreadable configuration must not silently fall back.
  }
  if (!data || !['mono', 'multi'].includes(data.layout)) throw new Error('Malformed local project configuration');
  const repos = data.repositories ?? (data.layout === 'mono' ? ['.'] : null);
  if (!Array.isArray(repos) || !repos.length || repos.some(name => typeof name !== 'string' || !name)) {
    throw new Error('Malformed local project repositories');
  }
  return { ...data, repositories: repos };
}

export async function projectIdentity(cwd) {
  let source;
  try { source = await gitIdentity(cwd); }
  catch (error) {
    if (error.code !== 128 || !/^fatal: not a git repository\b/m.test(error.stderr ?? '')) throw error;
    const root = await realpath(cwd);
    // A broken checkout is not a non-Git umbrella. Never grant a directory
    // identity when Git metadata exists but cannot be read.
    for (let folder = root; ; folder = dirname(folder)) {
      try { await lstat(join(folder, '.git')); throw new Error('Git metadata exists; repair the checkout'); }
      catch (probe) { if (probe.code !== 'ENOENT') throw probe; }
      if (dirname(folder) === folder) break;
    }
    source = { root, checkout: root, commonDir: null, kind: 'directory' };
  }
  const anchor = source.root;
  let selected;
  for (let folder = anchor; ; folder = dirname(folder)) {
    const config = await configAt(folder);
    if (config) {
      const repos = await Promise.all(config.repositories.map(async name => {
        const path = resolve(folder, name);
        if (path !== folder && !path.startsWith(folder + '/')) throw new Error('Repository escapes project folder');
        const canonical = await realpath(path);
        if (canonical !== folder && !canonical.startsWith(folder + '/')) throw new Error('Repository symlink escapes project folder');
        return canonical;
      }));
      if (config.layout === 'mono' && repos.length !== 1) throw new Error('Mono project needs one repository');
      if (repos.includes(anchor) || (source.commonDir === null && folder === anchor)) {
        selected = { root: folder, config };
      }
    }
    if (dirname(folder) === folder || folder === resolve(process.env.PI_PROJECTS_ROOT || join(process.env.HOME || '', 'PROJECTS'))) break;
  }
  if (!selected && source.commonDir === null) throw new Error('Non-Git project needs explicit .pi/project.json');
  const root = selected?.root ?? source.root;
  return { ...source, root, projectId: 'git-' + createHash('sha256').update(root).digest('hex').slice(0, 24) };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  if (process.argv.length !== 4 || process.argv[2] !== '--root') {
    console.error('Usage: node identity.mjs --root EXISTING_CHECKOUT_OR_PROJECT_DIRECTORY');
    process.exitCode = 2;
  } else {
    try { console.log(JSON.stringify(await projectIdentity(process.argv[3]))); }
    catch (error) { console.error('BLOCKED: ' + error.message); process.exitCode = 2; }
  }
}

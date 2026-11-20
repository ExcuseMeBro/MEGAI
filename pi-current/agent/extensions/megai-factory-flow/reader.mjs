import { execFile } from 'node:child_process';
import { constants } from 'node:fs';
import { lstat, open } from 'node:fs/promises';
import { dirname, isAbsolute, join, resolve } from 'node:path';
import { promisify } from 'node:util';
import { FlowError, isProject, task } from './core.mjs';

const git = promisify(execFile);
const BOARD_LIMIT = 8 * 1024 * 1024;
const DETAIL_LIMIT = 2 * 1024 * 1024;
const EVAL_LIMIT = 256 * 1024;
const record = x => x && typeof x === 'object' && !Array.isArray(x);

async function readFile(path, max) {
  const file = await open(path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
  try {
    const initial = await file.stat();
    if (!initial.isFile() || initial.size > max) throw new FlowError('Expected a bounded regular JSON file.');
    const buf = Buffer.alloc(initial.size + 1);
    let total = 0;
    while (total < buf.length) {
      const { bytesRead } = await file.read(buf, total, buf.length - total, total);
      if (!bytesRead) break;
      total += bytesRead;
    }
    if (total !== initial.size || (await file.stat()).mtimeMs !== initial.mtimeMs) throw new FlowError('JSON file changed during read.');
    return JSON.parse(buf.subarray(0, total).toString('utf8'));
  } finally { await file.close(); }
}

export async function loadEval(cwd, path) {
  if (!path || path.length > 1024 || /[\p{Cc}\p{Cf}]/u.test(path)) throw new FlowError('Provide the path to a private eval JSON file.');
  try { return await readFile(resolve(cwd, path), EVAL_LIMIT); }
  catch { throw new FlowError('Eval JSON is unreadable, invalid, linked or oversized (256 KiB limit).'); }
}

async function binding(cwd) {
  const env = { ...process.env };
  for (const key of ['GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE']) delete env[key];
  const options = { cwd, env, timeout: 2000, maxBuffer: 8192 };
  let root;
  try {
    root = (await git('git', ['rev-parse', '--show-toplevel'], options)).stdout.replace(/\r?\n$/, '');
    if (!isAbsolute(root) || /[\p{Cc}\p{Cf}]/u.test(root)) throw new FlowError('Invalid repository root.');
  }
  catch { throw new FlowError('Start Factory Flow from the bound repository.'); }
  const path = join(root, '.pi', 'project.json');
  try {
    if (!(await lstat(dirname(path))).isDirectory()) throw new FlowError('.pi must be an ordinary directory.');
    const config = await readFile(path, 65536);
    if (!record(config)) throw new FlowError('Invalid .pi/project.json.');
    if (config.brokanProject !== undefined) {
      if (!isProject(config.brokanProject)) throw new FlowError('Invalid brokanProject in .pi/project.json.');
      return { project: config.brokanProject };
    }
  } catch (err) {
    if (err.code !== 'ENOENT') throw new FlowError('Could not safely read the repository’s .pi/project.json.');
  }
  let url;
  try { url = (await git('git', ['remote', 'get-url', 'origin'], options)).stdout.trim(); }
  catch { throw new FlowError('Set brokanProject in .pi/project.json for this repository.'); }
  const match = /^(?:(?:https:\/\/|ssh:\/\/git@)github\.com\/|git@github\.com:)([\w.-]+)\/([\w.-]+?)(?:\.git)?$/i.exec(url);
  const project = match?.[2]?.toLowerCase();
  if (!isProject(project)) throw new FlowError('Set brokanProject in .pi/project.json for this repository.');
  return { project, repo: `${match[1]}/${match[2]}`.toLowerCase() };
}

export function reader(port = 1317) {
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new FlowError('Invalid local Brokan port.');
  async function get(path, max) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}${path}`, { redirect: 'error', signal: AbortSignal.timeout(3500) });
      if (!response.ok || !response.body || Number(response.headers.get('content-length')) > max) {
        await response.body?.cancel();
        throw new FlowError('Brokan read failed or exceeded its size limit.');
      }
      const chunks = [], stream = response.body.getReader();
      let size = 0;
      try {
        for (;;) {
          const { done, value } = await stream.read();
          if (done) break;
          size += value.length;
          if (size > max) throw new FlowError('Brokan response exceeded its size limit.');
          chunks.push(value);
        }
      } finally { await stream.cancel(); }
      const body = JSON.parse(Buffer.concat(chunks).toString('utf8'));
      if (!record(body)) throw new FlowError('Invalid Brokan response.');
      return body;
    } catch (err) {
      if (err instanceof FlowError) throw err;
      throw new FlowError('Local Brokan read failed; no state inferred.');
    }
  }

  return {
    async board(cwd) {
      const { project, repo } = await binding(cwd);
      const { projects, tasks, done_hidden } = await get(`/api/board?project=${project}`, BOARD_LIMIT);
      const matches = Array.isArray(projects) ? projects.filter(p => p?.slug === project) : [];
      if (matches.length !== 1 || matches[0].archived !== false || (repo &&
          (!Array.isArray(matches[0].repos) || !matches[0].repos.some(item => typeof item === 'string' && item.toLowerCase() === repo)))) {
        throw new FlowError('Brokan project is not linked, active or available.');
      }
      if (!Array.isArray(tasks) || tasks.length > 2000) throw new FlowError('Brokan returned an invalid or oversized project board.');
      const result = new Map();
      for (const value of tasks) {
        const item = task(value, project);
        if (result.has(item.id)) throw new FlowError('Duplicate tasks in Brokan project.');
        result.set(item.id, item);
      }
      return { project, tasks: result, doneHidden: Number.isSafeInteger(done_hidden) && done_hidden > 0 };
    },
    async detail(project, id) {
      if (!isProject(project) || !Number.isSafeInteger(id) || id < 1) throw new FlowError('Invalid task selector.');
      const { task: current, comments } = await get(`/api/tasks/${id}`, DETAIL_LIMIT);
      const value = task(current, project, id);
      if (!Array.isArray(comments) || comments.length !== value.comments) throw new FlowError('Brokan comments are incomplete; read again manually.');
      return { value, comments };
    },
  };
}

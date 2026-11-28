import { constants } from 'node:fs';
import { mkdir, open, unlink } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { join } from 'node:path';
import { promisify } from 'node:util';

const git = promisify(execFile);
const ORIGIN = 'http://127.0.0.1:1317';
const MAX_BODY = 16 * 1024 * 1024;
const MAX_CONFIG = 64 * 1024;
const SLUG = /^[a-z0-9][a-z0-9_-]{0,63}$/;
const REPO = /^[\w.-]+\/[\w.-]+$/;

export class FactoryError extends Error {}
export type Task = { id: number; project: string; status: string; human: boolean; updated?: string };
export const eligible = (task: Task) => !task.human && ['doing', 'todo'].includes(task.status);
export const handedOff = (task: Task) => ['review', 'done'].includes(task.status);

export function selection(input: string): { project?: string; id?: number } {
  const [project, number, extra] = input.trim().split('#');
  if (!input.trim()) return {};
  const id = Number(number);
  if (!SLUG.test(project) || extra !== undefined || project === 'all' ||
      (number !== undefined && (!/^[1-9]\d{0,15}$/.test(number) || !Number.isSafeInteger(id)))) {
    throw new FactoryError('Usage: /factory [project | project#123 | parallel [2-5] | watch [parallel [2-5]] | status | stop]');
  }
  return number === undefined ? { project } : { project, id };
}

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new FactoryError('Invalid Brokan response.');
  return value as Record<string, unknown>;
}

function parseTask(value: unknown, project: string): Task {
  const task = record(value);
  if (task.project !== project || typeof task.id !== 'number' || !Number.isSafeInteger(task.id) || task.id < 1 ||
      typeof task.status !== 'string' || typeof task.human !== 'boolean') {
    throw new FactoryError('Brokan task identity or state mismatch.');
  }
  return { id: task.id, project, status: task.status, human: task.human,
    // Comments do not move updated_at, so a new comment also counts as a change.
    ...(typeof task.updated_at === 'string' ? { updated: `${task.updated_at}#${typeof task.comments === 'number' ? task.comments : ''}` } : {}) };
}

async function get(path: string, signal?: AbortSignal): Promise<Record<string, unknown>> {
  const timeout = AbortSignal.timeout(4000);
  const response = await fetch(`${ORIGIN}${path}`, {
    redirect: 'error', signal: signal ? AbortSignal.any([timeout, signal]) : timeout,
  });
  if (!response.ok || !response.body || Number(response.headers.get('content-length')) > MAX_BODY) {
    await response.body?.cancel();
    throw new FactoryError('Brokan response unavailable or oversized.');
  }
  const chunks: Uint8Array[] = [];
  let size = 0;
  const reader = response.body.getReader();
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.length;
      if (size > MAX_BODY) throw new FactoryError('Brokan response oversized.');
      chunks.push(value);
    }
  } finally {
    await reader.cancel();
  }
  return record(JSON.parse(Buffer.concat(chunks).toString('utf8')));
}

export async function readTask(project: string, id: number, signal?: AbortSignal) {
  return (await readDetails(project, id, signal)).task;
}

/** The task plus its raw comments (validated by lessons.mjs), from the same single read. */
export async function readDetails(project: string, id: number, signal?: AbortSignal) {
  const body = await get(`/api/tasks/${id}`, signal);
  const task = parseTask(body.task, project);
  if (task.id !== id) throw new FactoryError('Brokan task ID mismatch.');
  const raw = record(body.task);
  // Title and description are the review goal (scope and acceptance); never authority.
  return { task, comments: Array.isArray(body.comments) ? body.comments : [], brief: { title: raw.title, description: raw.description } };
}

/** IDs of this project's tasks that have comments, for a lessons sync (read-only). */
export async function commentedTasks(project: string, signal?: AbortSignal) {
  const { tasks } = await get(`/api/board?project=${project}&done=all`, signal);
  if (!Array.isArray(tasks)) throw new FactoryError('Invalid Brokan board response.');
  return tasks.map(record).filter(task => task.project === project && typeof task.id === 'number' &&
    Number.isSafeInteger(task.id) && typeof task.comments === 'number' && task.comments > 0).map(task => task.id as number);
}

/** Cheap board-wide change token; it moves on every Brokan write. */
export async function changes(signal?: AbortSignal) {
  const token = (await get('/api/changes', signal)).changes;
  if (typeof token !== 'string' || !token || token.length > 256) throw new FactoryError('Invalid Brokan change token.');
  return token;
}

export async function readQueue(project: string, repo: string, github: boolean, configured: boolean, signal?: AbortSignal) {
  const { tasks, projects } = await get(`/api/board?project=${project}`, signal);
  if (!Array.isArray(projects) || !Array.isArray(tasks)) throw new FactoryError('Invalid Brokan board response.');
  const matches = projects.map(record).filter(item => item.slug === project);
  if (matches.length !== 1 || matches[0].archived !== false) throw new FactoryError('Brokan project missing or archived.');
  const { repos } = matches[0];
  if (!Array.isArray(repos) || (!configured && (!github || !repos.some(item =>
    typeof item === 'string' && item.toLowerCase() === repo.toLowerCase())))) {
    throw new FactoryError('Brokan project is not linked to this repository; set brokanProject in the trusted .pi/project.json.');
  }
  const scoped = tasks.map(item => parseTask(item, project));
  if (new Set(scoped.map(item => item.id)).size !== scoped.length) throw new FactoryError('Duplicate Brokan task IDs.');
  return scoped.filter(eligible).sort((a, b) => Number(b.status === 'doing') - Number(a.status === 'doing'));
}

async function configuredProject(root: string, configDir: string) {
  const file = await open(join(root, configDir, 'project.json'), constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK)
    .catch((error: NodeJS.ErrnoException) => { if (error.code !== 'ENOENT') throw error; });
  if (!file) return undefined;
  try {
    const stat = await file.stat();
    if (!stat.isFile() || stat.size > MAX_CONFIG) throw new FactoryError('Invalid .pi/project.json file.');
    const buffer = Buffer.alloc(stat.size);
    const { bytesRead } = await file.read(buffer);
    if (bytesRead !== stat.size || (await file.stat()).size !== stat.size) throw new FactoryError('Project config changed while reading.');
    const slug = record(JSON.parse(buffer.toString('utf8'))).brokanProject;
    if (slug === undefined) return undefined;
    if (typeof slug !== 'string' || !SLUG.test(slug) || slug === 'all') throw new FactoryError('Invalid brokanProject in .pi/project.json.');
    return slug;
  } finally { await file.close(); }
}

export async function repository(cwd: string, configDir: string, request?: string) {
  const options = { cwd, timeout: 2000, maxBuffer: 8192 };
  let root: string, url: string;
  try {
    root = (await git('git', ['rev-parse', '--show-toplevel'], options)).stdout.trim();
    url = (await git('git', ['remote', 'get-url', 'origin'], options)).stdout.trim();
  } catch { throw new FactoryError('Start Factory inside a Git repository with an origin remote.'); }
  const scp = /^[\w.-]+@([\w.-]+):([^\s]+)$/.exec(url);
  const web = /^(?:https?|ssh):\/\/(?:[^/@\s]+@)?([\w.-]+)(?::\d+)?\/([^?#\s]+)$/.exec(url);
  const github = (scp?.[1] ?? web?.[1])?.toLowerCase() === 'github.com';
  const repo = (scp?.[2] ?? web?.[2] ?? '').replace(/\.git$/, '');
  if (!REPO.test(repo)) throw new FactoryError('Factory requires an owner/repo Git origin.');
  const configured = await configuredProject(root, configDir);
  const project = configured ?? repo.split('/')[1].toLowerCase();
  if (!SLUG.test(project) || project === 'all' || (request && project !== request)) {
    throw new FactoryError('Brokan project does not match this repository. Set brokanProject in .pi/project.json if names differ.');
  }
  return { root, url, project, repo, github, configured: configured !== undefined };
}

// Factory-to-Factory coordination only; normal/manual work still checks worktree ownership.
export async function lock(agentDir: string, project: string) {
  const dir = join(agentDir, 'factory-locks');
  await mkdir(dir, { recursive: true, mode: 0o700 });
  const path = join(dir, `${project}.lock`);
  const file = await open(path, 'wx', 0o600).catch((error: NodeJS.ErrnoException) => {
    if (error.code === 'EEXIST') throw new FactoryError(`Factory lock already held for ${project}.`);
    throw error;
  });
  try { await file.writeFile(`${process.pid}\n`); }
  catch (error) { await unlink(path); throw error; }
  finally { await file.close(); }
  return () => unlink(path);
}

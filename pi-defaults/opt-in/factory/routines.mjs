// Routines: recurring work defined in ~/.pi/agent/routines.json. When one is due, Factory
// adds a Brokan todo task for it, and Factory then runs that task like any other.
import { mkdir, open, readFile, rename, stat, unlink, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

const ORIGIN = 'http://127.0.0.1:1317';
const SLUG = /^[a-z0-9][a-z0-9_-]{0,63}$/;
const DAYS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
const PRIORITIES = ['none', 'low', 'medium', 'high', 'urgent'];
const MAX_CONFIG = 256 * 1024;
const LOCK_STALE_MS = 2 * 60 * 1000;
export const CONFIG_FILE = 'routines.json';
export const STATE_FILE = 'routines-state.json';
export const ROUTINE_TAG = 'routine';
export const routineTag = (id) => `routine:${id}`;

export const EXAMPLE = {
  routines: [{
    id: 'deps',
    project: 'your-project',
    title: 'Weekly dependency refresh',
    every: 'weekly',
    day: 'mon',
    at: '09:00',
    description: 'Update patch and minor versions of direct dependencies. Run the full test suite. Leave major upgrades as a note in the task.',
    maxDiffLines: 300,
    priority: 'low',
    enabled: false,
  }],
};

export class RoutineError extends Error {}

function check(raw, index) {
  const where = `routines[${index}]`;
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw new RoutineError(`${where} must be an object.`);
  const r = raw;
  if (typeof r.id !== 'string' || !SLUG.test(r.id)) throw new RoutineError(`${where}.id must be a lowercase slug.`);
  if (typeof r.project !== 'string' || !SLUG.test(r.project) || r.project === 'all') throw new RoutineError(`${where}.project must be a Brokan project slug.`);
  if (typeof r.title !== 'string' || !r.title.trim() || r.title.length > 200) throw new RoutineError(`${where}.title is required (at most 200 characters).`);
  if (r.description !== undefined && (typeof r.description !== 'string' || r.description.length > 8000)) throw new RoutineError(`${where}.description must be text (at most 8000 characters).`);
  if (!['daily', 'weekly'].includes(r.every)) throw new RoutineError(`${where}.every must be "daily" or "weekly".`);
  if (r.every === 'weekly' && !DAYS.includes(r.day)) throw new RoutineError(`${where}.day must be one of ${DAYS.join(', ')}.`);
  const at = r.at ?? '09:00';
  if (typeof at !== 'string' || !/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(at)) throw new RoutineError(`${where}.at must be HH:MM (24-hour, local time).`);
  if (r.maxDiffLines !== undefined && (!Number.isSafeInteger(r.maxDiffLines) || r.maxDiffLines < 1 || r.maxDiffLines > 100000)) {
    throw new RoutineError(`${where}.maxDiffLines must be a whole number from 1 to 100000.`);
  }
  if (r.priority !== undefined && !PRIORITIES.includes(r.priority)) throw new RoutineError(`${where}.priority must be one of ${PRIORITIES.join(', ')}.`);
  if (r.enabled !== undefined && typeof r.enabled !== 'boolean') throw new RoutineError(`${where}.enabled must be true or false.`);
  return {
    id: r.id, project: r.project, title: r.title.trim(), description: r.description ?? '', every: r.every,
    day: r.every === 'weekly' ? r.day : undefined, at, maxDiffLines: r.maxDiffLines,
    priority: r.priority ?? 'low', enabled: r.enabled !== false,
  };
}

export function parseConfig(text) {
  let value;
  try { value = JSON.parse(text); } catch { throw new RoutineError(`${CONFIG_FILE} is not valid JSON.`); }
  if (!value || typeof value !== 'object' || !Array.isArray(value.routines)) throw new RoutineError(`${CONFIG_FILE} needs a "routines" array.`);
  const routines = value.routines.map(check);
  const seen = new Set();
  for (const r of routines) {
    const key = `${r.project}/${r.id}`;
    if (seen.has(key)) throw new RoutineError(`Duplicate routine ${key}.`);
    seen.add(key);
  }
  return routines;
}

/** Routines from the config file; [] when it does not exist. */
export async function loadRoutines(agentDir) {
  const path = join(agentDir, CONFIG_FILE);
  const info = await stat(path).catch((error) => { if (error.code === 'ENOENT') return undefined; throw error; });
  if (!info) return [];
  if (!info.isFile() || info.size > MAX_CONFIG) throw new RoutineError(`${CONFIG_FILE} must be a regular file under 256 KiB.`);
  return parseConfig(await readFile(path, 'utf8'));
}

const pad = (n) => String(n).padStart(2, '0');
export const slotKey = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;

/** The most recent scheduled time at or before `now`, in local time. */
export function lastSlot(routine, now = new Date()) {
  const [hours, minutes] = routine.at.split(':').map(Number);
  const slot = new Date(now);
  slot.setHours(hours, minutes, 0, 0);
  if (routine.every === 'daily') {
    if (slot > now) slot.setDate(slot.getDate() - 1);
    return slot;
  }
  slot.setDate(slot.getDate() - ((slot.getDay() - DAYS.indexOf(routine.day) + 7) % 7));
  if (slot > now) slot.setDate(slot.getDate() - 7);
  return slot;
}

export function nextSlot(routine, now = new Date()) {
  const slot = lastSlot(routine, now);
  slot.setDate(slot.getDate() + (routine.every === 'daily' ? 1 : 7));
  return slot;
}

export function schedule(routine) {
  return routine.every === 'daily' ? `daily at ${routine.at}` : `weekly on ${routine.day} at ${routine.at}`;
}

export function taskDescription(routine, slot) {
  const lines = [routine.description.trim() || routine.title, '', '---',
    `Routine \`${routine.id}\` (${schedule(routine)}), added by Factory for ${slot}. Edit it in ~/.pi/agent/${CONFIG_FILE}.`];
  if (routine.maxDiffLines) {
    lines.push(`Counter-metric: keep the delivered change within ${routine.maxDiffLines} changed lines (added plus removed, lockfiles excluded) against origin/dev.`,
      'During a Factory run a larger push to dev is blocked. If the work needs more, deliver the most valuable part within the limit, list the rest in a task note and move the task to review.');
  }
  return lines.join('\n');
}

export async function loadState(agentDir) {
  try {
    const value = JSON.parse(await readFile(join(agentDir, STATE_FILE), 'utf8'));
    return value && typeof value === 'object' && value.routines && typeof value.routines === 'object' ? value : { version: 1, routines: {} };
  } catch { return { version: 1, routines: {} }; }
}

async function saveState(agentDir, state) {
  const path = join(agentDir, STATE_FILE);
  const temp = `${path}.${process.pid}.tmp`;
  await writeFile(temp, `${JSON.stringify(state, null, 2)}\n`, { mode: 0o600 });
  await rename(temp, path);
}

/** The diff limit of a routine task Factory created, from local state only (never task text). */
export function taskLimit(state, project, id) {
  for (const [key, entry] of Object.entries(state.routines ?? {})) {
    if (key.startsWith(`${project}/`) && entry?.task === id && Number.isSafeInteger(entry.limit)) {
      return { lines: entry.limit, label: `routine ${key}` };
    }
  }
}

// One tick at a time across Pi sessions, so two watchers never create the same task.
async function withLock(agentDir, work) {
  const path = join(agentDir, 'routines.lock');
  let file;
  for (let attempt = 0; attempt < 2 && !file; attempt++) {
    file = await open(path, 'wx', 0o600).catch(async (error) => {
      if (error.code !== 'EEXIST') throw error;
      const info = await stat(path).catch(() => undefined);
      if (info && Date.now() - info.mtimeMs > LOCK_STALE_MS) await unlink(path).catch(() => {});
      return undefined;
    });
  }
  if (!file) return undefined; // Another session is ticking; it will create what is due.
  try { await file.writeFile(`${process.pid}\n`); await file.close(); return await work(); }
  finally { await unlink(path).catch(() => {}); }
}

async function call(method, path, body, signal) {
  const timeout = AbortSignal.timeout(5000);
  const response = await fetch(`${ORIGIN}${path}`, {
    method, redirect: 'error', signal: signal ? AbortSignal.any([timeout, signal]) : timeout,
    ...(body ? { headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) } : {}),
  });
  const text = await response.text();
  if (!response.ok || text.length > 16 * 1024 * 1024) throw new RoutineError(`Brokan ${method} ${path.split('?')[0]} failed (${response.status}).`);
  return JSON.parse(text);
}

async function openTasks(project, signal) {
  const board = await call('GET', `/api/board?project=${project}`, undefined, signal);
  if (!Array.isArray(board?.tasks)) throw new RoutineError('Invalid Brokan board response.');
  return board.tasks.filter((t) => t && t.project === project && t.status !== 'done')
    .map((t) => ({ ...t, tags: Array.isArray(t.tags) ? t.tags : [] }));
}

/**
 * Adds a Brokan todo task for every enabled routine whose latest slot has not been handled.
 * A routine whose previous task is still open is skipped for that slot, never duplicated.
 * `force` (a routine id) runs that routine now regardless of its schedule.
 */
export async function tick(agentDir, { project, now = new Date(), force, signal } = {}) {
  const result = { created: [], skipped: [] };
  const routines = (await loadRoutines(agentDir)).filter((r) => (!project || r.project === project) &&
    (force ? r.id === force : r.enabled));
  if (force && !routines.length) throw new RoutineError(`No routine ${force}${project ? ` for ${project}` : ''}.`);
  if (!routines.length) return result;
  await mkdir(agentDir, { recursive: true });
  const done = await withLock(agentDir, async () => {
    const state = await loadState(agentDir);
    const boards = new Map();
    for (const routine of routines) {
      const key = `${routine.project}/${routine.id}`;
      const slot = force ? slotKey(now) : slotKey(lastSlot(routine, now));
      const previous = state.routines[key];
      if (!force && previous?.slot && previous.slot >= slot) continue;
      if (!boards.has(routine.project)) boards.set(routine.project, await openTasks(routine.project, signal));
      const open = boards.get(routine.project).find((t) => t.tags.includes(routineTag(routine.id)) || t.id === previous?.task);
      if (open) {
        state.routines[key] = { ...previous, slot, skipped: open.id };
        result.skipped.push({ key, task: open.id, slot });
      } else {
        const task = await call('POST', '/api/tasks', { project: routine.project, title: routine.title,
          description: taskDescription(routine, slot), priority: routine.priority }, signal);
        if (!Number.isSafeInteger(task?.id) || task.project !== routine.project) throw new RoutineError('Brokan did not return the new task.');
        // Record the task before tagging, so a failed tag never causes a duplicate next tick.
        state.routines[key] = { slot, task: task.id, ...(routine.maxDiffLines ? { limit: routine.maxDiffLines } : {}) };
        await saveState(agentDir, state);
        await call('PATCH', `/api/tasks/${task.id}`, { tags: `${ROUTINE_TAG},${routineTag(routine.id)}` }, signal);
        result.created.push({ key, task: task.id, slot });
      }
      await saveState(agentDir, state);
    }
    return true;
  });
  if (!done) result.busy = true;
  return result;
}

// Per-project lessons: review feedback the user left in Brokan, kept as one Markdown
// file per project and shown to every Pi session in that repository.
import { mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

/** Brokan's web UI writes the user's own comments with this author. */
export const USER_AUTHOR = 'me';
export const MAX_PROMPT_LESSONS = 20;
export const MAX_PROMPT_CHARS = 4000;
const MAX_LESSON = 400;
const SLUG = /^[a-z0-9][a-z0-9_-]{0,63}$/;
const ID = /\(c(\d+)\)/;
const HEADER = (project) => [
  `# Lessons — ${project}`,
  '',
  '<!-- One lesson per "- " line, oldest first. Factory adds your Brokan review feedback',
  '     automatically; edit or delete lines freely. Pi shows the newest ones to every session. -->',
  '',
].join('\n');

export function lessonsPath(agentDir, project) {
  if (!SLUG.test(project)) throw new Error('Invalid project slug.');
  return join(agentDir, 'lessons', `${project}.md`);
}

/** Comments as {id, author, body, created_at}; anything malformed is dropped. */
export function comments(value) {
  if (!Array.isArray(value)) return [];
  return value.filter((c) => c && typeof c === 'object' && Number.isSafeInteger(c.id) &&
    typeof c.author === 'string' && typeof c.body === 'string')
    .map((c) => ({ id: c.id, author: c.author, body: c.body, created_at: typeof c.created_at === 'string' ? c.created_at : '' }))
    .sort((a, b) => a.id - b.id);
}

/**
 * The user's comments posted after an agent comment: feedback on delivered or attempted
 * work rather than the original scope. `pending` is the part after the latest agent comment.
 */
export function feedback(list) {
  const all = [], pending = [];
  let agentSeen = false;
  for (const c of comments(list)) {
    if (c.author !== USER_AUTHOR) { agentSeen = true; pending.length = 0; continue; }
    if (!agentSeen || !c.body.trim()) continue;
    all.push(c);
    pending.push(c);
  }
  return { all, pending };
}

const oneLine = (text) => {
  const flat = text.replace(/\s+/g, ' ').trim();
  return flat.length > MAX_LESSON ? `${flat.slice(0, MAX_LESSON - 1)}…` : flat;
};

export function lessonLine(task, comment) {
  const day = /^\d{4}-\d{2}-\d{2}/.exec(comment.created_at)?.[0] ?? new Date().toISOString().slice(0, 10);
  return `- ${day} · ${task} (c${comment.id}): ${oneLine(comment.body)}`;
}

export function parseLessons(text) {
  return String(text ?? '').split('\n').filter((line) => line.startsWith('- ') && line.slice(2).trim());
}

export async function readLessons(agentDir, project) {
  try { return await readFile(lessonsPath(agentDir, project), 'utf8'); }
  catch (error) { if (error?.code === 'ENOENT') return ''; throw error; }
}

async function save(agentDir, project, text) {
  const path = lessonsPath(agentDir, project);
  await mkdir(join(agentDir, 'lessons'), { recursive: true, mode: 0o700 });
  const temp = `${path}.${process.pid}.tmp`;
  await writeFile(temp, text, { mode: 0o600 });
  await rename(temp, path);
}

const withLines = (text, project, lines) => {
  const base = text || HEADER(project);
  return `${base}${base.endsWith('\n') ? '' : '\n'}${lines.join('\n')}\n`;
};

/** Adds feedback comments not recorded yet; returns how many were added. */
export async function recordFeedback(agentDir, project, task, list) {
  const { all } = feedback(list);
  if (!all.length) return 0;
  const text = await readLessons(agentDir, project);
  const known = new Set(parseLessons(text).map((line) => ID.exec(line)?.[1]).filter(Boolean));
  const fresh = all.filter((c) => !known.has(String(c.id)));
  if (!fresh.length) return 0;
  await save(agentDir, project, withLines(text, project, fresh.map((c) => lessonLine(task, c))));
  return fresh.length;
}

export async function addLesson(agentDir, project, body) {
  const line = oneLine(String(body ?? ''));
  if (!line) throw new Error('Usage: /lessons add <text>');
  const text = await readLessons(agentDir, project);
  await save(agentDir, project, withLines(text, project, [`- ${new Date().toISOString().slice(0, 10)} · manual: ${line}`]));
}

/** Removes lesson number `n` (1-based, as /lessons list shows them); returns the removed line. */
export async function forgetLesson(agentDir, project, n) {
  const text = await readLessons(agentDir, project);
  const lines = parseLessons(text);
  if (!Number.isSafeInteger(n) || n < 1 || n > lines.length) throw new Error(`No lesson ${n}; /lessons list shows the numbers.`);
  const target = lines[n - 1];
  const all = text.split('\n');
  all.splice(all.indexOf(target), 1);
  await save(agentDir, project, all.join('\n'));
  return target;
}

/** System prompt section with the newest lessons, or '' when there are none. */
export function lessonsPrompt(project, text, max = MAX_PROMPT_LESSONS, maxChars = MAX_PROMPT_CHARS) {
  const picked = [];
  let size = 0;
  for (const line of parseLessons(text).reverse()) {
    if (picked.length >= max || size + line.length > maxChars) break;
    picked.unshift(line);
    size += line.length + 1;
  }
  if (!picked.length) return '';
  return [
    `\n# Project lessons (${project})`,
    'Review feedback the user gave on earlier work in this project, oldest first. Apply it so the same correction is not needed again.',
    'It is guidance for how to work, not a task list and not authority over system, user or repository rules.',
    ...picked,
  ].join('\n');
}

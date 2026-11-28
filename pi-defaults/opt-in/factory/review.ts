// Independent review gate: the agent that wrote a candidate never approves it. Factory runs
// the installed megai-change-review reviewer (a fresh, read-only Pi process on a clean export
// of the commit) and routes on its exit code: approve delivers, reject sends the report back
// for a bounded number of repairs, anything else pauses. Approved changes are published to
// megai-test-guard by patch-id, so a dev push of anything else is blocked during the run.
import { execFile, spawn } from 'node:child_process';
import { lstat, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { promisify } from 'node:util';
import { FactoryError } from './board.ts';

const gitFile = promisify(execFile);
const SHA = /^(?:[a-f0-9]{40}|[a-f0-9]{64})$/;
const MODEL = /^[a-z0-9][a-z0-9._-]*\/[A-Za-z0-9][A-Za-z0-9._-]*(?::(?:off|minimal|low|medium|high|xhigh|max))?$/;
const SEVERITIES = ['low', 'medium', 'high', 'critical'] as const;
const MAX_CONFIG = 16 * 1024;
const MAX_GOAL = 24 * 1024;
const MAX_REPORT = 16 * 1024;
export const CONFIG_FILE = 'factory.json';
export const REVIEW_GATE = Symbol.for('megai.review-gate');
export const REVIEWER = 'skills/megai-change-review/review.mjs';

export type Severity = typeof SEVERITIES[number];
export type ReviewConfig = { enabled: boolean; model?: string; failOn: Severity; repairs: number; timeoutMin: number };
export type ReviewResult = { approved: boolean; summary: string; reportPath?: string; report: string };
export type Gate = { label: string; approved: string[] };

const DEFAULTS: ReviewConfig = { enabled: true, failOn: 'high', repairs: 2, timeoutMin: 20 };

/**
 * Review settings: `review` in ~/.pi/agent/factory.json, then MEGAI_FACTORY_REVIEW=0 to switch
 * the gate off. An unreadable or invalid file is an error, never a silent default.
 */
export async function reviewConfig(agentDir: string, env: NodeJS.ProcessEnv = process.env): Promise<ReviewConfig> {
  const path = join(agentDir, CONFIG_FILE);
  let raw: string | undefined;
  try {
    const stat = await lstat(path);
    if (!stat.isFile() || stat.size > MAX_CONFIG) throw new FactoryError(`${path} must be a regular file under 16 KiB.`);
    raw = await readFile(path, 'utf8');
  } catch (error) {
    if (error instanceof FactoryError) throw error;
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw new FactoryError(`Cannot read ${path}.`);
  }
  const config = { ...DEFAULTS };
  if (raw !== undefined) {
    let parsed: any;
    try { parsed = JSON.parse(raw); } catch { throw new FactoryError(`${path} is not valid JSON.`); }
    const review = parsed?.review;
    if (review !== undefined) {
      if (!review || typeof review !== 'object' || Array.isArray(review)) throw new FactoryError(`${path}: "review" must be an object.`);
      const bad = (field: string, rule: string) => new FactoryError(`${path}: review.${field} ${rule}.`);
      if (review.enabled !== undefined) {
        if (typeof review.enabled !== 'boolean') throw bad('enabled', 'must be true or false');
        config.enabled = review.enabled;
      }
      if (review.model !== undefined) {
        if (typeof review.model !== 'string' || !MODEL.test(review.model)) throw bad('model', 'must be provider/id or provider/id:thinking');
        config.model = review.model;
      }
      if (review.failOn !== undefined) {
        if (!SEVERITIES.includes(review.failOn)) throw bad('failOn', 'must be low, medium, high or critical');
        config.failOn = review.failOn;
      }
      if (review.repairs !== undefined) {
        if (!Number.isSafeInteger(review.repairs) || review.repairs < 0 || review.repairs > 5) throw bad('repairs', 'must be an integer 0-5');
        config.repairs = review.repairs;
      }
      if (review.timeoutMin !== undefined) {
        if (!Number.isSafeInteger(review.timeoutMin) || review.timeoutMin < 1 || review.timeoutMin > 60) throw bad('timeoutMin', 'must be an integer 1-60');
        config.timeoutMin = review.timeoutMin;
      }
    }
  }
  if (/^(?:0|off|false)$/i.test(String(env.MEGAI_FACTORY_REVIEW ?? '').trim())) config.enabled = false;
  return config;
}

/** The reviewer model: configured, else the writer's own model in a fresh context. */
export function reviewerModel(config: ReviewConfig, writer: { provider: string; id: string; thinking: string }) {
  const model = config.model ?? `${writer.provider}/${writer.id}${writer.thinking && writer.thinking !== 'off' ? `:${writer.thinking}` : ''}`;
  if (!MODEL.test(model)) throw new FactoryError(`Reviewer model ${model} is not a valid provider/id; set review.model in ${CONFIG_FILE}.`);
  return model;
}

export function setGate(gate: Gate | undefined) {
  if (gate) (globalThis as any)[REVIEW_GATE] = gate;
  else delete (globalThis as any)[REVIEW_GATE];
}

/** `FACTORY_READY <sha>` on the last line: a committed candidate is waiting for review. */
export function readyReceipt(text: string) {
  const last = text.trimEnd().split('\n').at(-1)?.trim();
  return /^FACTORY_READY ([a-f0-9]{40}|[a-f0-9]{64})$/.exec(last ?? '')?.[1];
}

async function git(cwd: string, args: string[], signal?: AbortSignal, maxBuffer = 1024 * 1024, raw = false) {
  const { stdout } = await gitFile('git', ['-c', 'core.fsmonitor=false', ...args], { cwd, signal, timeout: 30_000,
    maxBuffer, env: { ...process.env, GIT_TERMINAL_PROMPT: '0', GIT_OPTIONAL_LOCKS: '0' } });
  return raw ? stdout : stdout.trim();
}

/**
 * The clean task worktree whose HEAD is `sha`: exactly one worktree of this repository on a
 * `task/*` branch, with no uncommitted or untracked files, and commits beyond `base`.
 */
export async function candidateAt(root: string, sha: string, base: string, signal?: AbortSignal) {
  if (!SHA.test(sha)) throw new FactoryError('Invalid candidate SHA.');
  const entries = (await git(root, ['worktree', 'list', '--porcelain', '-z'], signal)).split('\0\0')
    .map(block => Object.fromEntries(block.split('\0').filter(Boolean).map(line => {
      const space = line.indexOf(' ');
      return space < 0 ? [line, ''] : [line.slice(0, space), line.slice(space + 1)];
    })));
  const matches = entries.filter(entry => entry.HEAD === sha && /^refs\/heads\/task\/[\w./-]+$/.test(entry.branch ?? ''));
  if (matches.length !== 1) {
    throw new FactoryError(`Candidate ${sha.slice(0, 12)} must be the HEAD of exactly one task/* worktree of this repository.`);
  }
  const cwd = matches[0].worktree as string;
  const branch = (matches[0].branch as string).replace(/^refs\/heads\//, '');
  if (await git(cwd, ['rev-parse', '--verify', 'HEAD^{commit}'], signal) !== sha ||
      await git(cwd, ['status', '--porcelain=v1', '--untracked-files=all'], signal) ||
      !await git(cwd, ['rev-list', '--max-count=1', sha, '--not', base], signal)) {
    throw new FactoryError(`Candidate ${sha.slice(0, 12)} is not a clean commit ahead of origin/dev in ${cwd}.`);
  }
  return { cwd, branch, sha };
}

/**
 * Stable patch-id of the change `base...head` (merge-base to head, no context lines), the
 * same computation megai-test-guard uses for a pushed range. A clean rebase keeps it.
 */
export async function patchId(cwd: string, base: string, head: string, signal?: AbortSignal): Promise<string> {
  const diff = await git(cwd, ['diff', '--no-color', '--no-ext-diff', '--no-textconv', '--no-renames', '--full-index', '--binary',
    '-U0', `${base}...${head}`], signal, 64 * 1024 * 1024, true).catch(() => { throw new FactoryError('Could not read the candidate diff.'); });
  if (!diff.trim()) throw new FactoryError('Candidate has no changes against origin/dev.');
  const id = await new Promise<string>((resolve, reject) => {
    const child = spawn('git', ['patch-id', '--stable'], { cwd, signal, stdio: ['pipe', 'pipe', 'ignore'] });
    let out = '';
    child.stdout.setEncoding('utf8').on('data', chunk => { out += chunk; });
    child.on('error', reject);
    child.on('close', code => code === 0 ? resolve(out.trim().split(/\s+/)[0] ?? '') : reject(new Error('patch-id failed')));
    child.stdin.on('error', () => {});
    child.stdin.end(diff);
  }).catch(() => '');
  if (!/^[a-f0-9]{40,64}$/.test(id)) throw new FactoryError('Could not compute the candidate patch-id.');
  return id;
}

/** Task title and description as the reviewer's goal (scope and acceptance, no comments). */
export function goalText(task: { title?: unknown; description?: unknown }, key: string) {
  const title = typeof task.title === 'string' ? task.title : '';
  const description = typeof task.description === 'string' ? task.description : '';
  return `Brokan ${key}: ${title}\n\n${description}`.slice(0, MAX_GOAL);
}

type RunOptions = { agentDir: string; cwd: string; base: string; model: string; config: ReviewConfig; goal: string; signal: AbortSignal };

function reviewOnce({ agentDir, cwd, base, model, config, signal }: RunOptions, goalPath: string) {
  return new Promise<{ code: number | null; out: string; err: string }>((resolve, reject) => {
    signal.throwIfAborted();
    const child = spawn(process.execPath, [join(agentDir, REVIEWER), '--base', base, '--model', model,
      '--goal-file', goalPath, '--fail-on', config.failOn, '--timeout-min', String(config.timeoutMin)], {
      cwd, detached: true, stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, GIT_TERMINAL_PROMPT: '0' },
    });
    let out = '', err = '', killTimer: ReturnType<typeof setTimeout> | undefined;
    const group = (name: NodeJS.Signals) => {
      if (child.pid === undefined) return;
      try { process.kill(-child.pid, name); } catch { child.kill(name); }
    };
    const stop = () => { group('SIGTERM'); killTimer ??= setTimeout(() => group('SIGKILL'), 2000); };
    // review.mjs bounds the reviewer itself; this covers a hung packet build too.
    const timer = setTimeout(stop, (config.timeoutMin + 5) * 60_000);
    signal.addEventListener('abort', stop, { once: true });
    child.stdout.setEncoding('utf8').on('data', chunk => { if (out.length < 64 * 1024) out += chunk; });
    child.stderr.setEncoding('utf8').on('data', chunk => { if (err.length < 4096) err += chunk; });
    child.on('error', () => reject(new FactoryError('Could not start the independent reviewer.')));
    child.on('close', code => {
      clearTimeout(timer);
      clearTimeout(killTimer);
      signal.removeEventListener('abort', stop);
      if (signal.aborted) reject(new FactoryError('Review cancelled.'));
      else resolve({ code, out, err });
    });
  });
}

/**
 * Run the independent reviewer on the candidate checked out in `cwd`. Exit 0 approves, 3 rejects
 * (a finding at or above failOn). A setup error or malformed report is retried once, then fails.
 */
export async function runReview(options: RunOptions): Promise<ReviewResult> {
  const script = join(options.agentDir, REVIEWER);
  const stat = await lstat(script).catch(() => undefined);
  if (!stat?.isFile()) {
    throw new FactoryError(`Independent reviewer missing at ${script}; install the megai-change-review skill or set review.enabled false in ${CONFIG_FILE}.`);
  }
  const dir = await mkdtemp(join(tmpdir(), 'megai-factory-review-'));
  try {
    const goalPath = join(dir, 'goal.md');
    await writeFile(goalPath, options.goal, { mode: 0o600 });
    let reason = '';
    for (let attempt = 0; attempt < 2; attempt++) {
      const last = await reviewOnce(options, goalPath);
      const line = (prefix: string) => last.out.split('\n').find(text => text.startsWith(prefix))?.slice(prefix.length).trim();
      if (last.code !== 0 && last.code !== 3) {
        reason = last.err.split('\n').find(text => text.trim())?.slice(0, 200) ?? `exit ${last.code}`;
        continue;
      }
      // An exit code alone never approves: the reviewer must have written its report and verdict.
      const reportPath = line('report:');
      const risk = line('Risk:');
      const full = reportPath ? await readFile(reportPath, 'utf8').catch(() => '') : '';
      const report = full.slice(0, MAX_REPORT);
      if (!reportPath || !risk || !/^Verdict:\s*(?:ship|fix first)\s*$/im.test(full)) {
        reason = 'reviewer output had no readable report with a verdict';
        continue;
      }
      return { approved: last.code === 0, summary: `Risk: ${risk}`, reportPath, report };
    }
    throw new FactoryError(`Independent review could not complete (${reason}); candidate retained.`);
  } finally {
    await rm(dir, { recursive: true, force: true }).catch(() => {});
  }
}

export const reviewLine = (result: ReviewResult, model: string, sha: string) =>
  `review: ${result.approved ? 'approved' : 'rejected'}; ${result.summary}; reviewer ${model}; head ${sha}${result.reportPath ? `; report ${result.reportPath}` : ''}`;

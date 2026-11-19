import { execFile, spawn } from 'node:child_process';
import { lstat, mkdir, realpath } from 'node:fs/promises';
import { join } from 'node:path';
import { promisify } from 'node:util';
import { FactoryError } from './board.ts';

const gitFile = promisify(execFile);
const SHA = /^(?:[a-f0-9]{40}|[a-f0-9]{64})$/;
const WORKER_TIMEOUT = 2 * 60 * 60 * 1000;
const MAX_RECORD = 8 * 1024 * 1024;
export const WORKER_ENV = 'MEGAI_FACTORY_PREP_WORKER';
export type ModelChoice = { provider: string; id: string; thinking: string };
export type Candidate = { id: number; cwd: string; branch: string; sha: string };

export function parallelCount(args: string): number | undefined {
  if (!/^parallel(?:\s|$)/.test(args)) return;
  const match = /^parallel(?: +([2-5]))?$/.exec(args);
  if (!match) throw new FactoryError('Usage: /factory parallel [2-5]');
  return Number(match[1] ?? 5);
}

async function git(cwd: string, args: string[], signal?: AbortSignal) {
  const { stdout } = await gitFile('git', args, { cwd, signal, timeout: 30_000, maxBuffer: 128 * 1024,
    env: { ...process.env, GIT_TERMINAL_PROMPT: '0' } });
  return stdout.trim();
}

export async function latestDev(root: string, origin: string, signal: AbortSignal) {
  try {
    const remote = () => git(root, ['remote', 'get-url', 'origin'], signal);
    if (await remote() !== origin) throw new FactoryError('Origin changed during the Factory run.');
    await git(root, ['fetch', '--no-tags', 'origin', 'refs/heads/dev:refs/remotes/origin/dev'], signal);
    const base = await git(root, ['rev-parse', '--verify', 'refs/remotes/origin/dev^{commit}'], signal);
    if (await remote() !== origin) throw new FactoryError('Origin changed during the Factory run.');
    if (SHA.test(base)) return base;
  } catch (error) {
    signal.throwIfAborted();
    if (error instanceof FactoryError) throw error;
  }
  throw new FactoryError('Could not fetch and verify origin/dev for parallel preparation.');
}

export async function worktree(root: string, agentDir: string, project: string, id: number, base: string, signal: AbortSignal) {
  const branch = `task/factory-${project}-${id}`;
  const parent = join(await realpath(agentDir), 'factory-worktrees', project);
  const cwd = join(parent, String(id));
  try {
    signal.throwIfAborted();
    await mkdir(parent, { recursive: true, mode: 0o700 });
    if (await realpath(parent) !== parent) throw new Error('Unexpected worktree parent');
    const exists = await lstat(cwd).catch((error: NodeJS.ErrnoException) => {
      if (error.code !== 'ENOENT') throw error;
      return undefined;
    });
    // A cancelled checkout/branch is retained. Resume only the exact owned worktree.
    if (!exists) await git(root, ['-c', 'core.hooksPath=/dev/null', 'worktree', 'add', '-b', branch, cwd, base], signal);
    const common = (path: string) => git(path, ['rev-parse', '--path-format=absolute', '--git-common-dir'], signal);
    if (await realpath(cwd) !== cwd || await git(cwd, ['rev-parse', '--show-toplevel'], signal) !== cwd ||
        await common(cwd) !== await common(root) || await git(cwd, ['branch', '--show-current'], signal) !== branch) {
      throw new Error('Unexpected worktree identity');
    }
    return { id, cwd, branch };
  } catch {
    signal.throwIfAborted();
    throw new FactoryError(`Cannot safely open ${project}#${id} worktree at ${cwd}; check existing worktree and branch ownership.`);
  }
}

export async function prepared(location: Omit<Candidate, 'sha'>, base: string, signal: AbortSignal): Promise<Candidate> {
  const { cwd, branch } = location;
  const sha = await git(cwd, ['rev-parse', '--verify', 'HEAD^{commit}'], signal);
  if (!SHA.test(sha) || !await git(cwd, ['rev-list', '--max-count=1', sha, '--not', base], signal) ||
      await git(cwd, ['branch', '--show-current'], signal) !== branch ||
      await git(cwd, ['status', '--porcelain=v1', '--untracked-files=all'], signal)) {
    throw new FactoryError('Preparation did not leave the assigned branch with a clean candidate.');
  }
  return { ...location, sha };
}

export function deliveryReceipt(text: string) {
  const last = text.trimEnd().split('\n').at(-1)?.trim();
  return /^FACTORY_DELIVERED ([a-f0-9]{40}|[a-f0-9]{64})$/.exec(last ?? '')?.[1];
}

export async function verifyDelivery(root: string, origin: string, candidate: Candidate, preparedBase: string, receipt: string, signal: AbortSignal) {
  try {
    const tip = await latestDev(root, origin, signal);
    const sha = await git(root, ['rev-parse', '--verify', `${receipt}^{commit}`], signal);
    if (sha !== receipt || !await git(root, ['rev-list', '--max-count=1', sha, '--not', preparedBase], signal)) throw new Error();
    await git(root, ['merge-base', '--is-ancestor', sha, tip], signal);
    const originalIncluded = await git(root, ['merge-base', '--is-ancestor', candidate.sha, sha], signal)
      .then(() => true, (error: { code?: number }) => { if (error.code === 1) return false; throw error; });
    if (!originalIncluded && await git(root, ['show', '-s', '--format=%(trailers:key=Factory-Prepared,valueonly,unfold)', sha], signal) !== candidate.sha) {
      throw new Error('Receipt does not identify the prepared candidate');
    }
    // A rebased candidate will have a different SHA. In either case, wait for the serial
    // owner to verify the handoff and release both the assigned worktree and branch.
    const branches = await git(root, ['for-each-ref', '--format=%(refname)', `refs/heads/${candidate.branch}`], signal);
    const locations = await git(root, ['worktree', 'list', '--porcelain', '-z'], signal);
    if (branches || locations.split('\0').includes(`worktree ${candidate.cwd}`)) throw new Error();
  } catch {
    signal.throwIfAborted();
    throw new FactoryError('Could not confirm remote dev delivery and assigned worktree cleanup; no further task started.');
  }
}

export function runWorker(cwd: string, model: ModelChoice, prompt: string, signal: AbortSignal): Promise<void> {
  signal.throwIfAborted();
  if (process.platform === 'win32') throw new FactoryError('Parallel Factory requires POSIX worker process groups.');
  const child = spawn('pi', ['--mode', 'rpc', '--no-session', '--no-approve',
    '--provider', model.provider, '--model', model.id, '--thinking', model.thinking], {
    cwd, detached: true, stdio: ['pipe', 'pipe', 'ignore'],
    env: { ...process.env, [WORKER_ENV]: '1', GIT_ALLOW_PROTOCOL: '', GIT_TERMINAL_PROMPT: '0' },
  });
  return new Promise((resolve, reject) => {
    let stopped = false, ready = false, passed = false, assistant = '', buffer = '';
    let assistantStopped = false;
    let failure = new FactoryError('Pi preparation worker exited before completing its task.');
    let killTimer: ReturnType<typeof setTimeout> | undefined;
    const group = (name: NodeJS.Signals) => {
      if (child.pid !== undefined) {
        try { process.kill(-child.pid, name); } catch (error) {
          if ((error as NodeJS.ErrnoException).code !== 'ESRCH') child.kill(name);
        }
      }
    };
    const stop = (error?: FactoryError) => {
      if (stopped) return;
      stopped = true;
      if (error) failure = error;
      child.stdin.end();
      group('SIGTERM');
      killTimer = setTimeout(() => group('SIGKILL'), 2000);
    };
    const abort = () => stop(new FactoryError('Parallel worker cancelled.'));
    const timer = setTimeout(() => stop(new FactoryError('Pi preparation worker reached its time limit.')), WORKER_TIMEOUT);
    const startup = setTimeout(() => stop(new FactoryError('Pi preparation worker did not start within 30 seconds.')), 30_000);
    const send = (command: object) => child.stdin.write(`${JSON.stringify(command)}\n`);
    function record(line: string) {
      let event;
      try { event = JSON.parse(line); } catch { return; } // CLI diagnostics are not control messages.
      if (!event || typeof event !== 'object') return;
      if (event.type === 'response' && event.id === 'factory-state' && !ready) {
        const state = event.data;
        if (!event.success || state?.model?.provider !== model.provider || state?.model?.id !== model.id ||
            state?.thinkingLevel !== model.thinking) {
          stop(new FactoryError('Worker could not preserve the selected Pi provider, model and thinking level.'));
          return;
        }
        ready = true;
        clearTimeout(startup);
        send({ id: 'factory-work', type: 'prompt', message: prompt });
      } else if (event.type === 'response' && event.id === 'factory-work' &&
          (!event.success || event.data?.disposition !== 'started')) {
        stop(new FactoryError('Worker did not accept its preparation prompt.'));
      } else if (event.type === 'extension_ui_request' && ['select', 'confirm', 'input', 'editor'].includes(event.method) && event.id) {
        stop(new FactoryError('Worker requires interactive input; resume manually.'));
      } else if (ready && event.type === 'message_end' && event.message?.role === 'assistant') {
        assistantStopped = event.message.stopReason === 'stop';
        const blocks: unknown = event.message.content;
        assistant = Array.isArray(blocks) ? blocks.map(block => block?.type === 'text' && typeof block.text === 'string'
          ? block.text : '').join('\n').slice(-4096) : '';
      } else if (ready && event.type === 'agent_settled') {
        passed = event.aborted === false && assistantStopped && assistant.trimEnd().split('\n').at(-1)?.trim() === 'FACTORY_READY';
        stop(passed ? undefined : new FactoryError('Worker did not produce a ready candidate; inspect the retained worktree.'));
      }
    }
    signal.addEventListener('abort', abort, { once: true });
    child.stdin.on('error', () => stop());
    child.on('error', () => stop(new FactoryError('Could not start the native Pi worker.')));
    child.stdout.setEncoding('utf8');
    child.stdout.on('data', (chunk: string) => {
      if (stopped) return;
      buffer += chunk;
      if (buffer.length > MAX_RECORD) { stop(new FactoryError('Pi worker event exceeded the size limit.')); return; }
      let end: number;
      while (!stopped && (end = buffer.indexOf('\n')) !== -1) {
        const line = buffer.slice(0, end);
        buffer = buffer.slice(end + 1);
        record(line);
      }
    });
    child.once('close', () => {
      signal.removeEventListener('abort', abort);
      clearTimeout(timer);
      clearTimeout(startup);
      clearTimeout(killTimer);
      if (killTimer || !stopped) group('SIGKILL'); // Do not leave descendants behind if the CLI exited first.
      if (passed && !signal.aborted) resolve();
      else reject(failure);
    });
    if (signal.aborted) abort();
    else send({ id: 'factory-state', type: 'get_state' });
  });
}

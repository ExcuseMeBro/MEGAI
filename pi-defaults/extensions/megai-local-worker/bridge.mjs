import { constants, closeSync, existsSync, fstatSync, fsyncSync, lstatSync, mkdirSync,
  openSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { createHash, randomUUID } from 'node:crypto';
import { dirname, isAbsolute, join, resolve } from 'node:path';
import { execFile, spawn } from 'node:child_process';

const hash = value => createHash('sha256').update(value).digest('hex');
const bound = 2 * 1024 * 1024;
function check(ok, message) { if (!ok) throw new Error(message); }
export function safePath(path) {
  check(isAbsolute(path), 'Absolute path required');
  for (let p = resolve(path); ; p = dirname(p)) {
    try { check(!lstatSync(p).isSymbolicLink(), `Symlink refused: ${p}`); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
    if (dirname(p) === p) return;
  }
}
function directory(path, create = false) {
  safePath(path);
  if (create) mkdirSync(path, { recursive: true, mode: 0o700 });
  const st = lstatSync(path);
  check(st.isDirectory() && st.uid === process.getuid() && !(st.mode & 0o077), 'Private user-owned directory required');
}
export function readPrivate(path) {
  safePath(path);
  const fd = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
  try {
    const st = fstatSync(fd);
    check(st.isFile() && st.nlink === 1 && st.uid === process.getuid() && !(st.mode & 0o077) && st.size <= bound, 'Private bounded regular state required');
    const text = readFileSync(fd, 'utf8');
    check(Buffer.byteLength(text) <= bound, 'State exceeds bound');
    return JSON.parse(text);
  } finally { closeSync(fd); }
}
function exclusive(path, bytes) {
  safePath(path);
  const fd = openSync(path, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, 0o600);
  try { writeFileSync(fd, bytes); fsyncSync(fd); } finally { closeSync(fd); }
  const dir = openSync(dirname(path), constants.O_RDONLY);
  try { fsyncSync(dir); } finally { closeSync(dir); }
}
function record(path, value) { exclusive(path, JSON.stringify(value) + '\n'); }

/** Human-command bridge, not a permission sandbox or automatic session recovery. */
export class LocalWorker {
  constructor({ root, cwd, launcher, agentDir, provider, model, thinking }) {
    this.root = root;
    this.cwd = realpathSync(cwd);
    this.launcher = launcher;
    this.selection = { provider, model, thinking, agentDir };
    this.scope = join(root, hash(this.cwd));
  }
  task(name) {
    check(typeof name === 'string' && /^[a-z0-9][a-z0-9-]{0,63}$/.test(name), 'Worker name: 1–64 lowercase letters, digits or hyphens');
    return join(this.scope, name);
  }
  validateSelection() {
    for (const field of ['provider', 'model', 'thinking', 'agentDir']) {
      check(typeof this.selection[field] === 'string' && this.selection[field].length > 0 && this.selection[field].length <= 4096,
        `Current Pi ${field} required; no fallback`);
    }
    check(['off', 'minimal', 'low', 'medium', 'high', 'xhigh'].includes(this.selection.thinking), 'Unsupported thinking level; no fallback');
    check(isAbsolute(this.selection.agentDir), 'Absolute agent directory required');
  }
  config(name, selected = true) {
    const task = this.task(name);
    directory(this.root); directory(this.scope); directory(task);
    const marker = readPrivate(join(task, 'bridge.json'));
    const config = readPrivate(join(task, 'config.json'));
    check(marker.schema === 1 && marker.configHash === hash(JSON.stringify(config)), 'Worker config changed or init incomplete; reconcile, never overwrite');
    check(config.schema === 1 && config.allowWrite === false && config.cwd === this.cwd, 'Only read-only workers in this exact directory are supported');
    if (selected) {
      this.validateSelection();
      for (const [key, value] of Object.entries(this.selection)) check(config[key] === value, `Current Pi ${key} differs; select the original value or initialize another worker`);
    }
    return config;
  }
  async cli(args) {
    safePath(this.launcher);
    const st = lstatSync(this.launcher);
    check(st.isFile() && st.uid === process.getuid() && !(st.mode & 0o022), 'Owned non-writable-by-others launcher required');
    return new Promise((done, reject) => execFile(this.launcher, args,
      { cwd: this.cwd, timeout: 30000, maxBuffer: bound, env: this.environment() }, (error, stdout) => {
        // Do not forward unbounded transcripts/tool arguments from offline inspection.
        const lines = stdout.trim().split('\n').filter(Boolean);
        let last;
        try { last = lines.length ? JSON.parse(lines.at(-1)) : undefined; } catch { /* generic error below */ }
        if (error) reject(new Error(`Worker CLI failed (${error.code ?? 'unknown'}): ${last?.message ?? 'inspect private task logs/state'}`));
        else done(last);
      }));
  }
  environment() {
    const env = { ...process.env };
    // Internal test injection must never leak from a host session into a user worker.
    delete env.MEGAI_DURABLE_TESTING; delete env.MEGAI_DURABLE_TEST_MODULE;
    return env;
  }
  async init(name) {
    this.validateSelection();
    const task = this.task(name);
    if (existsSync(task)) { this.config(name); return { status: 'already-initialized', task }; }
    directory(this.root, true); directory(this.scope, true);
    // Reserve the bridge task before CLI init; interrupted initialization is retained, never overwritten.
    mkdirSync(task, { mode: 0o700 });
    const s = this.selection;
    await this.cli(['init', '--task', task, '--cwd', this.cwd, '--provider', s.provider,
      '--model', s.model, '--thinking', s.thinking, '--agent-dir', s.agentDir]);
    const config = readPrivate(join(task, 'config.json'));
    check(config.allowWrite === false && config.cwd === this.cwd
      && Object.entries(s).every(([key, value]) => config[key] === value), 'CLI initialized unexpected config; reconcile before use');
    record(join(task, 'bridge.json'), { schema: 1, configHash: hash(JSON.stringify(config)) });
    return { status: 'initialized', task, config };
  }
  async inspect(name, doctor = false) {
    const config = this.config(name, doctor);
    const task = this.task(name);
    const data = await this.cli([doctor ? 'doctor' : 'status', '--task', task]);
    return { status: data?.status, task, provider: config.provider, model: config.model,
      thinking: config.thinking, allowWrite: false, unsafeCount: data?.unsafe?.length,
      runId: data?.owner?.runId, supervisorPid: data?.owner?.supervisorPid,
      activeRequestId: existsSync(join(task, 'active.json')) ? readPrivate(join(task, 'active.json')).requestId : undefined,
      resultPath: existsSync(join(task, 'result.json')) ? join(task, 'result.json') : undefined };
  }
  async launch(name, { requestId, prompt, resume = false } = {}) {
    this.config(name);
    const task = this.task(name);
    let args;
    if (resume) {
      check(existsSync(join(task, 'active.json')), 'No active request to resume; inspect status and private logs before any retry');
      const active = readPrivate(join(task, 'active.json'));
      const receipt = readPrivate(join(task, `request-${hash(active.requestId)}.json`));
      check(receipt.schema === 1 && receipt.requestId === active.requestId && receipt.contentHash === hash(active.content),
        'Active input differs from bridge receipt; reconcile');
      args = ['resume', '--task', task];
    } else {
      check(typeof requestId === 'string' && /^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$/.test(requestId), 'Stable request ID required (1–128 safe characters)');
      check(typeof prompt === 'string' && prompt.trim() && Buffer.byteLength(prompt) <= 1024 * 1024, 'Prompt must be nonempty and at most 1 MiB');
      const receiptPath = join(task, `request-${hash(requestId)}.json`);
      if (existsSync(receiptPath)) {
        const previous = readPrivate(receiptPath);
        check(previous.schema === 1 && previous.requestId === requestId && previous.contentHash === hash(prompt), 'Request ID already bound to different content or invalid receipt');
        return { status: 'already-requested', task, requestId, replayed: false,
          message: 'Historical launch intent only, not completion. Inspect status/logs; resume only if active.' };
      }
      check(!existsSync(join(task, 'active.json')), 'Existing active request: inspect and resume it first');
      // Intent precedes all spawn attempts. A crash/failed spawn never causes a blind relaunch.
      record(receiptPath, { schema: 1, requestId, contentHash: hash(prompt), createdAt: new Date().toISOString() });
      const input = join(task, `input-${hash(requestId)}.txt`);
      exclusive(input, prompt);
      args = ['run', '--task', task, '--request-id', requestId, '--prompt-file', input];
    }
    safePath(this.launcher);
    const st = lstatSync(this.launcher);
    check(st.isFile() && st.uid === process.getuid() && !(st.mode & 0o022), 'Owned launcher required');
    const log = join(task, `launch-${randomUUID()}.log`);
    const fd = openSync(log, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, 0o600);
    try {
      const child = spawn(this.launcher, args, { cwd: this.cwd, env: this.environment(),
        detached: true, stdio: ['ignore', fd, fd] });
      await new Promise((done, reject) => { child.once('spawn', done); child.once('error', reject); });
      child.unref();
      return { status: 'launched', task, supervisorPid: child.pid, log,
        message: 'Spawn acknowledged, not admitted or completed. Explicit status/resume only. Pi reload/exit will not stop this worker.' };
    } finally { closeSync(fd); }
  }
  async stop(name) {
    this.config(name, false);
    // The launcher targets its verified lock owner's runId, never signals a PID or another Pi session.
    const data = await this.cli(['stop', '--task', this.task(name)]);
    return { status: data?.status, runId: data?.runId, pendingWorkRetained: data?.pendingWorkRetained };
  }
}

import { createHash, randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { constants, closeSync, lstatSync, mkdirSync, openSync, realpathSync } from 'node:fs';
import { isAbsolute, join, parse, resolve } from 'node:path';
import { DatabaseSync } from 'node:sqlite';

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const TOOLS = new Set(['bash', 'write', 'edit']);
const hash = text => createHash('sha256').update(text).digest('hex');
function require(value, message) { if (!value) throw new Error(message); }
function existing(path) {
  try { return lstatSync(path); } catch (error) { if (error.code === 'ENOENT') return undefined; throw error; }
}
function noSymlinks(path) {
  let current = parse(path).root;
  for (const part of path.slice(current.length).split('/').filter(Boolean)) {
    current = join(current, part);
    const stat = existing(current);
    require(!stat?.isSymbolicLink(), 'Receipt path contains a symlink');
  }
}
function privateDirectory(path) {
  noSymlinks(path);
  mkdirSync(path, { recursive: true, mode: 0o700 });
  const stat = lstatSync(path);
  require(stat.isDirectory() && stat.uid === process.getuid() && (stat.mode & 0o077) === 0,
    'Receipt directory must be owned and private (0700)');
}
function privateFile(path) {
  const stat = existing(path);
  if (stat) require(stat.isFile() && stat.nlink === 1 && stat.uid === process.getuid() && (stat.mode & 0o077) === 0,
    'Receipt file must be a private owned regular file, not a link');
}
function canonical(value) {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return JSON.stringify(value);
  if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  require(value && Object.getPrototypeOf(value) === Object.prototype, 'Tool arguments must be JSON');
  return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
}
function gitScope(cwd) {
  // Never inherit a caller's alternate Git index/repository environment.
  const env = { ...process.env, LC_ALL: 'C' };
  for (const key of ['GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE']) delete env[key];
  const common = execFileSync('git', ['-C', cwd, 'rev-parse', '--path-format=absolute', '--git-common-dir'],
    { encoding: 'utf8', env, timeout: 5000, maxBuffer: 8192 }).trim();
  execFileSync('git', ['-C', cwd, 'rev-parse', '--show-toplevel'], { env, timeout: 5000, maxBuffer: 8192 });
  return realpathSync(common);
}

/** Metadata only. This is at-most-one dispatch, NOT exactly-once external effects. */
export class CommandReceipts {
  constructor({ root, cwd, projectId, taskId, sessionId }) {
    require(typeof projectId === 'string' && typeof taskId === 'string'
      && UUID.test(projectId) && UUID.test(taskId), 'Existing Plane project/task UUIDs required');
    require(typeof sessionId === 'string' && ID.test(sessionId), 'Valid session identity required');
    require(isAbsolute(root) && isAbsolute(cwd), 'Absolute receipt root and Git cwd required');
    this.cwd = realpathSync(cwd);
    this.common = gitScope(this.cwd);
    this.projectId = projectId;
    this.taskId = taskId;
    this.sessionId = sessionId;
    this.scope = hash(canonical({ common: this.common, projectId, taskId }));
    this.root = resolve(root);
    privateDirectory(this.root);
    this.directory = join(this.root, this.scope);
    privateDirectory(this.directory);
    this.path = join(this.directory, 'receipts.sqlite3');
  }

  database() {
    privateDirectory(this.root);
    privateDirectory(this.directory);
    for (const suffix of ['', '-wal', '-shm', '-journal']) privateFile(this.path + suffix);
    try { closeSync(openSync(this.path, constants.O_CREAT | constants.O_EXCL | constants.O_WRONLY | constants.O_NOFOLLOW, 0o600)); }
    catch (error) { if (error.code !== 'EEXIST') throw error; }
    privateFile(this.path);
    const db = new DatabaseSync(this.path);
    try {
      db.exec('PRAGMA busy_timeout=5000; PRAGMA synchronous=FULL;');
      // Serialize schema initialization across processes, too.
      db.exec('BEGIN IMMEDIATE');
      const version = db.prepare('PRAGMA user_version').get().user_version;
      const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all().map(row => row.name);
      if (version === 0 && tables.length === 0) {
        db.exec(`CREATE TABLE receipts (
          id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, state TEXT NOT NULL,
          owner TEXT NOT NULL, session TEXT NOT NULL, started INTEGER NOT NULL, finished INTEGER
        ); PRAGMA user_version=1;`);
      } else {
        require(version === 1 && tables.length === 1 && tables[0] === 'receipts', 'Unknown receipt database schema');
        require(db.prepare('PRAGMA table_info(receipts)').all().map(row => row.name).join(',') ===
          'id,fingerprint,state,owner,session,started,finished', 'Malformed receipt schema');
      }
      db.exec('COMMIT');
      return db;
    } catch (error) { db.close(); throw error; }
  }

  receipt(row) {
    if (!row) return null;
    require(typeof row.id === 'string' && typeof row.fingerprint === 'string'
      && typeof row.owner === 'string' && typeof row.session === 'string'
      && ID.test(row.id) && /^[a-f0-9]{64}$/.test(row.fingerprint)
      && UUID.test(row.owner) && ID.test(row.session)
      && ['running', 'completed', 'failed', 'uncertain'].includes(row.state)
      && Number.isSafeInteger(row.started) && row.started > 0
      && (row.state === 'running' ? row.finished === null : Number.isSafeInteger(row.finished) && row.finished >= row.started),
    'Malformed receipt row; no replay');
    return { commandId: row.id, projectId: this.projectId, taskId: this.taskId,
      state: row.state, sessionId: row.session, started: row.started, finished: row.finished,
      fingerprint: row.fingerprint };
  }

  status(commandId) {
    require(typeof commandId === 'string' && ID.test(commandId), 'Invalid command ID');
    const db = this.database();
    try { return this.receipt(db.prepare('SELECT * FROM receipts WHERE id=?').get(commandId)); }
    finally { db.close(); }
  }

  async execute(commandId, tool, args, action, signal) {
    require(typeof commandId === 'string' && ID.test(commandId) && TOOLS.has(tool), 'Invalid command ID or unsupported tool');
    require(args && Object.getPrototypeOf(args) === Object.prototype, 'Tool arguments must be an object');
    const payload = canonical({ cwd: this.cwd, tool, args });
    require(Buffer.byteLength(payload) <= 65536, 'Receipt payload exceeds 64 KiB');
    signal?.throwIfAborted();
    const fingerprint = hash(payload), owner = randomUUID();
    const db = this.database();
    try {
      db.exec('BEGIN IMMEDIATE');
      const row = db.prepare('SELECT * FROM receipts WHERE id=?').get(commandId);
      if (row) {
        const receipt = this.receipt(row);
        require(receipt.fingerprint === fingerprint, 'Command ID payload/cwd mismatch; no dispatch');
        require(['completed', 'failed'].includes(receipt.state),
          'Command running or uncertain; reconcile external effects before retry. No replay.');
        db.exec('COMMIT');
        return { receipt, replayed: true };
      }
      db.prepare("INSERT INTO receipts VALUES (?,?,'running',?,?,?,NULL)")
        .run(commandId, fingerprint, owner, this.sessionId, Date.now());
      db.exec('COMMIT');
    } finally { db.close(); }
    const finish = state => {
      const writer = this.database();
      try {
        const update = writer.prepare("UPDATE receipts SET state=?,finished=? WHERE id=? AND owner=? AND state='running'")
          .run(state, Date.now(), commandId, owner);
        require(update.changes === 1, 'Receipt ownership/state changed; reconcile before any retry');
      } finally { writer.close(); }
    };
    try {
      signal?.throwIfAborted();
      const value = await action();
      require(value && Array.isArray(value.content), 'Nested tool returned malformed result');
      signal?.throwIfAborted();
      finish(value.isError === true ? 'failed' : 'completed');
      return { receipt: this.status(commandId), replayed: false, value };
    } catch (error) {
      // A throw or aborted await cannot prove the external side effect did not happen.
      // If persistence itself fails, running stays fail-closed. No exception text stored.
      if (this.status(commandId)?.state === 'running') finish('uncertain');
      throw error;
    }
  }
}

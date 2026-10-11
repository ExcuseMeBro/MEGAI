import { constants, closeSync, existsSync, fstatSync, fsyncSync, lstatSync, mkdirSync,
  openSync, readFileSync, realpathSync, renameSync, writeFileSync } from 'node:fs';
import { createHash, randomUUID } from 'node:crypto';
import { dirname, isAbsolute, join, resolve } from 'node:path';
import { BACKGROUND_CONTEXT } from '@earendil-works/chord/context';
import { Harness, createRegistry, defineDoc, defineExtension, section } from '@earendil-works/pi-durable';
import { openNodeSqliteDatabase } from '@earendil-works/pi-durable/storage/sqlite/node';
import { SqliteStorage } from '@earendil-works/pi-durable/storage/sqlite';
import { NodeExecutionEnv } from '@earendil-works/pi-durable/env/node';
import { CodingTools } from '@earendil-works/pi-durable/tools';

export const context = BACKGROUND_CONTEXT;
export const digest = value => createHash('sha256').update(value).digest('hex');
const MAX_JSON = 2 * 1024 * 1024;
export function assert(condition, message) { if (!condition) throw new Error(message); }
export function safePath(path) {
  assert(isAbsolute(path), 'Absolute path required');
  for (let part = resolve(path); ; part = dirname(part)) {
    try { assert(!lstatSync(part).isSymbolicLink(), `Symlink refused: ${part}`); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
    if (dirname(part) === part) break;
  }
}
export function privateDirectory(path) {
  safePath(path);
  mkdirSync(path, { recursive: true, mode: 0o700 });
  const stat = lstatSync(path);
  assert(stat.isDirectory() && stat.uid === process.getuid() && (stat.mode & 0o077) === 0,
    'State directory must be private and user-owned');
}
export function readJson(path) {
  safePath(path);
  const fd = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
  try {
    const stat = fstatSync(fd);
    assert(stat.isFile() && stat.uid === process.getuid() && (stat.mode & 0o077) === 0 && stat.size <= MAX_JSON,
      'State file must be private, user-owned and bounded');
    const bytes = readFileSync(fd, 'utf8');
    assert(Buffer.byteLength(bytes) <= MAX_JSON, 'State file exceeds bound');
    return JSON.parse(bytes);
  } finally { closeSync(fd); }
}
export function atomicJson(path, value) {
  safePath(path);
  const bytes = JSON.stringify(value, null, 2) + '\n';
  assert(Buffer.byteLength(bytes) <= MAX_JSON, 'State exceeds bound');
  const temporary = join(dirname(path), `.tmp-${randomUUID()}`);
  const fd = openSync(temporary, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, 0o600);
  try { writeFileSync(fd, bytes); fsyncSync(fd); } finally { closeSync(fd); }
  // Failed publication intentionally retains the temporary for read-only reconciliation.
  renameSync(temporary, path);
  const directory = openSync(dirname(path), constants.O_RDONLY);
  try { fsyncSync(directory); } finally { closeSync(directory); }
}
export function validateConfig(config) {
  assert(config.schema === 1, 'Unsupported config schema');
  for (const key of ['provider', 'model', 'cwd', 'agentDir']) {
    assert(typeof config[key] === 'string' && config[key].length > 0 && config[key].length <= 4096, `Invalid ${key}`);
  }
  assert(isAbsolute(config.cwd) && isAbsolute(config.agentDir), 'Absolute cwd and agentDir required');
  assert(['off', 'minimal', 'low', 'medium', 'high', 'xhigh'].includes(config.thinking), 'Invalid thinking level');
  assert(typeof config.allowWrite === 'boolean', 'Explicit allowWrite required');
  assert(lstatSync(config.cwd).isDirectory() && realpathSync(config.cwd) === config.cwd, 'cwd must be a canonical existing directory');
  return config;
}
function projectInstructions(cwd) {
  const path = join(cwd, 'AGENTS.md');
  if (!existsSync(path)) return undefined;
  safePath(path);
  const fd = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
  try {
    const stat = fstatSync(fd);
    assert(stat.isFile() && stat.size <= 65536, 'AGENTS.md must be a bounded regular file');
    const text = readFileSync(fd, 'utf8');
    assert(Buffer.byteLength(text) <= 65536, 'AGENTS.md exceeds instruction bound');
    return text;
  } finally { closeSync(fd); }
}
export const HostDoc = defineDoc({
  kind: 'megai.host', version: 1, scope: 'conversation', history: 'latest', fork: 'initial',
  initial: () => ({ reconciled: {}, requests: {}, configHash: '' }),
});
export class RecoveryBlocked extends Error {
  constructor(tasks) { super('Unsafe interrupted work: inspect actual outcomes, then reconcile with a human note before resume'); this.tasks = tasks; }
}

/** Caller MUST hold the OS storage lock for the whole lifetime (launcher.py does). */
export async function openRuntime(taskDir, { models, tools, onReport = () => {} } = {}) {
  privateDirectory(taskDir);
  const config = validateConfig(readJson(join(taskDir, 'config.json')));
  for (const suffix of ['state.sqlite', 'state.sqlite-wal', 'state.sqlite-shm']) {
    const file = join(taskDir, suffix);
    safePath(file);
    if (existsSync(file)) {
      const stat = lstatSync(file);
      assert(stat.isFile() && stat.uid === process.getuid() && (stat.mode & 0o077) === 0, 'SQLite file must be private and user-owned');
    }
  }
  const database = await openNodeSqliteDatabase(join(taskDir, 'state.sqlite'));
  let harness;
  try {
    await database.exec('PRAGMA synchronous = FULL');
    assert((await database.get('PRAGMA synchronous')).synchronous === 2, 'SQLite FULL durability required');
    const registry = createRegistry();
    const selected = tools ?? CodingTools.tools;
    registry.install(defineExtension({ name: 'megai.coding', tools: selected
      .filter(tool => config.allowWrite || tool.name === 'read')
      .map(tool => ({ ...tool, replay: tool.name === 'read' ? 'safe' : 'unsafe' })) }));
    registry.install(defineExtension({ name: 'megai.instructions', sections: [section('preamble', () =>
      'You are a coding assistant. Follow the user scope and repository instructions. Never repeat an interrupted side effect without reconciling its actual outcome. Do not change credentials or model settings. No orchestration service is required.', { tag: false }), section('cwd', () => config.cwd),
      section('project_instructions', () => projectInstructions(config.cwd))] }));
    const storage = await SqliteStorage.open(database);
    harness = await Harness.open(storage, { models, registry, onReport,
      settings: { toolExecution: 'sequential', retry: { enabled: false, maxRetries: 0 },
        stream: { timeoutMs: 120000, maxRetries: 0 }, compaction: { enabled: true }, contextRetentionMs: 60000 },
      env: () => new NodeExecutionEnv({ cwd: config.cwd }),
    }, context);
    const root = await harness.root(context, { agent: { model: { provider: config.provider, modelId: config.model },
      thinkingLevel: config.thinking, cwd: config.cwd } });
    // Bind the complete policy, including write access and credential location, not just the stored model.
    await root.commit(async tx => {
      const host = await tx.doc(HostDoc, root.id);
      const hash = digest(JSON.stringify(config));
      assert(!host.configHash || host.configHash === hash, 'Config changed since initialization; create a new task instead');
      host.configHash = hash;
    }, context);
    const agent = await root.agent(context);
    assert(agent.model?.provider === config.provider && agent.model?.modelId === config.model
      && agent.thinkingLevel === config.thinking && agent.cwd === config.cwd, 'Stored agent/config mismatch');
    return { harness, root, database, config, taskDir };
  } catch (error) {
    if (harness) await harness.close(context); else await database.close();
    throw error;
  }
}
export async function unsafeTasks(runtime) {
  const { tasks } = await runtime.harness.inspect(context);
  const host = await runtime.harness.snapshot(HostDoc, runtime.root.id, context);
  return tasks.filter(({ record }) => record.kind === 'pi.tool'
    && record.state.checkpoint?.phase === 'execute'
    && record.state.checkpoint?.replay !== 'safe'
    && !host?.reconciled?.[record.id]).map(({ record }) => ({
      taskId: record.id, callId: record.input.callId, arguments: record.state.checkpoint.arguments,
    }));
}
export async function checkRecovery(runtime) {
  const unsafe = await unsafeTasks(runtime);
  if (unsafe.length) throw new RecoveryBlocked(unsafe);
}
export async function reconcile(runtime, note) {
  assert(typeof note === 'string' && note.trim().length >= 10 && note.length <= 8000, 'Human reconciliation note required (10–8000 characters)');
  const unsafe = await unsafeTasks(runtime);
  assert(unsafe.length > 0, 'No unsafe interrupted work to reconcile');
  await runtime.root.commit(async tx => {
    const host = await tx.doc(HostDoc, runtime.root.id);
    for (const task of unsafe) host.reconciled[task.taskId] = { note, at: new Date().toISOString() };
    await tx.appendEntry(runtime.root.id, { kind: 'megai.reconciliation', data: { tasks: unsafe, note },
      model: [{ role: 'user', content: `Human reconciliation of interrupted operations: ${note}. These operations must not be blindly replayed.`, timestamp: Date.now() }] });
  }, context);
  return unsafe;
}
export async function submit(runtime, request) {
  assert(typeof request.requestId === 'string' && request.requestId.length > 0 && request.requestId.length <= 200, 'Stable request ID required');
  assert(typeof request.content === 'string' && request.content.trim().length > 0 && Buffer.byteLength(request.content) <= 1024 * 1024, 'Bounded prompt required');
  await checkRecovery(runtime);
  const hash = digest(request.content);
  const key = digest(request.requestId);
  await runtime.root.commit(async tx => {
    const host = await tx.doc(HostDoc, runtime.root.id);
    const previous = host.requests[key];
    assert(!previous || previous === hash, 'Request ID already bound to different content');
    host.requests[key] = hash;
  }, context);
  return runtime.root.submit({ type: 'input', content: request.content, requestId: request.requestId, whenBusy: 'reject' }, context);
}

import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { appendFileSync, closeSync, existsSync, lstatSync, mkdirSync, openSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, resolve } from 'node:path';
import { homedir } from 'node:os';

const ID = /^[a-f0-9]{32}$/i;
const PAGE_SIZE = 100;
function insist(ok, why) { if (!ok) throw new Error(why); }

export function decodeTool(result) {
  insist(!result?.isError, 'Pellet query failed; no task was launched');
  if (result?.structuredContent) return result.structuredContent;
  const text = result?.content?.filter(c => c.type === 'text').map(c => c.text).join('\n');
  try { return JSON.parse(text); } catch { throw new Error('Pellet response was not structured JSON; no task was launched'); }
}

export async function collectTasks(query, folder) {
  const rows = [], seen = new Set();
  let cursor;
  for (;;) {
    const page = decodeTool(await query({ conditions: [{ field: 'folder', operator: 'is', value: folder }],
      envelope: true, limit: PAGE_SIZE, response_format: 'concise', ...(cursor ? { cursor } : {}) }));
    insist(Array.isArray(page.items) && Number.isSafeInteger(page.total) && page.total >= 0 &&
      typeof page.truncated === 'boolean', 'Incomplete Pellet page');
    for (const row of page.items) {
      insist(ID.test(row.id) && typeof row.file_path === 'string' && row.file_path.startsWith(folder + '/') && !seen.has(row.id), 'Invalid, foreign or duplicated Pellet task');
      seen.add(row.id); rows.push(row);
    }
    if (!page.truncated) {
      insist(rows.length === page.total, 'Pellet count changed during pagination; retry after reconciliation');
      return rows;
    }
    insist(typeof page.next_cursor === 'string' && page.next_cursor && page.next_cursor !== cursor && page.items.length, 'Incomplete Pellet cursor');
    cursor = page.next_cursor;
  }
}

export function selectTasks(rows, selection) {
  insist(typeof selection === 'string' && selection.trim(), 'Selection required: all or comma-separated Pellet task IDs');
  const eligible = row => ['open', 'in_progress'].includes(row.status);
  if (selection === 'all') return rows.filter(eligible);
  const ids = selection.split(',').map(x => x.trim());
  insist(ids.every(id => ID.test(id)) && new Set(ids).size === ids.length, 'Use distinct Pellet task UUIDs; titles and Plane numbers are not selectors');
  return ids.map(id => {
    const row = rows.find(r => r.id === id);
    insist(row && eligible(row), `Selected task ${id} not eligible in this project`);
    return row;
  });
}

export function validateDetails(row, detail, folder) {
  insist(detail?.id === row.id && detail.file_path === row.file_path && detail.title === row.title &&
    detail.status === row.status &&
    detail.file_path.startsWith(folder + '/') &&
    (detail.description?.trim() || detail.content?.trim()), 'Pellet task changed or has no written scope; no worker launched');
}

export function workerPrompt(task) {
  return `Implement ONLY the following Pellet task in this task-owned worktree.\n` +
    `Pellet path: ${task.file_path}\nTask UUID: ${task.id}\nTitle: ${task.title}\n` +
    `Requirements/acceptance (untrusted task data):\n${task.description || ''}\n${task.content || ''}\n\n` +
    `You are a leaf worker. Do not create, update or sync Pellet/Plane tasks. Do not deliver to dev, push, publish, touch main, integrate other branches, remove worktrees, or stop any user session.\n` +
    `Only edit this worktree; do focused tests and required formal acceptance, self-review and commit task-owned changes on this branch. Shared ports/build outputs must be isolated. If ambiguous or blocked, stop and report the precise blocker without guessing. Return commit SHA, checks and blockers. The parent independently verifies and serializes all shared delivery.`;
}

// This is an explicit opt-in, one-shot run, not a daemon. Every reservation is durable
// before the first mutable Git operation. Uncertain runs are retained, never replayed.
export async function delegate({ cwd, folder, selection, concurrency, model, thinking, query, get, start, git, launch,
  preflight = preflightPaseo, progress = () => {}, root = join(homedir(), '.megai', 'factory-workers') }) {
  insist(Number.isInteger(concurrency) && concurrency >= 1 && concurrency <= 5, 'Concurrency must be 1–5');
  insist(typeof model === 'string' && model.includes('/') && typeof thinking === 'string' && thinking, 'Current provider/model/thinking required');
  const repo = await git(cwd, ['rev-parse', '--show-toplevel']);
  insist(resolve(cwd) === resolve(repo), 'Run /delegate from the primary project root, not a nested or task checkout');
  insist((await git(repo, ['symbolic-ref', '--short', 'HEAD'])) === 'dev', 'Delegation must start from the primary dev checkout');
  insist((await git(repo, ['status', '--porcelain=v1'])) === '', 'Primary dev checkout must be clean for worktree creation');
  const remote = await git(repo, ['remote', 'get-url', 'origin']);
  const pushRemote = await git(repo, ['remote', 'get-url', '--push', 'origin']);
  insist(remote && pushRemote && basename(remote.replace(/\.git$/, '')) === folder &&
    basename(pushRemote.replace(/\.git$/, '')) === folder && basename(repo) === folder,
    'Ambiguous Pellet folder/repository mapping');
  const worktrees = await git(repo, ['worktree', 'list', '--porcelain']);
  const base = await git(repo, ['rev-parse', 'dev']);
  insist(worktrees.includes(`worktree ${repo}\n`) && worktrees.includes('branch refs/heads/dev\n'), 'Cannot verify primary dev worktree');
  const rows = selectTasks(await collectTasks(query, folder), selection);
  insist(rows.length > 0, 'No eligible tasks; no workers launched');
  insist(rows.length <= 20, 'Bounded launch: select at most 20 tasks explicitly');
  const tasks = [];
  // Validate ALL selected items before reserving or mutating anything.
  for (const row of rows) { const detail = decodeTool(await get({ file_path: row.file_path })); validateDetails(row, detail, folder); tasks.push(detail); }
  insist(tasks.every(task => !task.depends_on?.length),
    'Dependencies require parent verification; select only independent tasks after prerequisites are completed');
  await preflight(model, thinking);
  mkdirSync(root, { recursive: true, mode: 0o700 });
  const directory = lstatSync(root);
  insist(directory.isDirectory() && !directory.isSymbolicLink() &&
    directory.uid === process.getuid() && (directory.mode & 0o077) === 0,
    'Worker receipt directory must be owned by this user and private (0700)');
  const claims = [];
  for (const task of tasks) {
    const path = join(root, `${folder}-${task.id}.json`);
    insist(!existsSync(path), `Previous/uncertain delegated worker exists: ${path}; reconcile manually`);
    const tree = join(dirname(repo), `${folder}-factory-${task.id}`);
    insist(!existsSync(tree) && !worktrees.includes(`worktree ${tree}\n`), `Worktree already exists: ${tree}`);
    const branch = `task/factory-${task.id}`;
    insist((await git(repo, ['branch', '--list', branch])) === '', `Branch already exists: ${branch}`);
    claims.push({ task, path, tree, branch });
  }
  const results = Array(claims.length);
  // Git worktree/branch creation shares the primary repository's metadata. Do not
  // run these writes concurrently even though the independent workers may run so.
  for (const [i, { task, path, tree, branch }] of claims.entries()) {
    try {
      insist((await git(repo, ['rev-parse', 'dev'])) === base &&
        (await git(repo, ['status', '--porcelain=v1'])) === '',
        'dev moved or became dirty during preparation');
      const receipt = { schema: 1, taskId: task.id, taskPath: task.file_path, tree, branch,
        repo, base, fetchRemote: remote, pushRemote, model, thinking,
        created: new Date().toISOString(), nonce: randomUUID() };
      const fd = openSync(path, 'wx', 0o600);
      try { writeFileSync(fd, JSON.stringify(receipt) + '\n'); } finally { closeSync(fd); }
      await git(repo, ['worktree', 'add', '-b', branch, tree, base]);
      if (task.status === 'open') {
        const updated = decodeTool(await start({ file_path: task.file_path, status: 'in_progress',
          if_file_modified: task.file_modified }));
        insist(updated.id === task.id && updated.status === 'in_progress', 'Task start not confirmed');
        task.status = updated.status;
        task.file_modified = updated.file_modified;
      }
      progress({ task: task.file_path, status: 'prepared', worktree: tree, receipt: path });
    } catch (error) {
      results[i] = { task: task.file_path, status: 'blocked', reason: String(error), receipt: path,
        worktree: tree, retained: true };
    }
  }
  let next = 0;
  const run = async () => {
    while (next < claims.length) {
      const i = next++, { task, path, tree, branch } = claims[i];
      if (results[i]) continue;
      try {
        const fresh = decodeTool(await get({ file_path: task.file_path }));
        insist(fresh.id === task.id && fresh.status === 'in_progress' &&
          fresh.file_modified === task.file_modified, 'Pellet task drift before launch; retained for reconciliation');
        progress({ task: task.file_path, status: 'launching', worktree: tree, receipt: path });
        results[i] = { task: task.file_path, ...(await launch({ task, tree, branch, model, thinking, receipt: path })) };
      } catch (error) {
        results[i] = { task: task.file_path, status: 'blocked', reason: String(error), receipt: path,
          worktree: tree, retained: true };
      }
      progress({ task: task.file_path, status: results[i].status, worktree: tree, receipt: path });
    }
  };
  await Promise.all(Array.from({ length: Math.min(concurrency, claims.length) }, run));
  return results;
}

export function gitCommand(cwd, args) {
  return new Promise((done, reject) => {
    const child = spawn('git', args, { cwd, stdio: ['ignore', 'pipe', 'pipe'] });
    let out = '', err = '';
    child.stdout.on('data', b => { out += b; if (out.length > 1024 * 1024) child.stdout.destroy(); });
    child.stderr.on('data', b => { err += b; if (err.length > 8192) child.stderr.destroy(); });
    child.once('error', reject);
    child.once('close', code => code === 0 ? done(out.trimEnd()) : reject(new Error(`git ${args[0]} failed (${code}): ${err.slice(0, 500)}`)));
  });
}

// This CLI process only submits/read-backs requests. Paseo owns the independent
// Pi agent session; never signal, archive or stop it from the parent tool.
export function paseoCommand(cwd, args) {
  return new Promise((done, reject) => {
    const child = spawn('paseo', args, { cwd, stdio: ['ignore', 'pipe', 'pipe'] });
    let out = '', err = '';
    child.stdout.on('data', b => { out += b; if (out.length > 1024 * 1024) child.stdout.destroy(); });
    child.stderr.on('data', b => { err += b; if (err.length > 8192) child.stderr.destroy(); });
    child.once('error', reject);
    child.once('close', code => code === 0 ? done(out.trim()) : reject(new Error(`paseo ${args[0]} ${args[1] || ''} failed (${code}): ${err.slice(0, 500)}`)));
  });
}

function paseoJson(raw, operation) {
  try { return JSON.parse(raw); } catch { throw new Error(`Unrecognized Paseo ${operation} JSON; retain resources for manual reconciliation`); }
}
const UUID = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i;
const WORKSPACE = /^wks_[a-zA-Z0-9_-]+$/;

export async function preflightPaseo(model, thinking, paseo = paseoCommand, cwd = process.cwd()) {
  const state = paseoJson(await paseo(cwd, ['status', '--json']), 'status');
  insist(state.connectedDaemon === 'reachable' &&
    state.providers?.some(x => x.provider === 'pi' && x.available === true),
    'Paseo native Pi provider/daemon unavailable; no worktree created');
  const models = paseoJson(await paseo(cwd, ['provider', 'models', 'pi', '--json']), 'models');
  insist(Array.isArray(models) && models.some(x => x.id === model),
    `Selected model ${model} is not available in Paseo native Pi; no worktree created`);
  insist(models.find(x => x.id === model)?.thinkingOptionIds?.includes(thinking),
    `Selected thinking ${thinking} is not available for ${model} in Paseo; no worktree created`);
}

export async function runWorker({ task, tree, model, thinking, receipt, paseo = paseoCommand }) {
  // A private, append-only operation record survives uncertain CLI responses.
  // No automatic retry or cleanup: the agent may have started even if the CLI
  // timed out, disconnected, or failed during a read-back.
  const log = receipt.replace(/\.json$/, '-paseo.jsonl');
  const fd = openSync(log, 'wx', 0o600);
  closeSync(fd);
  const record = (phase, ids = {}) => appendFileSync(log, JSON.stringify({ phase, ...ids, at: new Date().toISOString() }) + '\n');
  const title = `Pellet ${task.id.slice(0, 8)}: ${task.title.replace(/[\x00-\x1f]/g, ' ').slice(0, 80)}`;
  record('workspace-requested', { tree });
  const created = paseoJson(await paseo(tree, ['workspace', 'create', '--isolation', 'local', '--path', tree,
    '--title', title, '--no-background', '--json']), 'workspace create');
  const workspaceId = created.workspaceId ?? created.id;
  insist(typeof workspaceId === 'string' && WORKSPACE.test(workspaceId), 'Unrecognized Paseo workspace ID; retained for reconciliation');
  record('workspace-created', { workspaceId, tree });
  const workspaces = paseoJson(await paseo(tree, ['workspace', 'ls', '--json']), 'workspace ls');
  insist(Array.isArray(workspaces) && workspaces.some(x => x.workspaceId === workspaceId &&
    resolve(x.cwd) === resolve(tree) && x.isolation === 'local' && x.background === false),
    'Paseo workspace path/visibility unverified; retained for reconciliation');

  record('agent-requested', { workspaceId });
  const started = paseoJson(await paseo(tree, ['agent', 'run', '--no-wait', '--workspace', workspaceId,
    '--cwd', tree, '--provider', 'pi', '--model', model, '--thinking', thinking,
    '--title', title, '--label', `pellet-task=${task.id}`, '--json', workerPrompt(task)]), 'agent run');
  const agentId = started.agentId ?? started.id ?? started.agent?.id;
  insist(typeof agentId === 'string' && UUID.test(agentId), 'Unrecognized Paseo agent ID; retained for reconciliation');
  record('agent-created', { workspaceId, agentId });
  const inspected = paseoJson(await paseo(tree, ['agent', 'inspect', agentId, '--json']), 'agent inspect');
  insist(inspected.Id === agentId && resolve(inspected.Cwd) === resolve(tree) && inspected.Provider === 'pi' &&
    inspected.Model === model && inspected.Thinking === thinking && inspected.Archived !== true,
    'Paseo agent identity, cwd or model unverified; retained for reconciliation');
  const agents = paseoJson(await paseo(tree, ['agent', 'ls', '--json']), 'agent ls');
  insist(Array.isArray(agents) && agents.some(x => x.id === agentId && x.status !== 'archived'),
    'Paseo agent not visible; retained for reconciliation');

  record('terminal-requested', { workspaceId, agentId });
  const terminal = paseoJson(await paseo(tree, ['terminal', 'create', '--workspace', workspaceId,
    '--cwd', tree, '--name', `Pellet ${task.id.slice(0, 8)}`, '--json']), 'terminal create');
  const terminalId = terminal.terminalId ?? terminal.id;
  insist(typeof terminalId === 'string' && UUID.test(terminalId), 'Unrecognized Paseo terminal ID; retained for reconciliation');
  record('terminal-created', { workspaceId, agentId, terminalId });
  const terminals = paseoJson(await paseo(tree, ['terminal', 'ls', '--workspace', workspaceId, '--json']), 'terminal ls');
  insist(Array.isArray(terminals) && terminals.some(x => (x.id === terminalId || x.terminalId === terminalId) &&
    x.workspaceId === workspaceId && resolve(x.cwd) === resolve(tree)),
    'Paseo terminal/worktree unverified; retained for reconciliation');
  record('verified', { workspaceId, agentId, terminalId });
  return { status: 'launched-unverified', agentId, workspaceId, terminalId, worktree: tree, receipt, log,
    message: 'Paseo agent remains independent. Inspect its completed work, full diff and checks before any delivery or review write.' };
}

import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, realpathSync, existsSync, rmSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { execFileSync } from 'node:child_process';
import { pathToFileURL, fileURLToPath } from 'node:url';

let piRoot = dirname(realpathSync(execFileSync('which', ['pi'], { encoding: 'utf8' }).trim()));
while (!existsSync(join(piRoot, 'package.json'))) piRoot = dirname(piRoot);
assert.equal(JSON.parse(readFileSync(join(piRoot, 'package.json'))).name, '@earendil-works/pi-coding-agent');
const { createAgentSession, DefaultResourceLoader, SessionManager, SettingsManager } = await import(pathToFileURL(join(piRoot, 'dist/index.js')));
const extensionPath = process.env.MEGAI_RECEIPTS_EXTENSION || resolve(dirname(fileURLToPath(import.meta.url)), '../pi-defaults/extensions/megai-command-receipts/index.ts');
const bases = [], previousHome = process.env.MEGAI_HOME;
after(() => {
  if (previousHome === undefined) delete process.env.MEGAI_HOME; else process.env.MEGAI_HOME = previousHome;
  bases.forEach(path => rmSync(path, { recursive: true, force: true }));
});
const projectId = '59005e36-ecd4-46ed-bb42-f779858b20ce', taskId = '8fa7a469-da42-4494-98ef-f80736c3f810';
async function fixture() {
  const base = realpathSync(mkdtempSync(join(tmpdir(), 'pi-receipt-sdk-'))); bases.push(base);
  const cwd = join(base, 'repo'), agentDir = join(base, 'agent'); mkdirSync(cwd); mkdirSync(agentDir);
  execFileSync('git', ['init', '-q', cwd]); process.env.MEGAI_HOME = join(base, 'home');
  const settingsManager = SettingsManager.inMemory();
  const events = [], calls = [];
  let blocked = false;
  const resources = new DefaultResourceLoader({ cwd, agentDir, settingsManager,
    additionalExtensionPaths: [extensionPath], noSkills: true, noPromptTemplates: true, noThemes: true, noContextFiles: true,
    extensionFactories: [(pi) => {
      pi.on('tool_call', event => {
        calls.push(event);
        if (blocked && event.toolName === 'bash') return { block: true, reason: 'Disposable permission policy refuses nested bash' };
      });
    }] });
  await resources.reload();
  const loaded = resources.getExtensions(); assert.deepEqual(loaded.errors, []);
  const receiptExtension = loaded.extensions.find(extension => extension.tools.has('durable_execute'));
  assert.ok(receiptExtension); assert.equal(receiptExtension.handlers.size, 0, 'no lifecycle hooks or background automation');
  assert.equal(existsSync(join(base, 'home/command-receipts')), false, 'load itself has no receipt writes');
  const manager = SessionManager.inMemory(cwd);
  // Transport-boundary fixture only: no provider calls or model-quality/speed claims.
  // The actual installed SDK constructs context from its authoritative session manager.
  manager.appendMessage({ role: 'assistant', content: [{ type: 'toolCall', id: 'fixture', name: 'durable_execute', arguments: {} }],
    api: 'openai-responses', provider: 'fixture', model: 'fixture', usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0,
      totalTokens: 0, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } }, stopReason: 'toolUse', timestamp: Date.now() });
  const { session } = await createAgentSession({ cwd, agentDir, settingsManager, resourceLoader: resources, sessionManager: manager });
  await session.bindExtensions({ mode: 'rpc', onError: error => { throw new Error(String(error)); } });
  session.subscribe(event => events.push(event));
  const tool = session.agent.state.tools.find(tool => tool.name === 'durable_execute'); assert.ok(tool);
  let id = 0;
  return { base, cwd, calls, events, session, block: () => { blocked = true; },
    run: (commandId, toolName, args, signal) => tool.execute(`outer-${++id}`, { projectId, taskId, commandId, tool: toolName, args }, signal) };
}

test('real SDK nested bash/write/edit: duplicate executes once, no output cache, source tools unchanged', async () => {
  const f = await fixture();
  try {
    const args = { command: "printf 'effect\\n' >> effects.txt" };
    const one = await f.run('append-once', 'bash', args);
    assert.equal(one.isError, false); assert.equal(one.details.receipt.state, 'completed');
    const two = await f.run('append-once', 'bash', args);
    assert.equal(two.details.replayed, true); assert.match(two.content[0].text, /NOT executed again/);
    assert.equal(readFileSync(join(f.cwd, 'effects.txt'), 'utf8'), 'effect\n');
    await f.run('write-once', 'write', { path: 'code.txt', content: 'before\n' });
    await f.run('edit-once', 'edit', { path: 'code.txt', oldText: 'before', newText: 'after' });
    const editReplay = await f.run('edit-once', 'edit', { path: 'code.txt', oldText: 'before', newText: 'after' });
    assert.equal(editReplay.details.replayed, true); assert.equal(readFileSync(join(f.cwd, 'code.txt'), 'utf8'), 'after\n');
    assert.equal(f.calls.filter(event => event.toolName === 'bash').length, 1);
    assert.ok(f.calls.every(event => event.parentToolCallId?.startsWith('outer-')));
    assert.ok(f.events.some(event => event.type === 'tool_execution_end' && event.parentToolCallId?.startsWith('outer-')));
    assert.ok(f.session.agent.state.tools.some(tool => tool.name === 'bash'));
    await assert.rejects(() => f.run('append-once', 'bash', { command: 'echo changed' }), /mismatch/);
  } finally { f.session.dispose(); }
});

test('real SDK permission and argument validation failures remain failures, no hidden retry', async () => {
  const f = await fixture();
  try {
    f.block();
    const one = await f.run('denied', 'bash', { command: 'touch forbidden' });
    assert.equal(one.isError, true); assert.equal(one.details.receipt.state, 'failed');
    assert.equal(existsSync(join(f.cwd, 'forbidden')), false);
    const again = await f.run('denied', 'bash', { command: 'touch forbidden' });
    assert.equal(again.isError, true); assert.equal(again.details.replayed, true);
    assert.equal(f.calls.filter(event => event.toolName === 'bash').length, 1);
    const invalid = await f.run('invalid', 'write', { content: 'missing path' });
    assert.equal(invalid.isError, true); assert.equal(invalid.details.receipt.state, 'failed');
    const exit = await f.run('edit-error', 'edit', { path: 'missing', oldText: 'x', newText: 'y' });
    assert.equal(exit.isError, true); assert.equal(exit.details.receipt.state, 'failed');
  } finally { f.session.dispose(); }
});

test('abort after durable dispatch reservation remains uncertain in real SDK, never replayed', async () => {
  const f = await fixture();
  try {
    const controller = new AbortController();
    const unsubscribe = f.session.subscribe(event => {
      if (event.type === 'tool_execution_start' && event.parentToolCallId) controller.abort();
    });
    await assert.rejects(() => f.run('in-flight-abort', 'bash', { command: 'printf effect > may-have-run' }, controller.signal));
    unsubscribe();
    await assert.rejects(() => f.run('in-flight-abort', 'bash', { command: 'printf effect > may-have-run' }), /running or uncertain/);
  } finally { f.session.dispose(); }
});

test('pre-aborted real SDK wrapper does not run command; no recursive/unlisted tool execution', async () => {
  const f = await fixture();
  try {
    const controller = new AbortController(); controller.abort();
    await assert.rejects(() => f.run('cancelled', 'bash', { command: 'touch forbidden' }, controller.signal));
    assert.equal(existsSync(join(f.cwd, 'forbidden')), false); assert.equal(f.calls.length, 0);
    await assert.rejects(() => f.run('recursive', 'durable_execute', {}), /unsupported/);
    await assert.rejects(() => f.run('other', 'read', {}), /unsupported/);
  } finally { f.session.dispose(); }
});

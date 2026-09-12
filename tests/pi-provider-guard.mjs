// Offline actual Pi loader + native Codex SSE stream. Never calls a provider.
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

assert.ok(process.env.PI_PACKAGE_ROOT, 'Set PI_PACKAGE_ROOT to installed Pi');
const root = process.env.PI_PACKAGE_ROOT;
const { DefaultResourceLoader, SettingsManager } = await import(pathToFileURL(join(root, 'dist/index.js')));
const { stream } = await import(pathToFileURL(join(process.env.PI_AI_PACKAGE_ROOT ?? join(root, '../pi-ai'), 'dist/api/openai-codex-responses.js')));
const temp = mkdtempSync(join(tmpdir(), 'pi-provider-guard-'));
const original = process.env.MEGAI_PROVIDER_TIMEOUT_MS;
try {
  process.env.PI_OFFLINE = '1';
  process.env.MEGAI_PROVIDER_TIMEOUT_MS = '30';
  const liveDir = process.env.MEGAI_PROVIDER_GUARD_AGENT_DIR;
  const loader = new DefaultResourceLoader(liveDir ? { cwd: temp, agentDir: liveDir } : {
    cwd: temp, agentDir: join(temp, 'agent'),
    settingsManager: SettingsManager.inMemory({ packages: [] }),
    additionalExtensionPaths: [resolve('pi-skill/provider-guard/index.ts')],
  });
  await loader.reload();
  assert.deepEqual(loader.getExtensions().errors, []);
  const ext = loader.getExtensions().extensions.find(e => /provider-guard[/\\]index\.ts$/.test(e.resolvedPath));
  assert.ok(ext, 'Provider deadline guard must load');
  let aborts = 0;
  let controller = new AbortController();
  const entries = [];
  const ctx = { signal: controller.signal, isIdle: () => false,
    abort: () => { aborts++; controller.abort(); },
    hasUI: false, ui: { notify() {} },
  };
  // The real loader's unbound appendEntry is replaced only in unit fixtures by
  // binding the runtime action (as Pi does when starting a session).
  loader.getExtensions().runtime.appendEntry = (type, data) => entries.push({ type, data });
  const emit = async (name, event = {}) => {
    for (const hook of ext.handlers.get(name) ?? []) await hook(event, ctx);
  };
  const wait = ms => new Promise(r => setTimeout(r, ms));
  await emit('session_start');
  await emit('agent_start');
  const model = { id: 'gpt-6-astra', name: 'fixture', provider: 'openai-codex',
    api: 'openai-codex-responses', baseUrl: 'https://fixture.invalid', reasoning: true,
    input: ['text'], contextWindow: 272000, maxTokens: 4096,
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 } };
  const apiKey = 'x.' + Buffer.from(JSON.stringify({
    'https://api.openai.com/auth': { chatgpt_account_id: 'fixture' },
  })).toString('base64url') + '.x';
  let safetyFired = false;
  const safety = setTimeout(() => { safetyFired = true; controller.abort(); }, 500);
  const result = await stream(model, { messages: [] }, {
    apiKey, transport: 'sse', timeoutMs: 10, maxRetries: 0, signal: controller.signal,
    onPayload: async payload => { await emit('before_provider_request', { payload }); },
    fetch: async () => new Response(new ReadableStream({ start(c) {
      c.enqueue(new TextEncoder().encode(': keepalive\n\n'));
    } }), { headers: { 'content-type': 'text/event-stream' } }),
  }).result();
  clearTimeout(safety);
  assert.equal(safetyFired, false, 'Native SSE body must not need safety abort');
  assert.equal(result.stopReason, 'aborted');
  assert.equal(aborts, 1);
  assert.equal(entries.length, 1, 'Persist a metadata-only timeout diagnostic');
  await emit('message_end', { message: result });

  // Timer clears before any tool, including nested provider calls inside tools.
  controller = new AbortController(); ctx.signal = controller.signal;
  await emit('agent_start');
  await emit('before_provider_request');
  await emit('tool_execution_start', { toolCallId: 'write' });
  await emit('before_provider_request');
  await emit('message_update', { assistantMessageEvent: { type: 'thinking_delta', delta: 'nested tool progress' } });
  await wait(60);
  assert.equal(aborts, 1, 'Never abort in-flight writes/tools');
  await emit('tool_execution_end', { toolCallId: 'write' });
  await emit('before_provider_request');
  await emit('message_end', { message: { role: 'assistant', stopReason: 'toolUse' } });
  await wait(60);
  assert.equal(aborts, 1, 'Completed response must disarm deadline');

  // Automatic retries share the original budget; they cannot reset it.
  await emit('before_provider_request');
  await wait(20);
  await emit('message_end', { message: { role: 'assistant', stopReason: 'error' } });
  await emit('agent_start');
  await emit('before_provider_request');
  await wait(20);
  assert.equal(aborts, 2, 'Retry must retain original deadline');
  await emit('agent_settled');
  controller = new AbortController(); ctx.signal = controller.signal;
  await emit('agent_start');
  await emit('before_provider_request');
  await emit('session_shutdown');
  await wait(60);
  assert.equal(aborts, 2, 'Shutdown must remove stale timers');
  // Parallel tools remain protected until every tool has completed.
  controller = new AbortController(); ctx.signal = controller.signal;
  await emit('agent_start');
  await emit('tool_execution_start', { toolCallId: 'a' });
  await emit('tool_execution_start', { toolCallId: 'b' });
  await emit('tool_execution_end', { toolCallId: 'a' });
  await emit('before_provider_request');
  await wait(60);
  assert.equal(aborts, 2);
  await emit('tool_execution_end', { toolCallId: 'b' });
  await emit('before_provider_request');
  await emit('agent_settled');
  await wait(60);
  assert.equal(aborts, 2, 'Settled sessions cannot be aborted by a stale timer');

  process.env.MEGAI_PROVIDER_TIMEOUT_MS = '0';
  await emit('session_start');
  await emit('agent_start');
  await emit('before_provider_request');
  await wait(60);
  assert.equal(aborts, 2, 'Explicit opt-out must win');
  await emit('session_shutdown');
  process.env.MEGAI_PROVIDER_TIMEOUT_MS = '30';
  await emit('session_start');
  await emit('agent_start');
  await emit('before_provider_request');
  ctx.isIdle = () => { throw new Error('Extension runtime is no longer active'); };
  await wait(60);
  assert.equal(aborts, 2, 'SDK-disposed context must not crash from a queued timer');
  ctx.isIdle = () => false;
  controller = new AbortController(); ctx.signal = controller.signal;
  const originalError = console.error;
  const diagnosticErrors = [];
  console.error = message => diagnosticErrors.push(message);
  loader.getExtensions().runtime.appendEntry = () => { throw new Error('fixture storage failure'); };
  ctx.hasUI = true;
  ctx.ui.notify = () => { throw new Error('fixture UI failure'); };
  try {
    await emit('before_provider_request');
    await wait(60);
    assert.equal(aborts, 3, 'Diagnostic failures must not prevent native cancellation');
    assert.equal(diagnosticErrors.length, 2, 'Storage and UI diagnostics fail independently');
  } finally { console.error = originalError; }
  await emit('session_shutdown');
  // Native tool-argument streaming is provider progress, not tool execution.
  ctx.hasUI = false;
  const beforeProgress = aborts;
  await emit('session_start');
  await emit('agent_start');
  await emit('before_provider_request');
  for (let i = 0; i < 6; i++) {
    await wait(10);
    await emit('message_update', { assistantMessageEvent: { type: 'toolcall_delta', delta: 'x' } });
  }
  assert.equal(aborts, beforeProgress, 'Tool argument progress must renew inactivity deadline');
  await emit('message_end', { message: { role: 'assistant', stopReason: 'toolUse' } });
  await wait(60);
  assert.equal(aborts, beforeProgress, 'Completed streamed tool arguments must disarm timer');
  await emit('session_shutdown');
  console.log('PASS: actual loader/native SSE cancellation, parallel/nested tool safety, tool argument progress, retry budget, cleanup, opt-out, disposed context and diagnostic failures');
} finally {
  if (original === undefined) delete process.env.MEGAI_PROVIDER_TIMEOUT_MS;
  else process.env.MEGAI_PROVIDER_TIMEOUT_MS = original;
  rmSync(temp, { recursive: true, force: true });
}
// Installed third-party factories may keep timers; this is a loader snapshot.
if (process.env.MEGAI_PROVIDER_GUARD_AGENT_DIR) process.exit(0);

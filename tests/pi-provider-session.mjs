// Full AgentSession binding, native SSE and native retry backoff; no network/auth files.
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
assert.ok(process.env.PI_PACKAGE_ROOT, 'Set PI_PACKAGE_ROOT to installed Pi');
const root = process.env.PI_PACKAGE_ROOT;
const { createAgentSession, DefaultResourceLoader, ModelRuntime, SessionManager, SettingsManager } =
  await import(pathToFileURL(join(root, 'dist/index.js')));
const { stream } = await import(pathToFileURL(join(process.env.PI_AI_PACKAGE_ROOT ?? join(root, '../pi-ai'), 'dist/api/openai-codex-responses.js')));
const temp = mkdtempSync(join(tmpdir(), 'pi-provider-session-'));
const previous = process.env.MEGAI_PROVIDER_TIMEOUT_MS;
const sessions = [];
try {
  process.env.PI_OFFLINE = '1';
  process.env.MEGAI_PROVIDER_TIMEOUT_MS = '80';
  const runtime = await ModelRuntime.create({
    authPath: join(temp, 'auth.json'), modelsPath: join(temp, 'models.json'),
    modelsStorePath: join(temp, 'models-store.json'), allowModelNetwork: false,
  });
  const apiKey = 'x.' + Buffer.from(JSON.stringify({
    'https://api.openai.com/auth': { chatgpt_account_id: 'fixture' },
  })).toString('base64url') + '.x';
  // Bypass only the prompt auth preflight for this in-memory offline fixture.
  // Native streaming below receives a synthetic JWT and a no-network fetch.
  runtime.hasConfiguredAuth = () => true;
  const model = runtime.getModel('openai-codex', 'gpt-6-astra');
  assert.ok(model, 'Approved fixture model must be available in selected installed Pi');

  for (const mode of ['stream', 'retry', 'dispose']) {
    const settingsManager = SettingsManager.inMemory({
      packages: [], compaction: { enabled: false },
      retry: { enabled: true, maxRetries: 3, baseDelayMs: 500 },
    });
    const loader = new DefaultResourceLoader({
      cwd: temp, agentDir: join(temp, 'agent'), settingsManager,
      noSkills: true, noPromptTemplates: true,
      additionalExtensionPaths: [resolve('pi-skill/provider-guard/index.ts')],
      systemPromptOverride: () => 'Synthetic offline test.',
      agentsFilesOverride: () => ({ agentsFiles: [] }),
    });
    await loader.reload();
    const sessionManager = SessionManager.inMemory(temp);
    const { session } = await createAgentSession({
      cwd: temp, agentDir: join(temp, 'agent'), modelRuntime: runtime, model,
      thinkingLevel: 'high', noTools: 'all', resourceLoader: loader,
      settingsManager, sessionManager,
    });
    sessions.push(session);
    await session.bindExtensions({});
    const events = [];
    session.subscribe(event => events.push(event));
    let calls = 0;
    session.agent.streamFunction = (selected, context, options) => stream(selected, context, {
      ...options, apiKey, transport: 'sse', timeoutMs: 10, maxRetries: 0,
      fetch: async () => {
        calls++;
        if (mode === 'dispose') setTimeout(() => session.dispose(), 20);
        return new Response(new ReadableStream({ start(c) {
          if (mode === 'retry') c.error(new Error('terminated'));
          else c.enqueue(new TextEncoder().encode(': keepalive\n\n'));
        } }), { headers: { 'content-type': 'text/event-stream' } });
      },
    });
    let safetyFired = false;
    const safety = setTimeout(() => { safetyFired = true; void session.abort(); }, 1500);
    try { await session.prompt('Synthetic timeout fixture.'); }
    finally { clearTimeout(safety); }
    assert.equal(safetyFired, false, `${mode}: must settle without safety abort`);
    if (mode === 'dispose') {
      // Keep the event loop alive past the deadline: any uncaught stale-context
      // callback or rejected promise fails this process, not just the assertion.
      await new Promise(resolve => setTimeout(resolve, 120));
      assert.equal(calls, 1);
      assert.equal(sessionManager.getEntries().filter(e => e.customType === 'megai-provider-timeout').length, 0);
      continue;
    }
    assert.equal(session.isIdle, true);
    assert.equal(calls, 1, `${mode}: no replay after deadline`);
    const diagnostics = sessionManager.getEntries().filter(e => e.customType === 'megai-provider-timeout');
    assert.equal(diagnostics.length, 1, `${mode}: durable timeout evidence`);
    assert.ok(diagnostics[0].data.elapsedMs >= 80);
    if (mode === 'stream') {
      assert.ok(session.messages.some(m => m.role === 'assistant' && m.stopReason === 'aborted'));
      assert.equal(events.filter(e => e.type === 'auto_retry_start').length, 0);
    } else {
      assert.equal(events.filter(e => e.type === 'auto_retry_start').length, 1);
      assert.ok(events.some(e => e.type === 'auto_retry_end' && e.finalError === 'Retry cancelled'));
      assert.ok(sessionManager.getEntries().some(e => e.message?.errorMessage === 'terminated'),
        'Original provider error must remain in native history');
    }
  }
  console.log('PASS: full AgentSession native SSE abort, no retry after abort, actual retry-backoff cancellation, preserved error history, direct SDK disposal');
} finally {
  for (const session of sessions) session.dispose();
  if (previous === undefined) delete process.env.MEGAI_PROVIDER_TIMEOUT_MS;
  else process.env.MEGAI_PROVIDER_TIMEOUT_MS = previous;
  rmSync(temp, { recursive: true, force: true });
}

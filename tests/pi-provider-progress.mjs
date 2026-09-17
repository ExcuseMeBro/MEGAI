// Actual AgentSession + native Codex SSE; only the external HTTP boundary is synthetic.
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
assert.ok(process.env.PI_PACKAGE_ROOT);
const root = process.env.PI_PACKAGE_ROOT;
const { createAgentSession, DefaultResourceLoader, ModelRuntime, SessionManager, SettingsManager } =
  await import(pathToFileURL(join(root, 'dist/index.js')));
const { stream } = await import(pathToFileURL(join(process.env.PI_AI_PACKAGE_ROOT ?? join(root, '../pi-ai'), 'dist/api/openai-codex-responses.js')));
const temp = mkdtempSync(join(tmpdir(), 'pi-provider-progress-'));
const previous = process.env.MEGAI_PROVIDER_TIMEOUT_MS;
const sessions = [];
try {
  process.env.PI_OFFLINE = '1';
  process.env.MEGAI_PROVIDER_TIMEOUT_MS = '120';
  const runtime = await ModelRuntime.create({ authPath: join(temp, 'auth.json'), modelsPath: join(temp, 'models.json'), modelsStorePath: join(temp, 'store.json'), allowModelNetwork: false });
  runtime.hasConfiguredAuth = () => true;
  const model = runtime.getModel('openai-codex', 'gpt-6-astra');
  assert.ok(model);
  const apiKey = 'x.' + Buffer.from(JSON.stringify({ 'https://api.openai.com/auth': { chatgpt_account_id: 'fixture' } })).toString('base64url') + '.x';
  for (const mode of ['thinking', 'text', 'stalled', 'empty']) {
    const settingsManager = SettingsManager.inMemory({ packages: [], compaction: { enabled: false }, retry: { enabled: true, maxRetries: 3, baseDelayMs: 500 } });
    const loader = new DefaultResourceLoader({ cwd: temp, agentDir: join(temp, 'agent'), settingsManager, noSkills: true, noPromptTemplates: true,
      additionalExtensionPaths: [process.env.MEGAI_TEST_PROVIDER_GUARD || resolve('pi-skill/provider-guard/index.ts')], systemPromptOverride: () => 'Offline fixture.', agentsFilesOverride: () => ({ agentsFiles: [] }) });
    await loader.reload();
    assert.deepEqual(loader.getExtensions().errors, []);
    const sessionManager = SessionManager.inMemory(temp);
    const { session } = await createAgentSession({ cwd: temp, agentDir: join(temp, 'agent'), modelRuntime: runtime, model, thinkingLevel: 'high', noTools: 'all', resourceLoader: loader, settingsManager, sessionManager });
    sessions.push(session);
    await session.bindExtensions({});
    const events = [];
    session.subscribe(event => events.push(event));
    let calls = 0, pulse, ticks = 0;
    session.agent.streamFunction = (selected, context, options) => stream(selected, context, { ...options, apiKey, transport: 'sse', timeoutMs: 10, maxRetries: 0,
      fetch: async () => {
        calls++;
        return new Response(new ReadableStream({ start(controller) {
          const send = data => controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify(data)}\n\n`));
          const text = mode === 'text';
          send({ type: 'response.created', response: { id: 'fixture' } });
          send({ type: 'response.output_item.added', output_index: 0, item: { type: text ? 'message' : 'reasoning', id: 'item', role: 'assistant' } });
          pulse = setInterval(() => {
            ticks++;
            if (mode !== 'stalled' || ticks <= 3) send({ type: text ? 'response.output_text.delta' : 'response.reasoning_summary_text.delta', output_index: 0, delta: mode === 'empty' ? '' : 'tick' });
            if (ticks === 12 && (mode === 'thinking' || mode === 'text')) {
              clearInterval(pulse);
              send({ type: 'response.completed', response: { id: 'fixture', status: 'completed', output: [], usage: { input_tokens: 1, output_tokens: 1, total_tokens: 2 } } });
              controller.close();
            }
          }, 25);
        }, cancel() { clearInterval(pulse); } }), { headers: { 'content-type': 'text/event-stream' } });
      },
    });
    let safetyFired = false;
    const safety = setTimeout(() => { safetyFired = true; void session.abort(); }, 2000);
    try { await session.prompt('Offline active-progress fixture.'); }
    finally { clearTimeout(safety); clearInterval(pulse); }
    assert.equal(safetyFired, false, `${mode}: guard or normal completion must settle without fallback`);
    assert.equal(calls, 1, `${mode}: never replay provider or tools`);
    const message = session.messages.filter(m => m.role === 'assistant').at(-1);
    const diagnostics = sessionManager.getEntries().filter(e => e.customType === 'megai-provider-timeout');
    if (mode === 'thinking' || mode === 'text') {
      assert.ok(events.some(e => e.type === 'message_update' && e.assistantMessageEvent?.delta === 'tick'), 'Native progress must reach AgentSession');
      assert.equal(message.stopReason, 'stop', `${mode}: active provider progress must survive beyond the initial deadline`);
      assert.equal(ticks, 12);
      assert.equal(diagnostics.length, 0);
      assert.equal(message.content[0][mode], 'tick'.repeat(12));
    } else {
      assert.equal(message.stopReason, 'aborted', `${mode}: genuine inactivity must still abort`);
      assert.equal(diagnostics.length, 1);
      if (mode === 'stalled') assert.ok(ticks >= 7, 'Silence budget starts after last real progress, not request start');
      else assert.ok(ticks < 12, 'Empty deltas must not extend the deadline');
    }
    session.dispose();
  }
  console.log('PASS: 4 full native AgentSession scenarios: sustained thinking/text complete, stopped progress and empty deltas abort without replay.');
} finally {
  for (const session of sessions) session.dispose();
  if (previous === undefined) delete process.env.MEGAI_PROVIDER_TIMEOUT_MS; else process.env.MEGAI_PROVIDER_TIMEOUT_MS = previous;
  rmSync(temp, { recursive: true, force: true });
}

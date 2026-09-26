import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import { homedir, tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';

const piVersion = execFileSync('pi', ['--version'], { encoding: 'utf8' }).trim();
const { DefaultResourceLoader, SettingsManager } = await import(
  pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js'))
);
const cwd = mkdtempSync(join(tmpdir(), 'pi-laya-shadow-'));
const previous = Object.fromEntries(['MEGAI_LAYA_SHADOW', 'MEGAI_LAYA_SHADOW_PORT'].map(k => [k, process.env[k]]));
const requests = [];
let responseMode = 'valid';
const server = createServer(async (request, response) => {
  let body = '';
  for await (const chunk of request) body += chunk;
  requests.push({ path: request.url, body: JSON.parse(body) });
  if (responseMode === 'slow') await new Promise(done => setTimeout(done, 1700));
  response.setHeader('content-type', 'application/json');
  response.end(responseMode === 'invalid' ? JSON.stringify({ answers: { noise: { type: 'boolean', probability: 4 } } })
    : JSON.stringify({ answers: { noise: { type: 'boolean', probability: 0.91 } }, warnings: [] }));
});
try {
  await new Promise(done => server.listen(0, '127.0.0.1', done));
  process.env.MEGAI_LAYA_SHADOW_PORT = String(server.address().port);
  delete process.env.MEGAI_LAYA_SHADOW;
  const loader = new DefaultResourceLoader({ cwd, agentDir: join(cwd, 'agent'),
    settingsManager: SettingsManager.inMemory({ packages: [] }),
    additionalExtensionPaths: [resolve('pi-skill/laya-shadow/index.ts')],
  });
  await loader.reload();
  const loaded = loader.getExtensions();
  assert.deepEqual(loaded.errors, []);
  assert.equal(loaded.extensions.length, 1);
  const extension = loaded.extensions[0];
  const ledger = [];
  loaded.runtime.appendEntry = (type, data) => ledger.push({ type, data });
  const ctx = { cwd, model: { provider: 'openai-codex', id: 'keep' }, thinkingLevel: 'high' };
  const invoke = async (name, event = {}) => {
    for (const handler of extension.handlers.get(name) || []) await handler(event, ctx);
  };
  const text = 'PASS: test case 1\n'.repeat(95);
  const event = { type: 'tool_result', toolName: 'bash', toolCallId: 'test-1',
    input: { command: 'npm test' }, content: [{ type: 'text', text }], details: {}, isError: false };
  const original = structuredClone(event);
  await invoke('session_start');
  await invoke('tool_result', event);
  await invoke('session_shutdown');
  assert.deepEqual(event, original, 'default must not change tool output');
  assert.equal(requests.length, 0, 'no opt-in = no local request');
  assert.equal(ledger.length, 0);

  process.env.MEGAI_LAYA_SHADOW = '1';
  await invoke('session_start');
  await invoke('tool_result', event);
  await invoke('session_shutdown');
  assert.equal(requests.length, 1);
  assert.equal(requests[0].path, '/evaluate');
  assert.equal(requests[0].body.questions.noise.type, 'boolean');
  assert.equal(requests[0].body.state.includes('PASS:'), true);
  assert.ok(requests[0].body.state.length <= 907, 'local judge sees only a bounded sample');
  assert.deepEqual(event, original, 'shadow verdict cannot change native tool result');
  assert.equal(ledger.length, 1);
  assert.equal(ledger[0].type, 'megai.laya.shadow');
  assert.equal(ledger[0].data.status, 'noise');
  assert.equal(ledger[0].data.probability, 0.91);
  assert.equal(JSON.stringify(ledger).includes('PASS:'), false, 'no raw output in session ledger');

  await invoke('session_start');
  await invoke('tool_result', { ...event, toolCallId: 'failure', isError: true });
  await invoke('tool_result', { ...event, toolCallId: 'source', input: { command: 'git diff' } });
  await invoke('session_shutdown');
  assert.equal(requests.length, 1, 'never classify failures or non-test commands');
  responseMode = 'invalid';
  await invoke('session_start');
  await invoke('tool_result', event);
  await invoke('session_shutdown');
  assert.equal(ledger.at(-1).data.status, 'unavailable');
  assert.deepEqual(event, original);
  responseMode = 'slow';
  await invoke('session_start');
  const started = Date.now();
  await invoke('tool_result', event);
  assert.ok(Date.now() - started < 300, 'shadow evaluation must not delay the tool result');
  await invoke('session_shutdown');
  assert.equal(ledger.at(-1).data.status, 'unavailable');
  assert.deepEqual(event, original);
  assert.deepEqual(ctx.model, { provider: 'openai-codex', id: 'keep' });
  assert.equal(ctx.thinkingLevel, 'high');
  assert.equal(extension.handlers.has('tool_call'), false);
  assert.equal(extension.handlers.has('context'), false);
  const runtimePath = join(homedir(), '.megai/laya-runtime/bin/python');
  const extensionPath = join(homedir(), '.pi/agent/extensions/megai-laya/index.ts');
  console.log(`PASS: Pi ${piVersion}; opt-in local shadow verdict, metadata-only ledger, default/failure/timeout fail-open; prior Laya runtime ${existsSync(runtimePath) ? 'present' : 'absent'}, prior extension ${existsSync(extensionPath) ? 'present' : 'absent'}; fixture uses mock endpoint, not live inference`);
} finally {
  await new Promise(done => server.close(done));
  for (const [k, v] of Object.entries(previous)) v === undefined ? delete process.env[k] : process.env[k] = v;
  rmSync(cwd, { recursive: true, force: true });
}

// Offline: the real Pi extension loader plus stubbed runtime actions. No provider call.
// Proves a provider failure continues on the configured partner exactly once, that
// reconciliation-only failures never switch, and that the optional user config is
// honoured without changing anything else about the session.
import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

assert.ok(process.env.PI_PACKAGE_ROOT, 'Set PI_PACKAGE_ROOT to installed Pi');
const { DefaultResourceLoader, SettingsManager } = await import(
  pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js')));
process.env.PI_OFFLINE = '1';

const temp = mkdtempSync(join(tmpdir(), 'pi-model-fallback-'));
const agentDir = join(temp, 'agent');
mkdirSync(agentDir, { recursive: true });
process.env.PI_CODING_AGENT_DIR = agentDir;
const config = join(agentDir, 'model-fallback.json');

const loader = new DefaultResourceLoader({
  cwd: temp, agentDir,
  settingsManager: SettingsManager.inMemory({ packages: [] }),
  additionalExtensionPaths: [resolve('pi-skill/model-fallback/index.ts')],
});
await loader.reload();
const loaded = loader.getExtensions();
assert.deepEqual(loaded.errors, []);
const ext = loaded.extensions.find(e => /model-fallback[/\\]index\.ts$/.test(e.resolvedPath));
assert.ok(ext, 'Model fallback extension must load');

const models = new Map([
  ['deepseek/deepseek-flash', { id: 'deepseek-flash', provider: 'deepseek' }],
  ['openai-codex/gpt-6-sol', { id: 'gpt-6-sol', provider: 'openai-codex' }],
  ['openai-codex/gpt-6-luna', { id: 'gpt-6-luna', provider: 'openai-codex' }],
  ['openai-codex/gpt-5.5', { id: 'gpt-5.5', provider: 'openai-codex' }],
]);

const switched = [], sent = [], entries = [], notices = [];
loaded.runtime.setModel = async (model) => { switched.push(`${model.provider}/${model.id}`); return true; };
loaded.runtime.sendUserMessage = (text, options) => { sent.push({ text, options }); };
loaded.runtime.appendEntry = (type, data) => { entries.push({ type, data }); };

const ctx = {
  hasUI: true, mode: 'interactive', cwd: temp,
  modelRegistry: { find: (provider, id) => models.get(`${provider}/${id}`) },
  ui: { notify: (message, level) => notices.push({ message, level }) },
};

const emit = async (name, event = {}) => {
  for (const hook of ext.handlers.get(name) ?? []) await hook(event, ctx);
};
const assistant = (provider, model, stopReason, errorMessage) =>
  ({ message: { role: 'assistant', provider, model, stopReason, errorMessage } });
const reset = () => { for (const list of [switched, sent, entries, notices]) list.length = 0; };
const fail = async (provider, model, errorMessage) => {
  await emit('message_end', assistant(provider, model, 'error', errorMessage));
  await emit('agent_end');
};

await emit('session_start');
reset();

// A provider failure on the configured primary continues on the partner, visibly.
await fail('deepseek', 'deepseek-flash', '402 {"error":{"message":"Insufficient Balance","code":"invalid_request_error"}}');
assert.deepEqual(switched, ['openai-codex/gpt-6-sol'], 'Continue on the configured partner');
assert.equal(sent.length, 1, 'Continue the unfinished task once');
assert.match(sent[0].text, /Insufficient Balance/);
assert.equal(sent[0].options?.deliverAs, 'followUp', 'Queue the continuation into the live run');
assert.equal(entries.length, 1);
assert.equal(entries[0].type, 'megai-model-fallback');
assert.deepEqual(entries[0].data, {
  from: 'deepseek/deepseek-flash', to: 'openai-codex/gpt-6-sol',
  reason: '402 {"error":{"message":"Insufficient Balance","code":"invalid_request_error"}}',
});
assert.equal(notices.length, 1, 'The switch must be visible');
assert.equal(notices[0].level, 'warning');

// The partner failing too must not ping-pong back to the already failed primary.
await fail('openai-codex', 'gpt-6-sol', '503 Service Unavailable');
assert.deepEqual(switched, ['openai-codex/gpt-6-sol'], 'Never cycle back to a failed model');
assert.equal(sent.length, 1);

// A completed run stays where it is.
reset();
await emit('message_end', assistant('deepseek', 'deepseek-flash', 'stop'));
await emit('agent_end');
assert.equal(switched.length + sent.length + entries.length + notices.length, 0);

// Authorization, permission and a shared quota need reconciliation, not a swap; so
// does every context overflow — a different provider does not shrink the prompt.
// The overflow texts are Pi's own OVERFLOW_PATTERNS catalogue, which decides what Pi
// treats as an overflow, so the extension's deny list must cover all of them.
const overflow = [
  'prompt is too long: 250000 tokens > 200000 maximum',
  'request_too_large',
  'input is too long for requested model',
  'exceeds the context window',
  "exceeds the model's maximum context length of 128,000 tokens",
  'input token count 300000 exceeds the maximum',
  'maximum prompt length is 200000',
  'reduce the length of the messages and try again',
  'maximum context length is 65536 tokens',
  'exceeds the maximum allowed input length of 200,000 tokens',
  "input (250000 tokens) is longer than the model's context length (200000 tokens)",
  'exceeds the limit of 128000',
  'exceeds the available context size',
  'greater than the context length',
  'context window exceeds limit',
  'exceeded model token limit',
  'too large for model with 128000 maximum context length',
  'prompt has 900000 tokens, but the configured context size is 65536 tokens',
  'model_context_window_exceeded',
  'prompt too long; exceeded max context length',
  'range of input length should be [1, 4096]',
  'context_length_exceeded',
  'too many tokens',
  'token limit exceeded',
];
for (const message of ['401 Unauthorized: invalid api key', '403 Forbidden: permission denied', 'shared quota exhausted for this workspace', ...overflow]) {
  reset();
  await fail('deepseek', 'deepseek-flash', message);
  assert.deepEqual(switched, [], `Reconcile instead of switching for: ${message}`);
  assert.equal(sent.length, 0);
}

// Provider-specific exhaustion is what the partner provider exists for.
await emit('session_start');
reset();
for (const message of [
  '402 {"error":{"message":"Insufficient Balance"}}',
  'insufficient_quota: you exceeded your current quota',
  '429 Too Many Requests: rate limit reached',
  'Codex error: The usage limit has been reached',
  '503 Service Unavailable',
]) {
  reset();
  await fail('deepseek', 'deepseek-flash', message);
  assert.deepEqual(switched, ['openai-codex/gpt-6-sol'], `Continue on the partner for: ${message}`);
}

// A model without a configured partner is left alone.
reset();
await fail('openai-codex', 'gpt-5.5', '500 Internal Server Error');
assert.deepEqual(switched, []);

// A new session forgets the previous failure and honours the user override.
writeFileSync(config, JSON.stringify({ fallbacks: { 'deepseek/deepseek-flash': 'openai-codex/gpt-6-luna' } }));
await emit('session_start');
reset();
await fail('deepseek', 'deepseek-flash', '500 Internal Server Error');
assert.deepEqual(switched, ['openai-codex/gpt-6-luna'], 'Use the configured pair');

// An empty map is the documented off switch; an unusable file keeps the defaults.
writeFileSync(config, JSON.stringify({ fallbacks: {} }));
await emit('session_start');
reset();
await fail('deepseek', 'deepseek-flash', '500 Internal Server Error');
assert.deepEqual(switched, [], 'An empty fallbacks object disables the swap');
writeFileSync(config, '{ not json');
await emit('session_start');
reset();
await fail('deepseek', 'deepseek-flash', '500 Internal Server Error');
assert.deepEqual(switched, ['openai-codex/gpt-6-sol'], 'Unusable config keeps the built-in pair');

// An unauthenticated partner cannot be selected, so the session is left untouched.
rmSync(config);
loaded.runtime.setModel = async () => false;
await emit('session_start');
reset();
await fail('deepseek', 'deepseek-flash', '502 Bad Gateway');
assert.equal(sent.length + entries.length + notices.length, 0, 'No switch without a usable partner');

rmSync(temp, { recursive: true, force: true });
console.log('pi-model-fallback: ok');

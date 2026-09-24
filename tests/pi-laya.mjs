#!/usr/bin/env node
// Disposable offline Pi loader exercising the local typed tool and file screening.
import assert from 'node:assert/strict';
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

assert.ok(process.env.PI_PACKAGE_ROOT, 'PI_PACKAGE_ROOT must name installed Pi');
const { DefaultResourceLoader } = await import(pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js')));
const dir = mkdtempSync(join(tmpdir(), 'pi-laya-'));
const agent = join(dir, 'agent');
const extension = join(agent, 'extensions/megai-laya');
mkdirSync(extension, { recursive: true });
for (const name of ['index.ts', 'bridge.py', 'compaction.ts']) {
  copyFileSync(resolve('pi-skill/laya', name), join(extension, name));
}
const keys = ['LAYA_PYTHON', 'LAYA_BRIDGE_TEST', 'LAYA_TEST_DELAY_MS', 'LAYA_TIMEOUT_MS',
  'HF_HUB_OFFLINE', 'TYPESAFE_API_KEY', 'TYPESAFE_ENDPOINT'];
const saved = Object.fromEntries(keys.map(key => [key, process.env[key]]));
process.env.PI_CODING_AGENT_DIR = agent;
process.env.LAYA_PYTHON = 'python3';
process.env.LAYA_BRIDGE_TEST = '1';
process.env.HF_HUB_OFFLINE = '1';
process.env.TYPESAFE_API_KEY = 'forbidden-in-local-call';
process.env.TYPESAFE_ENDPOINT = 'https://api.typesafe.ai/v1/systemone';
const context = { cwd: dir, hasUI: false, mode: 'print', isIdle: () => true, isProjectTrusted: () => false,
  ui: { notify() {} }, abort() {}, getSystemPrompt: () => '' };
function parse(reply) { return JSON.parse(reply.content[0].text); }
try {
  const loader = new DefaultResourceLoader({ cwd: dir, agentDir: agent });
  await loader.reload();
  const loaded = loader.getExtensions();
  assert.deepEqual(loaded.errors, []);
  const tools = new Map(loaded.extensions.flatMap(ext => [...ext.tools].map(([name, tool]) => [name, tool.definition])));
  assert.ok(tools.has('laya'), 'on-device tool is registered');
  assert.ok(tools.has('sift'), 'local screening is registered');
  assert.ok(!tools.has('jev'));
  assert.ok(!loaded.extensions.some(ext => ext.handlers.has('tool_call')), 'no Laya-blocking gate');
  const questions = {
    route: { type: 'choice', instructions: 'Choose route', criteria: { safe: 'safe', unsafe: 'unsafe' } },
    impact: { type: 'score', instructions: 'How much?', criteria: ['low', 'high'] },
    proceed: { type: 'noul', instructions: 'Is this safe?' },
  };
  const result = parse(await tools.get('laya').execute('local-1', { state: 'Work in local mode', questions }, undefined, undefined, context));
  assert.equal(result.ok, true, JSON.stringify(result));
  assert.equal(result.answers.route.choice, 'safe');
  assert.equal(result.answers.impact.type, 'score');
  assert.equal(result.answers.proceed.type, 'noul');
  assert.equal(result.model, 'laya-multilingual-0.3.20');
  const bad = parse(await tools.get('laya').execute('local-2', { state: 'x'.repeat(30000), questions }, undefined, undefined, context));
  assert.equal(bad.ok, false);
  assert.ok(!JSON.stringify(bad).includes('forbidden-in-local-call'));
  const localFile = join(dir, 'notes.txt');
  writeFileSync(localFile, 'Invoice has two charges.');
  const sifted = parse(await tools.get('sift').execute('local-3', { query: 'Which file describes billing?', paths: [localFile] }, undefined, undefined, context));
  assert.equal(sifted.files.length, 1);
  assert.equal(typeof sifted.files[0].probability, 'number');
  writeFileSync(join(dir, '.env'), 'FAKE_SECRET=must-not-read');
  const refused = parse(await tools.get('sift').execute('local-4', { query: 'billing', paths: [join(dir, '.env')] }, undefined, undefined, context));
  assert.ok(refused.files[0].error);
  assert.ok(!JSON.stringify(refused).includes('FAKE_SECRET'));
  const source = readFileSync(resolve('pi-skill/laya/index.ts'), 'utf8');
  assert.ok(!source.includes('fetch(') && !source.includes('TYPESAFE_API_KEY'));
  for (const fn of loaded.extensions.flatMap(ext => ext.handlers.get('session_shutdown') ?? [])) await fn({}, {});
  process.env.LAYA_PYTHON = '/no/such/local/python';
  const crashed = parse(await tools.get('laya').execute('local-5', { state: 'Recover from crash', questions }, undefined, undefined, context));
  assert.equal(crashed.ok, false, 'missing subprocess fails locally');
  assert.ok(!JSON.stringify(crashed).includes('forbidden-in-local-call'));
  process.env.LAYA_PYTHON = '/usr/bin/false';
  const pipeFailure = parse(await tools.get('laya').execute('local-5b', { state: 'Recover from a broken pipe '.repeat(7000), questions }, undefined, undefined, context));
  assert.equal(pipeFailure.ok, false, 'early worker exit must become a bounded local error');
  assert.ok(!JSON.stringify(pipeFailure).includes('write EPIPE'));
  process.env.LAYA_PYTHON = 'python3';
  process.env.LAYA_TEST_DELAY_MS = '500';
  process.env.LAYA_TIMEOUT_MS = '50';
  const timed = parse(await tools.get('laya').execute('local-6', { state: 'Bound a hung worker', questions }, undefined, undefined, context));
  assert.equal(timed.ok, false, 'stalled local model must fail within a bounded deadline');
  assert.match(timed.error, /timed out/);
  console.log('pi-laya offline loader + tool + sift + crash/timeout OK');
} finally {
  for (const key of keys) saved[key] === undefined ? delete process.env[key] : process.env[key] = saved[key];
  rmSync(dir, { recursive: true, force: true });
}

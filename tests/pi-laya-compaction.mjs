#!/usr/bin/env node
// Actual Pi compaction event hook with offline on-device Laya stub; no unique loss.
import assert from 'node:assert/strict';
import { copyFileSync, mkdirSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
assert.ok(process.env.PI_PACKAGE_ROOT);
const { DefaultResourceLoader } = await import(pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js')));
const dir = mkdtempSync(join(tmpdir(), 'pi-laya-compaction-'));
const agent = join(dir, 'agent'), extension = join(agent, 'extensions/megai-laya');
mkdirSync(extension, { recursive: true });
for (const name of ['index.ts', 'compaction.ts', 'bridge.py']) copyFileSync(resolve('pi-skill/laya', name), join(extension, name));
process.env.LAYA_PYTHON = 'python3';
process.env.LAYA_BRIDGE_TEST = '1';
process.env.LAYA_TEST_NOUL = '0.5';
process.env.PI_CODING_AGENT_DIR = agent;
const user = { role: 'user', content: [{ type: 'text', text: 'Keep the facts.' }], timestamp: 1 };
const result = (text, id) => ({ role: 'toolResult', toolCallId: id, toolName: 'read', content: [{ type: 'text', text }], isError: false, timestamp: id.length + 2 });
function event(messages, overrides = {}) {
  return { reason: 'threshold', customInstructions: '', signal: new AbortController().signal,
    preparation: { messagesToSummarize: messages, turnPrefixMessages: [], previousSummary: '',
      firstKeptEntryId: 'entry-7', tokensBefore: 10000, fileOps: { read: ['a.txt'], edited: [], written: [] } }, ...overrides };
}
try {
  const loader = new DefaultResourceLoader({ cwd: dir, agentDir: agent });
  await loader.reload();
  const loaded = loader.getExtensions();
  assert.deepEqual(loaded.errors, []);
  const handler = loaded.extensions.flatMap(e => e.handlers.get('session_before_compact') ?? [])[0];
  assert.equal(typeof handler, 'function');
  const unique = 'Unique result, never discard. '.repeat(160);
  assert.equal(await handler(event([user, result(unique, 'one')])), undefined, 'one unique tool result uses native summarization');
  const long = 'long '.repeat(5000);
  assert.equal(await handler(event([user, result(long, 'one'), result(long, 'two')])), undefined, 'long state uses native summarization');
  const stillLarge = 'unique '.repeat(1300);
  assert.equal(await handler(event([user, result(stillLarge, 'one'), result(stillLarge, 'two')])), undefined,
    'a still-large summary must use native summarization');
  assert.equal(await handler(event([user, result(unique, 'one'), result(unique, 'two')], { reason: 'overflow' })), undefined);
  assert.equal(await handler(event([user, result(unique, 'one'), result(unique, 'two')], { customInstructions: 'summarize risks' })), undefined);
  assert.equal(await handler(event([user, result(unique, 'one'), result(unique, 'two')])), undefined,
    'an uncertain boundary result uses Pi native summarization');
  for (const fn of loaded.extensions.flatMap(e => e.handlers.get('session_shutdown') ?? [])) await fn({}, {});
  process.env.LAYA_TEST_NOUL = '0.75';
  const paired = await handler(event([user, result(unique, 'one'), result(unique, 'two')]));
  assert.ok(paired?.compaction, 'only exact repeated outputs are safely reduced');
  assert.ok(paired.compaction.summary.includes(unique), 'the first exact copy remains');
  assert.ok(!paired.compaction.summary.includes('Jev'));
  assert.equal(paired.compaction.details.laya.uniqueResultsOmitted, 0);
  assert.equal(paired.compaction.firstKeptEntryId, 'entry-7');
  const sameTextDifferentTools = await handler(event([
    user,
    {...result(unique, 'one'), toolName: 'read'},
    {...result(unique, 'two'), toolName: 'search'},
  ]));
  assert.equal(sameTextDifferentTools, undefined, 'same text from different tools is not a safe duplicate');
  const sameTextDifferentErrors = await handler(event([
    user,
    {...result(unique, 'one'), toolName: 'read', isError: false},
    {...result(unique, 'two'), toolName: 'read', isError: true},
  ]));
  assert.equal(sameTextDifferentErrors, undefined, 'same text with different error status is not a safe duplicate');
  const other = 'Other '.repeat(500);
  const repeatedA = await handler(event([user, result(unique, 'call-1'), result(other, 'call-2'), result(unique, 'call-3')]));
  const repeatedB = await handler(event([user, result(unique, 'call-1'), result(other, 'call-2'), result(other, 'call-3')]));
  assert.ok(repeatedA?.compaction && repeatedB?.compaction);
  assert.notEqual(repeatedA.compaction.summary, repeatedB.compaction.summary,
    'duplicate marker must identify the retained result instead of losing call identity');
  assert.match(repeatedA.compaction.summary, /retained earlier at tool=read call=call-1 error=false/);
  assert.match(repeatedB.compaction.summary, /retained earlier at tool=read call=call-2 error=false/);
  for (const fn of loaded.extensions.flatMap(e => e.handlers.get('session_shutdown') ?? [])) await fn({}, {});
  process.env.LAYA_PYTHON = '/no/such/local/python';
  assert.equal(await handler(event([user, result(unique, 'one'), result(unique, 'two')])), undefined,
    'crashed local worker must use Pi native summarization');
  console.log('pi-laya compaction conservative fallback OK');
} finally { rmSync(dir, { recursive: true, force: true }); }

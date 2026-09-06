import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { paginate, decodeRpc, toolData, ReadOnlyAsana, privateRoot, saveJson, singleFlightTokens } from '../lib/asana_plane_export.mjs';

test('pagination requires terminal evidence, follows all pages, rejects loops', async () => {
  const calls = [];
  assert.deepEqual(await paginate(async args => { calls.push(args); return args.offset ? { data: [2], next_page: null } : { data: [1], next_page: { offset: 'next' } }; }, { completed_since: '1970-01-01' }), [1, 2]);
  assert.equal(calls[1].completed_since, '1970-01-01');
  await assert.rejects(paginate(async () => ({ data: [] })), /completion evidence/);
  await assert.rejects(paginate(async () => ({ data: [], next_page: { offset: 'loop' } })), /Repeated/);
  await assert.rejects(paginate(async () => ({ data: [], next_page: {} })), /Malformed/);
});
test('RPC checks identity, protocol errors and SSE data', () => {
  assert.deepEqual(decodeRpc('event: message\ndata: {"id":1,"result":{"ok":true}}\n\n', 1), { ok: true });
  assert.throws(() => decodeRpc('{"id":2,"result":{}}', 1), /matching/);
  assert.throws(() => decodeRpc('{"id":1,"error":{"code":-1,"message":"private"}}', 1), /^Error: MCP protocol error -1$/);
});
test('nested failures cannot appear as successful data', () => {
  assert.throws(() => toolData({ isError: true }), /isError/);
  assert.throws(() => toolData({ structuredContent: { error: 'private' } }), /nested/);
  assert.deepEqual(toolData({ content: [{ type: 'text', text: '{"data":[]}' }] }), { data: [] });
});
test('both call and transport reject mutations before fetching credentials', async () => {
  const client = new ReadOnlyAsana(() => { throw new Error('must not read token'); });
  await assert.rejects(client.call('create_tasks', {}), /mutation/);
  await assert.rejects(client.rpc('tools/call', { name: 'asana_create_tasks' }), /mutation/);
  await assert.rejects(client.rpc('other', {}), /method rejected/);
});
test('OAuth refresh is single-flight across parallel reads and caches until near expiry', async () => {
  let loads = 0; let now = 100000;
  const token = singleFlightTokens(async () => { loads++; await new Promise(resolve => setTimeout(resolve, 5)); return { accessToken: 'synthetic-only', expiresAt: now / 1000 + 120 }; }, () => now);
  await Promise.all([token(), token(), token()]); assert.equal(loads, 1);
  await token(); assert.equal(loads, 1);
  now += 70000; await Promise.all([token(), token()]); assert.equal(loads, 2);
});
test('storage remains private, rejects checkout, traversal and symlinks', () => {
  const root = fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()), 'megai-export-test-'));
  try {
    assert.equal(privateRoot(root), root); saveJson(root, 'source/test.json', { synthetic: true });
    assert.equal(fs.statSync(path.join(root, 'source/test.json')).mode & 0o777, 0o600);
    assert.throws(() => saveJson(root, '../escape', {}), /Invalid/);
    fs.symlinkSync(path.join(root, 'source/test.json'), path.join(root, 'link'));
    assert.throws(() => saveJson(root, 'link', {}), /Symlink/);
    fs.mkdirSync(path.join(root, '.git'));
    assert.throws(() => privateRoot(path.join(root, 'data')), /checkout/);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

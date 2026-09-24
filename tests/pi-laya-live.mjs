#!/usr/bin/env node
// Real offline MPS smoke: requires a task-owned Python with cached laya-multilingual.
import assert from 'node:assert/strict';
import { copyFileSync, mkdirSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
assert.ok(process.env.PI_PACKAGE_ROOT && process.env.LAYA_PYTHON);
const { DefaultResourceLoader } = await import(pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js')));
const dir = mkdtempSync(join(tmpdir(), 'pi-laya-live-'));
const agent = join(dir, 'agent'), ext = join(agent, 'extensions/megai-laya');
mkdirSync(ext, { recursive: true });
for (const name of ['index.ts', 'compaction.ts', 'bridge.py']) copyFileSync(resolve('pi-skill/laya', name), join(ext, name));
delete process.env.LAYA_BRIDGE_TEST;
process.env.HF_HUB_OFFLINE = '1';
try {
  const loader = new DefaultResourceLoader({ cwd: dir, agentDir: agent });
  await loader.reload();
  const loaded = loader.getExtensions();
  assert.deepEqual(loaded.errors, []);
  const laya = loaded.extensions.flatMap(e => [...e.tools]).find(([name]) => name === 'laya')?.[1]?.definition;
  assert.ok(laya);
  const questions = { route: { type: 'choice', instructions: 'Choose a safe route', criteria: { safe: 'normal', unsafe: 'not normal' } },
    strength: { type: 'score', instructions: 'Estimate strength', criteria: ['weak', 'strong'] },
    ready: { type: 'noul', instructions: 'Is the request normal?' } };
  const reply = JSON.parse((await laya.execute('live-1', { state: 'A normal local request', questions },
    undefined, undefined, { cwd: dir })).content[0].text);
  assert.equal(reply.ok, true, JSON.stringify(reply));
  assert.equal(reply.model, 'laya-multilingual-0.3.20');
  assert.ok(['safe', 'unsafe'].includes(reply.answers.route.choice));
  assert.ok(reply.answers.strength.score >= 0 && reply.answers.strength.score <= 1);
  assert.ok(reply.answers.ready.noul >= 0 && reply.answers.ready.noul <= 1);
  for (const fn of loaded.extensions.flatMap(e => e.handlers.get('session_shutdown') ?? [])) await fn({}, {});
  console.log('pi-laya real offline MPS smoke OK');
} finally { rmSync(dir, { recursive: true, force: true }); }

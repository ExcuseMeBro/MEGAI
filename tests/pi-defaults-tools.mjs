#!/usr/bin/env node
// Actual offline Pi loader against a disposable agent root and installed package code.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { homedir, tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

assert.ok(process.env.PI_PACKAGE_ROOT, 'Set PI_PACKAGE_ROOT to the installed Pi package');
const { DefaultResourceLoader, SettingsManager } = await import(
  pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js')));
const npmRoot = process.env.PI_DEFAULTS_NPM_ROOT || join(homedir(), '.pi/agent/npm/node_modules');
const temp = mkdtempSync(join(tmpdir(), 'pi-defaults-tools-'));
try {
  process.env.PI_OFFLINE = '1';
  const loader = new DefaultResourceLoader({ cwd: temp, agentDir: join(temp, 'agent'),
    settingsManager: SettingsManager.inMemory({ packages: [] }),
    additionalExtensionPaths: [
      resolve('pi-skill/headroom/index.ts'),
      join(npmRoot, 'pi-mcp-adapter/index.ts'),
      join(npmRoot, 'pi-web-access/index.ts'),
    ],
  });
  await loader.reload();
  const loaded = loader.getExtensions();
  assert.deepEqual(loaded.errors, [], 'Pi extensions must load without errors');
  const tools = loaded.extensions.flatMap(extension => [...extension.tools.keys()]);
  const required = readFileSync(resolve('pi-defaults/verify.mjs'), 'utf8')
    .match(/const requiredTools = (?:engineeringOnly \? \[\] : )?\[(.*?)\]/s)[1].match(/'[^']+'/g).map(name => name.slice(1, -1));
  assert.deepEqual(required.filter(name => !tools.includes(name)), [], 'No required Pi tools missing');
  assert.ok(!tools.includes('sift'), 'Core dependency-only loader does not install optional local Laya');

  // Standalone policy install into an isolated profile must instead load only
  // the local Laya companion; never alter the operator's model preferences.
  const agent = join(temp, '.pi/agent'), megai = join(temp, '.megai');
  const runtime = join(megai, 'laya-runtime');
  mkdirSync(join(runtime, 'bin'), { recursive: true });
  writeFileSync(join(runtime, '.megai-owned'), 'megai-laya\nversion=0.3.20\n');
  writeFileSync(join(runtime, 'bin/python'), '#!/bin/sh\nexit 0\n');
  writeFileSync(join(megai, 'state.json'), '{"tools":{}}\n');
  mkdirSync(agent, { recursive: true });
  const preferences = '{"defaultProvider":"openai-codex","defaultModel":"untouched","defaultThinkingLevel":"high"}\n';
  writeFileSync(join(agent, 'settings.json'), preferences);
  execFileSync('python3', ['-B', resolve('lib/pi_model_policy.py')], {
    cwd: resolve('.'), stdio: 'pipe', env: { ...process.env, HOME: temp, MEGAI_HOME: megai,
      MEGAI_SOURCE: resolve('.'), PI_CODING_AGENT_DIR: agent },
  });
  assert.equal(readFileSync(join(agent, 'settings.json'), 'utf8'), preferences);
  const local = new DefaultResourceLoader({ cwd: temp, agentDir: agent,
    settingsManager: SettingsManager.inMemory({ packages: [] }) });
  await local.reload();
  const installed = local.getExtensions();
  assert.deepEqual(installed.errors, []);
  const names = installed.extensions.flatMap(e => [...e.tools.keys()]);
  assert.ok(names.includes('laya') && names.includes('sift'));
  assert.ok(!names.includes('jev'));
  assert.ok(!installed.extensions.some(e => e.path.includes('megai-jev')));
  assert.ok(!local.getSkills().skills.some(s => s.name === 'jev-browser'));
  console.log('PASS: core Pi tools + installed offline Laya; hosted Jev/browser absent');
} finally {
  rmSync(temp, { recursive: true, force: true });
}
process.exit(0);

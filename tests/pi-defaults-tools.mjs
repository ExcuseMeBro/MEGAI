#!/usr/bin/env node
// Actual offline Pi loader against a disposable agent root and installed package code.
import assert from 'node:assert/strict';
import { readFileSync, mkdtempSync, rmSync } from 'node:fs';
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
    .match(/const requiredTools = \[(.*?)\]/s)[1].match(/'[^']+'/g).map(name => name.slice(1, -1));
  assert.deepEqual(required.filter(name => !tools.includes(name)), [], 'No required Pi tools missing');
  assert.ok(!tools.includes('sift'), 'No retired decision-tool companion remains');
  console.log('PASS: actual Pi loader has all required tools and no retired companion');
} finally {
  rmSync(temp, { recursive: true, force: true });
}
process.exit(0);

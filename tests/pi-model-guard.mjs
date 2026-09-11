// Actual Pi resource selection, offline: no agent/provider is invoked.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

assert.ok(process.env.PI_PACKAGE_ROOT, 'Set PI_PACKAGE_ROOT to installed Pi');
const { DefaultResourceLoader } = await import(pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js')));
const temp = mkdtempSync(join(tmpdir(), 'pi-model-choice-'));
try {
  process.env.PI_OFFLINE = '1';
  const agentDir = process.env.MEGAI_GUARD_AGENT_DIR ?? join(temp, 'agent');
  if (!process.env.MEGAI_GUARD_AGENT_DIR) {
    execFileSync('python3', [resolve('lib/pi_model_policy.py')], { env: {
      ...process.env, HOME: temp, MEGAI_HOME: join(temp, 'megai'),
      MEGAI_SOURCE: resolve('.'), PI_CODING_AGENT_DIR: agentDir,
    } });
  }
  const loader = new DefaultResourceLoader({ cwd: temp, agentDir });
  await loader.reload();
  const loaded = loader.getExtensions();
  assert.deepEqual(loaded.errors, []);
  assert.equal(loaded.extensions.some(ext => /model-guard[/\\]index\.ts$/.test(ext.resolvedPath)), false);
  assert.ok(loaded.extensions.some(ext => /provider-guard[/\\]index\.ts$/.test(ext.resolvedPath)));
  assert.ok(readFileSync(join(agentDir, 'AGENTS.md'), 'utf8').includes('no model allowlist'));
  console.log('PASS: actual Pi loader has no model guard; provider timeout guard remains active');
} finally { rmSync(temp, { recursive: true, force: true }); }
// Third-party factories can leave timers; this is an offline loader snapshot.
process.exit(0);

// Offline installer regression: role routing must never be reinstalled.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const temp = mkdtempSync(join(tmpdir(), 'pi-role-retirement-'));
try {
  for (const preset of [undefined, 'economy', 'native']) {
    const agent = join(temp, preset ?? 'default');
    const flags = preset ? ['--adaptive', '--preset', preset] : [];
    if (preset === 'native') {
      mkdirSync(agent, { recursive: true });
      writeFileSync(join(agent, 'AGENTS.md'), readFileSync(resolve('pi-defaults/AGENTS.md')));
    }
    execFileSync('python3', ['-B', resolve('lib/pi_model_policy.py'), ...flags], {
      env: { ...process.env, HOME: temp, MEGAI_HOME: join(temp, 'megai'),
        MEGAI_SOURCE: resolve('.'), PI_CODING_AGENT_DIR: agent },
    });
    assert.equal(existsSync(join(agent, 'megai-roles.json')), false);
    assert.equal(existsSync(join(agent, 'extensions/megai-role-routing/index.ts')), false);
    assert.ok(!readFileSync(join(agent, 'AGENTS.md'), 'utf8').includes('Use configured roles'));
  }
  assert.equal(existsSync(resolve('pi-skill/role-routing/index.ts')), false);
  console.log('PASS: no role routing in default, economy or native installs');
} finally {
  rmSync(temp, { recursive: true, force: true });
}

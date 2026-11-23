import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

const bin = process.env.MEGAI_SAFE_ANYTHING || 'safe-anything';
const skill = readFileSync(fileURLToPath(new URL('../agent/skills/safe-anything/SKILL.md', import.meta.url)), 'utf8');
const diffSecurity = readFileSync(fileURLToPath(new URL('../agent/skills/diff-security/SKILL.md', import.meta.url)), 'utf8');

test('skill and diff-security keep the offline default', () => {
  assert.match(skill, /Default to `--offline`/);
  assert.match(diffSecurity, /safe-anything <task-worktree> --offline --json/);
});

test('installed scanner finds a planted key offline and never prints its value', { skip: spawnSync(bin, ['--version']).status !== 0 && 'safe-anything not installed' }, t => {
  const dir = mkdtempSync(join(tmpdir(), 'safe-anything-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  const key = 'ghp_' + 'A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8';
  writeFileSync(join(dir, 'app.js'), `const token = "${key}";\nexport default token;\n`);
  const r = spawnSync(bin, [dir, '--offline', '--json', '--fail-on', 'never'], { encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr);
  const findings = JSON.parse(r.stdout).findings;
  assert.ok(findings.some(f => String(f.rule).startsWith('secret.') && f.path.endsWith('app.js')), r.stdout.slice(0, 500));
  assert.ok(!r.stdout.includes(key) && !r.stderr.includes(key), 'secret value redacted');
  const strict = spawnSync(bin, [dir, '--offline'], { encoding: 'utf8' });
  assert.equal(strict.status, 1, 'default --fail-on high exits 1');
});

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { copyFileSync, appendFileSync, existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { homedir, tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

const here = p => fileURLToPath(new URL(p, import.meta.url));
const guard = here('../agent/skills/safe-anything/safe-anything-guard.sh');
const skill = readFileSync(here('../agent/skills/safe-anything/SKILL.md'), 'utf8');
const diffSecurity = readFileSync(here('../agent/skills/diff-security/SKILL.md'), 'utf8');
const real = process.env.SAFE_ANYTHING_BIN || join(homedir(), '.local/lib/safe-anything/1.0.2/safe-anything');
const required = process.env.MEGAI_REQUIRE_SAFE_ANYTHING === '1';
const run = (args, env = {}) => spawnSync('/bin/bash', [guard, ...args], { encoding: 'utf8', env: { ...process.env, SAFE_ANYTHING_BIN: real, ...env } });

test('skills keep the offline default and never open files with secret findings', () => {
  assert.match(skill, /adds `--offline` unless `SAFE_ANYTHING_ONLINE=1`/);
  assert.match(skill, /never open those files at all/); assert.match(diffSecurity, /never open those\s+files/);
  assert.doesNotMatch(skill.split('## Local usage')[0].replace(/\(MEGAI patch[^)]*\)/g, ''), /npx safe-anything`\)/, 'no npx/cargo fallback left');
});

test('guard refuses a missing or tampered binary and MCP mode', t => {
  const dir = mkdtempSync(join(tmpdir(), 'sa-guard-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  assert.equal(run(['--version'], { SAFE_ANYTHING_BIN: join(dir, 'none') }).status, 3);
  writeFileSync(join(dir, 'fake'), '#!/bin/sh\necho safe-anything 1.0.2\n', { mode: 0o755 });
  const fake = run(['--version'], { SAFE_ANYTHING_BIN: join(dir, 'fake') });
  assert.equal(fake.status, 3); assert.match(fake.stderr, /digest mismatch/); assert.equal(fake.stdout, '', 'fake binary never executed');
  assert.equal(run(['mcp']).status, 3);
});

test('pinned binary through the guard: v1.0.2, offline, finds a planted key without printing it', { skip: !required && !existsSync(real) && 'safe-anything not installed (MEGAI_REQUIRE_SAFE_ANYTHING=1 requires it)' }, t => {
  assert.equal(run(['--version']).stdout.trim(), 'safe-anything 1.0.2');
  const dir = mkdtempSync(join(tmpdir(), 'safe-anything-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  const key = 'ghp_' + 'A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8';
  writeFileSync(join(dir, 'app.js'), `const token = "${key}";\n`);
  writeFileSync(join(dir, 'package-lock.json'), '{"lockfileVersion":3,"packages":{"node_modules/lodash":{"version":"4.17.20"}}}');
  const r = run([dir, '--json', '--fail-on', 'never']);
  assert.equal(r.status, 0, r.stderr);
  const rules = JSON.parse(r.stdout).findings.map(f => f.rule);
  assert.ok(rules.some(x => x.startsWith('secret.')));
  assert.ok(!rules.some(x => x.startsWith('dep')), 'offline: no dependency (OSV) findings');
  assert.ok(!r.stdout.includes(key) && !r.stderr.includes(key), 'secret value redacted');
  copyFileSync(real, join(dir, 'tampered')); appendFileSync(join(dir, 'tampered'), 'x');
  assert.equal(run(['--version'], { SAFE_ANYTHING_BIN: join(dir, 'tampered') }).status, 3);
});

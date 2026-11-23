import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { copyFileSync, appendFileSync, existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { homedir, tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

const here = p => fileURLToPath(new URL(p, import.meta.url));
const guard = here('../agent/skills/safe-anything/safe-anything-guard.sh');
const triage = here('../agent/skills/safe-anything/triage.mjs');
const skill = readFileSync(here('../agent/skills/safe-anything/SKILL.md'), 'utf8');
const diffSecurity = readFileSync(here('../agent/skills/diff-security/SKILL.md'), 'utf8');
const real = process.env.SAFE_ANYTHING_BIN || join(homedir(), '.local/lib/safe-anything/1.0.2/safe-anything');
const required = process.env.MEGAI_REQUIRE_SAFE_ANYTHING === '1';
const run = (args, env = {}) => spawnSync('/bin/bash', [guard, ...args], { encoding: 'utf8', env: { ...process.env, SAFE_ANYTHING_BIN: real, ...env } });

test('skills keep the offline default and never open files with secret findings', () => {
  assert.match(skill, /adds `--offline` to every scan unless the\s+first argument is `--online`/);
  assert.match(skill, /never open those files at all/); assert.match(diffSecurity, /Never open a file it lists under SECRET/);
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
  assert.equal(run(['--version'], { SAFE_ANYTHING_BIN: 'safe-anything' }).status, 3, 'relative override rejected');
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
  // A path containing " --help " or "mcp" is still a scan, still offline.
  const odd = join(dir, 'x --help mcp'); execFileSync('mkdir', [odd]); writeFileSync(join(odd, 'package-lock.json'), '{"lockfileVersion":3,"packages":{"node_modules/lodash":{"version":"4.17.20"}}}');
  const oddRun = run([odd, '--json', '--fail-on', 'never']);
  assert.equal(oddRun.status, 0, oddRun.stderr); assert.ok(!JSON.parse(oddRun.stdout).findings.some(f => String(f.rule).startsWith('dep')));
  // triage: secrets listed by location only, other findings in that file marked unverified.
  writeFileSync(join(dir, 'app.js'), `const token = "${key}";\nconst h = require('crypto').createHash('md5');\n`);
  const tri = spawnSync(process.execPath, [triage, dir], { encoding: 'utf8', env: { ...process.env, SAFE_ANYTHING_GUARD: guard } });
  assert.equal(tri.status, 0, tri.stdout + tri.stderr);
  assert.match(tri.stdout, /SECRET findings[\s\S]*app\.js:1/); assert.ok(!tri.stdout.includes(key));
  const bad = spawnSync(process.execPath, [triage, dir], { encoding: 'utf8', env: { ...process.env, SAFE_ANYTHING_GUARD: join(dir, 'nope.sh') } });
  assert.equal(bad.status, 3); assert.match(bad.stdout, /scan: unavailable/);
  copyFileSync(real, join(dir, 'tampered')); appendFileSync(join(dir, 'tampered'), 'x');
  assert.equal(run(['--version'], { SAFE_ANYTHING_BIN: join(dir, 'tampered') }).status, 3);
});

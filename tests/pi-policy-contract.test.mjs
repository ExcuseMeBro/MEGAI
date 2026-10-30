import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { policyProblems } from '../pi-defaults/policy-contract.mjs';

const root = fileURLToPath(new URL('..', import.meta.url));
const source = readFileSync(resolve(root, 'pi-defaults/AGENTS.md'), 'utf8');
// Pin the actual failing version so the regression fixture survives a task commit.
const baselinePolicy = () => execFileSync('git', [
  'show', '7955cbefe4068b019898baadedd1be1a9a80c36c:pi-defaults/AGENTS.md',
], { cwd: root, encoding: 'utf8' });

// The previous installed profile actually directed Plane-only execution and
// required a retired launcher. Keep that version as a real failing fixture.
test('prior profile fails closed instead of passing installer verification', () => {
  const old = baselinePolicy();
  const problems = policyProblems(old);
  assert.ok(problems.includes('obsolete: Plane-only task authority'));
  assert.ok(problems.includes('obsolete: retired workflow launcher'));
  assert.ok(problems.includes('missing: exact remote dev push'));
});

test('installer preflight CLI rejects stale policy and accepts current policy', () => {
  const script = resolve(root, 'pi-defaults/policy-contract.mjs');
  const staging = mkdtempSync(resolve(tmpdir(), 'megai-policy-contract-'));
  try {
    const old = baselinePolicy();
    const stale = resolve(staging, 'old.md');
    writeFileSync(stale, old);
    const red = spawnSync('node', [script, stale], { encoding: 'utf8' });
    assert.equal(red.status, 1);
    assert.match(red.stderr, /obsolete: Plane-only task authority/);
    const green = spawnSync('node', [script, resolve(root, 'pi-defaults/AGENTS.md')], { encoding: 'utf8' });
    assert.equal(green.status, 0, green.stderr);
  } finally {
    rmSync(staging, { recursive: true, force: true });
  }
});

test('source policy has current task and delivery contract', () => {
  assert.deepEqual(policyProblems(source), []);
});

test('installer rejects retired task sync without weakening safety or acceptance', () => {
  assert.ok(policyProblems(source.replace('Do not synchronize Brokan tasks with Plane',
    'Only `/splane` reconciles tasks with Plane')).includes('obsolete: retired task sync guidance'));
  assert.ok(policyProblems(source.replace('Do not synchronize Brokan tasks with Plane',
    'Permit task synchronization')).includes('missing: no task synchronization'));
  assert.deepEqual(policyProblems(source.replace('Brokan is the sole execution tracker',
    'Brokan (local kanban, MCP server `brokan`) is the sole execution tracker')), []);
  assert.ok(policyProblems(source.replace('Brokan is the sole execution tracker',
    'Pellet is the sole execution tracker')).includes('missing: Brokan task authority'));
  assert.ok(policyProblems(source.replace('Guarded safety/installer/acceptance changes retain their formal gate and frozen criteria',
    'Safety changes need no gate')).includes('missing: formal gate preservation'));
});

test('missing or stale safety evidence is diagnosed while intact policy passes', () => {
  assert.ok(policyProblems('').includes('missing: Brokan task authority'));
  assert.ok(policyProblems(source.replace('git ls-remote', 'git remote -v'))
    .includes('missing: independent remote verification'));
  assert.ok(policyProblems(source.replace('Never terminate, signal, archive, restart or close', 'May terminate'))
    .includes('missing: session protection'));
  assert.deepEqual(policyProblems(source), []);
});

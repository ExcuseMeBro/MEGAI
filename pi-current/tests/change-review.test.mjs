import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { chmodSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';
import {
  READ_ONLY_TOOLS, atLeast, boundDiff, buildPacket, changeStack, parseReport, redact, validModel, validRef,
} from '../agent/skills/megai-change-review/review-core.mjs';

const script = fileURLToPath(new URL('../agent/skills/megai-change-review/review.mjs', import.meta.url));

test('change stack orders contracts, logic, wiring, UI, tests, docs', () => {
  const stack = changeStack(['README.md', 'tests/index.test.mjs', 'src/app/index.ts', 'src/policy.mjs', 'package.json',
    'web/components/Panel.tsx', 'ext/config.json', 'pi-current/tests/x.test.mjs', 'src/types/api.ts']);
  assert.deepEqual(stack.map(b => b.name), ['config & contracts', 'core logic', 'wiring, I/O & entry points', 'UI', 'tests', 'docs']);
  assert.deepEqual(stack[0].files, ['package.json', 'ext/config.json', 'src/types/api.ts']);
  assert.deepEqual(stack[1].files, ['src/policy.mjs']);
  assert.deepEqual(stack[4].files, ['tests/index.test.mjs', 'pi-current/tests/x.test.mjs']);
});

const fileDiff = (f, body) => `diff --git a/${f} b/${f}\n--- a/${f}\n+++ b/${f}\n@@ -1 +1 @@\n${body}\n`;

test('diff is bounded: lockfiles hidden, big files cut, total capped', () => {
  const diff = fileDiff('package-lock.json', '+x'.repeat(10)) + fileDiff('a.mjs', '+' + 'a'.repeat(300)) + fileDiff('b.mjs', '+' + 'b'.repeat(300));
  const r = boundDiff(diff, { total: 500, perFile: 200 });
  assert.match(r.skipped[0], /package-lock\.json \(generated/);
  assert.match(r.text, /cut at 200 chars/);
  assert.match(r.skipped[1], /b\.mjs \(over the packet limit/);
  assert.ok(!r.text.includes('package-lock'));
});

test('secret-looking lines are redacted before reaching the reviewer', () => {
  const r = redact(['+const token = "ghp_abcdefghijklmnopqrstuvwx"', '+headers: { Authorization: "Bearer abcdefghijklmnop1234" }',
    '+api_key = AbCdEfGhIjKlMnOp12', ' const tokens = countTokens(text)', '-password: hunter2'].join('\n'));
  assert.equal(r.count, 3);
  assert.ok(!/ghp_|Bearer abc|AbCdEf/.test(r.text));
  assert.match(r.text, /countTokens/);
  assert.match(r.text, /password: hunter2/, 'short values are not treated as secrets');
});

test('argument validation', () => {
  for (const ok of ['origin/dev', 'dev', 'origin/for-ustama', 'task/megai-1-x']) assert.ok(validRef(ok), ok);
  for (const bad of ['-x', '--output=/tmp/x', 'a..b', 'a b', '', 'x;rm']) assert.ok(!validRef(bad), bad);
  for (const ok of ['openai/gpt-6.2-sol', 'openai/gpt-6.2-sol:high', 'opencode-go/deepseek-v4.1-flash']) assert.ok(validModel(ok), ok);
  for (const bad of ['gpt-6.2-sol', 'openai/gpt:ultra', '--model', 'a/b c']) assert.ok(!validModel(bad), bad);
  assert.equal(READ_ONLY_TOOLS, 'read,grep,find,ls');
});

test('packet carries template, goal, stack and diff; report parsing', () => {
  const p = buildPacket({ base: 'origin/dev', head: 'abc', goal: 'Cap outputs', stat: ' a.mjs | 1 +', files: ['a.mjs'], diff: fileDiff('a.mjs', '+x'), dirty: true });
  assert.match(p.text, /independent code reviewer/);
  assert.match(p.text, /Cap outputs/);
  assert.match(p.text, /1\. core logic: a\.mjs/);
  assert.match(p.text, /uncommitted changes; they are NOT part/);
  const report = 'Risk: High — touches auth\n\n## Findings\n### [high] Fallback picks max probability\n- Where: a.mjs:3\n### [low] Naming\nVerdict: fix first\n';
  const r = parseReport(report);
  assert.equal(r.risk, 'High'); assert.equal(r.verdict, 'fix first'); assert.equal(r.findings.length, 2); assert.ok(r.wellFormed);
  assert.ok(atLeast(r.findings, 'high')); assert.ok(!atLeast(r.findings, 'critical'));
  assert.equal(parseReport('### none\nVerdict: ship').wellFormed, false, 'missing risk line is malformed');
});

test('CLI runs a fresh read-only reviewer and maps findings to exit codes', t => {
  const root = mkdtempSync(join(tmpdir(), 'change-review-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const repo = join(root, 'repo');
  const sh = (...a) => execFileSync('git', a, { cwd: repo, encoding: 'utf8' });
  execFileSync('git', ['init', '-q', '-b', 'dev', repo]);
  sh('config', 'user.email', 't@example.invalid'); sh('config', 'user.name', 't');
  writeFileSync(join(repo, 'a.mjs'), 'export const a = 1;\n'); sh('add', '.'); sh('commit', '-qm', 'base');
  sh('switch', '-qc', 'task/x');
  writeFileSync(join(repo, 'a.mjs'), 'export const a = 2;\nconst key = "sk-abcdefghijklmnopqrstuvwxyz";\n'); sh('commit', '-qam', 'Change a');
  const argsLog = join(root, 'args.txt');
  const fake = join(root, 'fake-pi.mjs');
  writeFileSync(fake, `#!/usr/bin/env node
import { appendFileSync, readFileSync } from 'node:fs';
const args = process.argv.slice(2);
appendFileSync(${JSON.stringify(argsLog)}, JSON.stringify(args) + '\\n');
const packet = readFileSync(args.find(a => a.startsWith('@')).slice(1), 'utf8');
if (packet.includes('sk-abc')) { console.log('LEAK'); process.exit(0); }
console.log(process.env.FAKE_REPORT);
`);
  chmodSync(fake, 0o755);
  const run = (report, extra = []) => spawnSync(process.execPath, [script, '--base', 'dev', ...extra], {
    cwd: repo, encoding: 'utf8', env: { ...process.env, MEGAI_REVIEW_PI: fake, FAKE_REPORT: report } });

  const ok = run('Risk: Low — small\n### none\nVerdict: ship', ['--fail-on', 'high']);
  assert.equal(ok.status, 0, ok.stderr);
  assert.match(ok.stdout, /Risk: Low; findings: 0 .*verdict: ship/);
  const args = JSON.parse(readFileSync(argsLog, 'utf8').trim().split('\n')[0]);
  for (const flag of ['-p', '--no-session', '--no-extensions', '--no-mcp', '--no-context-files']) assert.ok(args.includes(flag), flag);
  assert.equal(args[args.indexOf('--tools') + 1], 'read,grep,find,ls');
  assert.equal(args[args.indexOf('--model') + 1], 'openai/gpt-6.2-sol:high');
  const reportPath = ok.stdout.match(/report: (\S+)/)[1];
  assert.equal(statSync(reportPath).mode & 0o777, 0o600);

  const high = run('Risk: High — x\n### [high] Bug\nVerdict: fix first', ['--fail-on', 'high']);
  assert.equal(high.status, 3);
  assert.equal(run('garbage').status, 2, 'malformed report');
  assert.equal(run('x', ['--model', 'nope']).status, 2);
  assert.equal(spawnSync(process.execPath, [script, '--base', '--evil'], { cwd: repo, encoding: 'utf8' }).status, 2);
  const packetOnly = run('', ['--packet-only']);
  assert.equal(packetOnly.status, 0);
  const packet = readFileSync(packetOnly.stdout.match(/packet: (\S+)/)[1], 'utf8');
  assert.match(packet, /1 secret-looking diff lines were redacted/);
});

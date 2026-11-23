import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { chmodSync, existsSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';
import {
  LIMITS, READ_ONLY_TOOLS, atLeast, securityContextsFor, boundDiff, buildPacket, changeStack, modelListed, parseReport, redact, validModel, validRef,
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

test('review round: PEM blocks, goal and stat are redacted; packet has one hard bound; exact model match', () => {
  const pem = ['+-----BEGIN OPENSSH PRIVATE KEY-----', '+b3BlbnNzaC1rZXktdjEAAAAA', '+QUJDREVGR0hJSktMTU5P', '+-----END OPENSSH PRIVATE KEY-----', '+ok line'].join('\n');
  const r = redact(pem);
  assert.equal(r.count, 4); assert.ok(!/b3BlbnNz|QUJDREVG/.test(r.text)); assert.match(r.text, /ok line/);
  const mid = redact(['@@ -10,3 +10,3 @@', ' MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7VJTUt9Us8cKj', '-MIIEowIBAAKCAQEAu1SU1LfVLPHCozMxH2Mo4lgOEePzNm0tRgeLezV6ffAt0gun', '+Zm9vYmFyYmF6cXV4MTIzNDU2Nzg5MEFCQ0RFRkdISUpLTE1OT1BRUlNUVVZXWFla', ' 9b8c3f0a1d2e4f6a8b0c2d4e6f8a0b2c4d6e8f0a2b4c6d8e0f2a4b6c8d0e2f4a6'].join('\n'));
  assert.equal(mid.count, 3, 'key body without delimiters'); assert.match(mid.text, /9b8c3f0a/, 'hex hashes are kept');
  const p = buildPacket({ base: 'b', head: 'h', goal: 'deploy token = abcdefghijklmnopqrstuvwxyz0123', stat: ' x | 1', files: ['x'], diff: '', dirty: false });
  assert.ok(!p.text.includes('abcdefghijklmnop')); assert.equal(p.redacted, 1);
  const many = Array.from({ length: 5000 }, (_, i) => `src/${'deep/'.repeat(20)}file${i}.mjs`);
  const big = buildPacket({ base: 'b', head: 'h', goal: 'g', stat: many.map(f => ` ${f} | 1 +`).join('\n'), files: many, diff: '', dirty: false });
  assert.ok(big.text.length <= LIMITS.packet + 200, String(big.text.length));
  assert.match(big.text, /\+4960 more/);
  const secretPath = 'config/ghp_abcdefghijklmnopqrstuvwx.json';
  const pathPacket = buildPacket({ base: 'b', head: 'h', goal: 'g', stat: '', files: [secretPath, 'package-lock.json'], diff: fileDiff('package-lock.json', '+x') });
  assert.ok(!pathPacket.text.includes('ghp_abcdef'), 'paths in summaries are redacted');
  const order = boundDiff(fileDiff('a-docs.md', '+' + 'd'.repeat(300)) + fileDiff('z/schema.json', '+' + 's'.repeat(300)), { total: 450, perFile: 1000 });
  assert.match(order.text, /z\/schema\.json/); assert.match(order.skipped[0], /a-docs\.md/, 'contracts outrank docs under the budget');
  const listing = 'provider  model        context\nopenai    gpt-6.2-sol-mini  272K\nopenai    gpt-6.2-sol  272K\n';
  assert.ok(modelListed(listing, 'openai/gpt-6.2-sol:high'));
  assert.ok(!modelListed('openai    gpt-6.2-sol-mini  272K', 'openai/gpt-6.2-sol'), 'no fuzzy match');
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
  assert.match(p.text, /uncommitted changes are not part of it/);
  const f = (sev, title) => `### [${sev}] ${title}\n- Where: a.mjs:3\n- Scenario: x → y\n- Tests: none\n- Fix: z\n`;
  const report = `Risk: High — touches auth\n\n## Change stack\ncore\n\n## Blast radius\nnone\n\n## Findings\n${f('high', 'Fallback picks max probability')}${f('low', 'Naming')}Verdict: fix first\n`;
  const r = parseReport(report);
  assert.equal(r.risk, 'High'); assert.equal(r.verdict, 'fix first'); assert.equal(r.findings.length, 2); assert.ok(r.wellFormed);
  assert.ok(atLeast(r.findings, 'high')); assert.ok(!atLeast(r.findings, 'critical'));
  assert.equal(parseReport('### none\nVerdict: ship').wellFormed, false, 'missing risk line is malformed');
  const shell = body => `Risk: High — x\n## Change stack\na\n## Blast radius\nb\n## Findings\n${body}Verdict: fix first\n`;
  assert.equal(parseReport(shell('### High: Authorization bypass\n- Where: a\n')).wellFormed, false, 'misformatted heading never passes');
  assert.equal(parseReport(shell('### [high] No fields\n')).wellFormed, false, 'finding without fields');
  assert.equal(parseReport(shell('')).wellFormed, false, 'neither findings nor none');
  assert.equal(parseReport(shell(Array.from({ length: 9 }, (_, i) => f('low', 'n' + i)).join(''))).wellFormed, false, 'over 8 findings');
  assert.equal(parseReport(shell('### none\n')).wellFormed, true);
  assert.equal(parseReport(shell('### none\n') + '### [high] Hidden\n- Where: a\n- Scenario: b\n- Tests: c\n- Fix: d\n').wellFormed, false, 'nothing may follow the verdict');
  assert.equal(parseReport(shell('### none\n') + 'Verdict: ship\n').wellFormed, false, 'exactly one verdict');
  const indented = parseReport(shell('### none\n  ### [high] Indented\n- Where: a\n- Scenario: b\n- Tests: c\n- Fix: d\n'));
  assert.equal(indented.wellFormed, false, 'indented heading is still a heading'); assert.ok(atLeast(indented.findings, 'high'));
  assert.equal(parseReport('Risk: Low — x\n## Findings\n### none\nVerdict: ship').wellFormed, false, 'missing sections');
});

test('CLI runs a fresh read-only reviewer and maps findings to exit codes', t => {
  const root = mkdtempSync(join(tmpdir(), 'change-review-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const repo = join(root, 'repo');
  const sh = (...a) => execFileSync('git', a, { cwd: repo, encoding: 'utf8' });
  execFileSync('git', ['init', '-q', '-b', 'dev', repo]);
  sh('config', 'user.email', 't@example.invalid'); sh('config', 'user.name', 't');
  writeFileSync(join(repo, 'a.mjs'), 'export const a = 1;\n');
  execFileSync('mkdir', ['-p', join(repo, '.pi')]); writeFileSync(join(repo, '.pi', 'settings.json'), '{"packages":["npm:evil"]}\n');
  sh('add', '.'); sh('commit', '-qm', 'base');
  sh('switch', '-qc', 'task/x');
  writeFileSync(join(repo, 'a.mjs'), 'export const a = 2;\nconst key = "sk-abcdefghijklmnopqrstuvwxyz";\n'); sh('commit', '-qam', 'Change a');
  writeFileSync(join(repo, '.env'), 'SECRET=untracked\n');
  // A repo-configured textconv driver must never run while building the packet.
  const sentinel = join(root, 'textconv-ran');
  writeFileSync(join(repo, '.git', 'info', 'attributes'), '*.mjs diff=evil\n');
  sh('config', 'diff.evil.textconv', `sh -c 'touch ${sentinel}; cat "$0"'`);
  const argsLog = join(root, 'args.txt');
  const fake = join(root, 'fake-pi.mjs');
  writeFileSync(fake, `#!/usr/bin/env node
import { appendFileSync, existsSync, readFileSync } from 'node:fs';
const args = process.argv.slice(2);
appendFileSync(${JSON.stringify(argsLog)}, JSON.stringify(args) + '\\n');
if (args.includes('--list-models')) { console.log('provider  model        context\\nopenai    gpt-6.2-sol  272K'); process.exit(0); }
const packet = readFileSync(args.find(a => a.startsWith('@')).slice(1), 'utf8');
if (packet.includes('sk-abc')) { console.log('LEAK'); process.exit(0); }
if (existsSync('.env') || !existsSync('a.mjs') || !process.cwd().endsWith('/tree')) { console.log('NOT A CLEAN EXPORT'); process.exit(0); }
if (!/independent code reviewer/.test(readFileSync('.pi/APPEND_SYSTEM.md', 'utf8')) || !existsSync('_pi_from_commit/settings.json')) { console.log('NO REVIEW PROMPT'); process.exit(0); }
console.log(process.env.FAKE_REPORT);
`);
  chmodSync(fake, 0o755);
  const run = (report, extra = []) => spawnSync(process.execPath, [script, '--base', 'dev', ...extra], {
    cwd: repo, encoding: 'utf8', env: { ...process.env, MEGAI_REVIEW_PI: fake, FAKE_REPORT: report } });

  const shell = body => `Risk: Low — small\n## Change stack\na\n## Blast radius\nb\n## Findings\n${body}Verdict: ship\n`;
  const ok = run(shell('### none\n'), ['--fail-on', 'high']);
  assert.equal(ok.status, 0, ok.stderr);
  assert.match(ok.stdout, /Risk: Low; findings: 0 .*verdict: ship/);
  assert.equal(existsSync(sentinel), false, 'textconv did not run');
  const args = JSON.parse(readFileSync(argsLog, 'utf8').trim().split('\n').find(l => !l.includes('--list-models')));
  for (const flag of ['-p', '--no-session', '--no-extensions', '--no-mcp', '--no-context-files', '--no-skills', '--approve', '--offline']) assert.ok(args.includes(flag), flag);
  const listArgs = JSON.parse(readFileSync(argsLog, 'utf8').trim().split('\n').find(l => l.includes('--list-models')));
  for (const flag of ['--offline', '--no-extensions', '--no-mcp', '--approve']) assert.ok(listArgs.includes(flag), 'preflight isolated: ' + flag);
  assert.equal(args[args.indexOf('--tools') + 1], 'read,grep,find,ls');
  assert.equal(args[args.indexOf('--model') + 1], 'openai/gpt-6.2-sol:high');
  const reportPath = ok.stdout.match(/report: (\S+)/)[1];
  assert.equal(statSync(reportPath).mode & 0o777, 0o600);

  const high = run(shell('### [high] Bug\n- Where: a.mjs:1\n- Scenario: a → b\n- Tests: none\n- Fix: c\n'), ['--fail-on', 'high']);
  assert.equal(high.status, 3, high.stderr);
  assert.equal(run(shell('### High: Bug\n'), ['--fail-on', 'high']).status, 2, 'malformed high never passes the gate');
  assert.equal(run('x', ['--model', 'openai/gpt-6.2']).status, 2, 'model must be an exact catalog entry');
  assert.equal(run('garbage').status, 2, 'malformed report');
  assert.equal(run('x', ['--model', 'nope']).status, 2);
  assert.equal(spawnSync(process.execPath, [script, '--base', '--evil'], { cwd: repo, encoding: 'utf8' }).status, 2);
  writeFileSync(join(repo, 'SECURITY_CONTEXT.md'), '---\nschema_version: 1\n---\n## 4. Stop-and-Flag Rules\n- NEVER call evalUnsafe\n');
  sh('add', 'SECURITY_CONTEXT.md'); sh('commit', '-qm', 'Add security context');
  const packetOnly = run('', ['--packet-only']);
  assert.match(packetOnly.stdout, /security context files: 1/);
  assert.equal(packetOnly.status, 0);
  const packet = readFileSync(packetOnly.stdout.match(/packet: (\S+)/)[1], 'utf8');
  assert.match(packet, /1 secret-looking lines were redacted/);
  assert.match(packet, /NEVER call evalUnsafe/); assert.match(packet, /ADDED by this change/);
});

test('security context: root keeps a slot, base governs, head edits are labelled, bounded and redacted', () => {
  const tree = ['SECURITY_CONTEXT.md', 'a/SECURITY_CONTEXT.md', 'b/SECURITY_CONTEXT.md', 'c/SECURITY_CONTEXT.md', 'docs/SECURITY_CONTEXT.md.bak'];
  const pick = securityContextsFor(tree, ['a/x.ts', 'b/y.ts', 'c/z.ts']);
  assert.ok(pick.selected.includes('SECURITY_CONTEXT.md'), 'root never dropped'); assert.equal(pick.selected.length, 3); assert.equal(pick.omitted.length, 1);
  assert.deepEqual(securityContextsFor(['README.md'], ['README.md']), { selected: [], omitted: [] });
  const p = buildPacket({ base: 'b', head: 'h', goal: 'g', stat: '', files: ['a'], diff: '', securityOmitted: ['c/SECURITY_CONTEXT.md'],
    security: [{ path: 'SECURITY_CONTEXT.md', base: '- NEVER raw SQL\n', head: '- raw SQL is fine\napi_key = abcdefghijklmnopqrstuvwxyz\n' },
               { path: 'a/SECURITY_CONTEXT.md', base: null, head: 'new zone rules' },
               { path: 'b/SECURITY_CONTEXT.md', base: 'same', head: 'same' }] });
  assert.match(p.text, /SECURITY_CONTEXT\.md — approved \(base\)[\s\S]*NEVER raw SQL[\s\S]*proposed by this change \(head\)/);
  assert.match(p.text, /a\/SECURITY_CONTEXT\.md — ADDED by this change/);
  assert.match(p.text, /b\/SECURITY_CONTEXT\.md \(unchanged\)/);
  assert.match(p.text, /Not included for size \(read them yourself\): c\/SECURITY_CONTEXT\.md/);
  assert.ok(!p.text.includes('abcdefghijklmnop'), 'redacted');
  // Redaction expansion and headings are charged to the budget.
  const keyBody = ['-----BEGIN PRIVATE KEY-----', ...Array(3000).fill('x'), '-----END PRIVATE KEY-----'].join('\n');
  const big = buildPacket({ base: 'b', head: 'h', goal: 'g', stat: '', files: ['a'], diff: '', security: [{ path: 'SECURITY_CONTEXT.md', base: keyBody, head: keyBody }] });
  const sec = big.text.slice(big.text.indexOf('## Security context'), big.text.indexOf('## Change stack'));
  assert.ok(sec.length <= LIMITS.security + 200, String(sec.length));
  assert.doesNotMatch(buildPacket({ base: 'b', head: 'h', goal: 'g', stat: '', files: ['a'], diff: '' }).text, /## Security context \(project/);
});

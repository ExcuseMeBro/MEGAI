#!/usr/bin/env node
// Independent change review: builds a bounded packet from `git diff <base>...HEAD` and runs
// a fresh, read-only Pi reviewer on it. Usage (from the task worktree root):
//   node review.mjs [--base REF] [--model provider/id[:thinking]] [--goal-file PATH]
//                   [--fail-on low|medium|high|critical] [--packet-only] [--timeout-min N]
// Exit codes: 0 report written, 2 usage/setup error or malformed report, 3 findings at --fail-on.
import { execFileSync, spawn } from 'node:child_process';
import { lstatSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { DEFAULT_MODEL, LIMITS, READ_ONLY_TOOLS, atLeast, buildPacket, parseReport, validModel, validRef } from './review-core.mjs';

const fail = msg => { console.error(`review: ${msg}`); process.exit(2); };
const args = process.argv.slice(2);
const opt = { base: null, model: DEFAULT_MODEL, goalFile: null, failOn: null, packetOnly: false, timeoutMin: 15 };
for (let i = 0; i < args.length; i++) {
  const a = args[i], v = () => args[++i] ?? fail(`${a} needs a value`);
  if (a === '--base') opt.base = v();
  else if (a === '--model') opt.model = v();
  else if (a === '--goal-file') opt.goalFile = v();
  else if (a === '--fail-on') opt.failOn = v();
  else if (a === '--packet-only') opt.packetOnly = true;
  else if (a === '--timeout-min') opt.timeoutMin = Number(v());
  else fail(`unknown argument ${a}`);
}
if (!validModel(opt.model)) fail('invalid --model (use provider/id or provider/id:thinking)');
if (opt.failOn && !['low', 'medium', 'high', 'critical'].includes(opt.failOn)) fail('invalid --fail-on');
if (!(opt.timeoutMin >= 1 && opt.timeoutMin <= 60)) fail('--timeout-min must be 1..60');

const env = { ...process.env };
for (const k of ['GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR']) delete env[k];
const git = (...a) => execFileSync('git', a, { env, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
let root;
try { root = git('rev-parse', '--show-toplevel').trim(); } catch { fail('run from inside a Git worktree'); }
process.chdir(root);
const exists = ref => { try { git('rev-parse', '--verify', '--quiet', `${ref}^{commit}`); return true; } catch { return false; } };
const base = opt.base ?? ['origin/dev', 'dev', 'origin/main', 'main'].find(exists);
if (!base || !validRef(base) || !exists(base)) fail(`base ref not found or invalid: ${base ?? '(none)'}`);
const head = git('rev-parse', 'HEAD').trim();
const range = `${base}...HEAD`;
const files = git('diff', '--name-only', range).split('\n').filter(Boolean);
if (!files.length) fail(`no committed changes in ${range}`);
let goal = '';
if (opt.goalFile) {
  try {
    const st = lstatSync(opt.goalFile);
    if (!st.isFile() || st.size > LIMITS.context * 4) throw new Error();
    goal = readFileSync(opt.goalFile, 'utf8');
  } catch { fail('--goal-file must be a regular file under 32 KiB'); }
} else {
  goal = 'Commit messages:\n' + git('log', '--format=- %s%n%b', `${base}..HEAD`).slice(0, LIMITS.context);
}
const packet = buildPacket({
  base, head, goal, files,
  stat: git('diff', '--stat', range),
  diff: git('diff', '-U3', '--no-color', range),
  dirty: git('status', '--porcelain').trim().length > 0,
});
const dir = mkdtempSync(join(tmpdir(), 'megai-review-'));
const packetPath = join(dir, 'packet.md');
writeFileSync(packetPath, packet.text, { mode: 0o600 });
console.log(`packet: ${packetPath} (${packet.text.length} chars, ${files.length} files, ${packet.redacted} redacted lines, ${packet.skipped.length} not shown)`);
if (opt.packetOnly) process.exit(0);

const pi = process.env.MEGAI_REVIEW_PI || 'pi';
const piArgs = ['-p', '--no-session', '--no-extensions', '--no-skills', '--no-prompt-templates', '--no-context-files', '--no-mcp',
  '--tools', READ_ONLY_TOOLS, '--model', opt.model, `@${packetPath}`, 'Review this change now, in the required format.'];
const child = spawn(pi, piArgs, { cwd: root, env, stdio: ['ignore', 'pipe', 'pipe'] });
let out = '', err = '';
child.stdout.on('data', d => { if (out.length < 400_000) out += d; });
child.stderr.on('data', d => { if (err.length < 4000) err += d; });
const timer = setTimeout(() => child.kill('SIGTERM'), opt.timeoutMin * 60_000);
child.on('error', e => fail(`cannot start ${pi}: ${e.message}`));
child.on('close', code => {
  clearTimeout(timer);
  const reportPath = join(dir, 'report.md');
  writeFileSync(reportPath, out, { mode: 0o600 });
  const r = parseReport(out);
  const bySev = ['critical', 'high', 'medium', 'low'].map(s => `${s} ${r.findings.filter(f => f.severity === s).length}`).join(', ');
  console.log(`report: ${reportPath}`);
  console.log(`reviewer: ${opt.model} (fresh session, tools ${READ_ONLY_TOOLS}); base ${base}; head ${head}`);
  console.log(`Risk: ${r.risk ?? '?'}; findings: ${r.findings.length} (${bySev}); verdict: ${r.verdict ?? '?'}`);
  if (code !== 0 || !r.wellFormed) { console.error(`review: reviewer exited ${code}; report ${r.wellFormed ? 'ok' : 'malformed'}. ${err.trim().slice(0, 500)}`); process.exit(2); }
  if (opt.failOn && atLeast(r.findings, opt.failOn)) process.exit(3);
  process.exit(0);
});

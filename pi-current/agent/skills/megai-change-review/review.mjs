#!/usr/bin/env node
// Independent change review: builds a bounded packet from `git diff <base>...HEAD` and runs
// a fresh, read-only Pi reviewer on it. Usage (from the task worktree root):
//   node review.mjs [--base REF] [--model provider/id[:thinking]] [--goal-file PATH]
//                   [--fail-on low|medium|high|critical] [--packet-only] [--timeout-min N]
// Exit codes: 0 report written, 2 usage/setup error or malformed report, 3 findings at --fail-on.
import { execFileSync, spawn } from 'node:child_process';
import { rmSync } from 'node:fs';
import { existsSync, lstatSync, mkdirSync, mkdtempSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { DEFAULT_MODEL, LIMITS, READ_ONLY_TOOLS, REVIEWER_SYSTEM, atLeast, buildPacket, modelListed, parseReport, securityContextsFor, validModel, validRef } from './review-core.mjs';

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
env.GIT_OPTIONAL_LOCKS = '0';
env.GIT_NO_LAZY_FETCH = '1'; // a partial clone must not contact its promisor remote while we read
// Never let an uncaught error print captured Git output (it may hold unredacted diff text).
process.on('uncaughtException', e => { console.error(`review: ${String(e?.message ?? e).split('\n')[0].slice(0, 200)}`); process.exit(2); });
// No repo-configured helpers (external diff, textconv, fsmonitor) run while building the packet.
const git = (...a) => execFileSync('git', ['-c', 'core.fsmonitor=false', '-c', 'diff.external=', ...a], { env, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
let root;
try { root = git('rev-parse', '--show-toplevel').trim(); } catch { fail('run from inside a Git worktree'); }
process.chdir(root);
const exists = ref => { try { git('rev-parse', '--verify', '--quiet', `${ref}^{commit}`); return true; } catch { return false; } };
const base = opt.base ?? ['origin/dev', 'dev', 'origin/main', 'main'].find(exists);
if (!base || !validRef(base) || !exists(base)) fail(`base ref not found or invalid: ${base ?? '(none)'}`);
// Pin both ends once so every later read describes the same snapshot.
const head = git('rev-parse', '--verify', 'HEAD^{commit}').trim();
const baseSha = git('rev-parse', '--verify', `${base}^{commit}`).trim();
const range = `${baseSha}...${head}`;
const NOHELPERS = ['--no-ext-diff', '--no-textconv'];
const files = git('diff', ...NOHELPERS, '--name-only', range).split('\n').filter(Boolean);
if (!files.length) fail(`no committed changes in ${range}`);
let goal = '';
if (opt.goalFile) {
  try {
    const st = lstatSync(opt.goalFile);
    if (!st.isFile() || st.size > LIMITS.context * 4) throw new Error();
    goal = readFileSync(opt.goalFile, 'utf8');
  } catch { fail('--goal-file must be a regular file under 32 KiB'); }
} else {
  goal = 'Commit messages:\n' + git('log', '--format=- %s%n%b', `${baseSha}..${head}`).slice(0, LIMITS.context);
}
// SECURITY_CONTEXT.md files from the pinned head (blob reads: no checkout, no filters).
const treePaths = git('ls-tree', '-r', '--name-only', head).split('\n').filter(Boolean);
const security = securityContextsFor(treePaths, files).map(path => {
  try { return { path, text: git('cat-file', 'blob', `${head}:${path}`) }; } catch { return null; }
}).filter(Boolean);
const packet = buildPacket({ security,
  base: `${base} (${baseSha.slice(0, 12)})`, head, goal, files,
  stat: git('diff', ...NOHELPERS, '--stat', range),
  diff: git('diff', ...NOHELPERS, '-U3', '--no-color', range),
});
const dir = mkdtempSync(join(tmpdir(), 'megai-review-'));
const packetPath = join(dir, 'packet.md');
writeFileSync(packetPath, packet.text, { mode: 0o600 });
console.log(`packet: ${packetPath} (${packet.text.length} chars, ${files.length} files, ${packet.redacted} redacted lines, ${packet.skipped.length} not shown${packet.security.length ? `, security context: ${packet.security.join(', ')}` : ''})`);
if (opt.packetOnly) process.exit(0);

const pi = process.env.MEGAI_REVIEW_PI || 'pi';
// The reviewer sees a clean export of the pinned commit, not the live worktree (no untracked or ignored files).
const tree = join(dir, 'tree');
execFileSync('/bin/sh', ['-c', 'mkdir -p "$1" && git -c core.fsmonitor=false archive --format=tar "$2" | tar -x -C "$1"', 'sh', tree, head], { cwd: root, env, stdio: ['ignore', 'ignore', 'pipe'] });
// Project-local .pi from the commit is kept readable but inert; our own .pi/APPEND_SYSTEM.md replaces the
// author's global one (Pi uses the trusted project file instead of the agent-dir file), so no author rules leak in.
if (existsSync(join(tree, '.pi'))) renameSync(join(tree, '.pi'), join(tree, '_pi_from_commit'));
mkdirSync(join(tree, '.pi'), { mode: 0o700 });
writeFileSync(join(tree, '.pi', 'APPEND_SYSTEM.md'), REVIEWER_SYSTEM, { mode: 0o600 });
const isolation = ['--offline', '--approve', '--no-extensions', '--no-skills', '--no-prompt-templates', '--no-context-files', '--no-mcp'];
// The model must exist exactly, checked with the same isolation; never let a fuzzy pattern pick another reviewer.
let listing;
try { listing = execFileSync(pi, [...isolation, '--list-models', opt.model.split(':')[0].split('/')[1]], { cwd: tree, env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], timeout: 30_000 }); }
catch { fail(`\`${pi} --list-models\` failed`); }
if (!modelListed(listing, opt.model)) fail(`model ${opt.model} is not an exact entry in \`${pi} --list-models\``);
const piArgs = ['-p', '--no-session', ...isolation, '--tools', READ_ONLY_TOOLS, '--model', opt.model, `@${packetPath}`, 'Review this change now, in the required format.'];
const child = spawn(pi, piArgs, { cwd: tree, env, stdio: ['ignore', 'pipe', 'pipe'] });
let out = '', err = '';
child.stdout.on('data', d => { if (out.length < 400_000) out += d; });
child.stderr.on('data', d => { if (err.length < 4000) err += d; });
const timer = setTimeout(() => child.kill('SIGTERM'), opt.timeoutMin * 60_000);
child.on('error', e => fail(`cannot start ${pi}: ${e.message}`));
child.on('close', code => {
  clearTimeout(timer);
  try { rmSync(tree, { recursive: true, force: true }); } catch { /* temp */ }
  const reportPath = join(dir, 'report.md');
  writeFileSync(reportPath, out, { mode: 0o600 });
  const r = parseReport(out);
  const bySev = ['critical', 'high', 'medium', 'low'].map(s => `${s} ${r.findings.filter(f => f.severity === s).length}`).join(', ');
  console.log(`report: ${reportPath}`);
  console.log(`reviewer: ${opt.model} (fresh session, tools ${READ_ONLY_TOOLS}); base ${base}; head ${head}`);
  console.log(`Risk: ${r.risk ?? '?'}; findings: ${r.findings.length} (${bySev}); verdict: ${r.verdict ?? '?'}`);
  if (code !== 0 || !r.wellFormed) { console.error(`review: reviewer exited ${code}; report ${r.wellFormed ? 'ok' : `malformed (${r.problems.slice(0, 3).join('; ') || 'missing risk, sections or verdict'})`}.`); process.exit(2); }
  if (opt.failOn && atLeast(r.findings, opt.failOn)) process.exit(3);
  process.exit(0);
});

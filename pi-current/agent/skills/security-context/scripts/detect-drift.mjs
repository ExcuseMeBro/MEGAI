#!/usr/bin/env node
/**
 * Detects security-context drift since `last_synced_commit` recorded in SECURITY_CONTEXT.md.
 * Exit code:
 *   0 = up to date (no security-relevant drift)
 *   2 = drift detected (sync recommended)
 *   1 = missing or malformed SECURITY_CONTEXT.md
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const cwd = process.argv[2] ? path.resolve(process.argv[2]) : process.cwd();
const contextPath = path.join(cwd, 'SECURITY_CONTEXT.md');

// MEGAI patch: bounded reads of regular files only (no symlinks, FIFOs or huge files).
function readSmall(file) {
  let st;
  try { st = fs.lstatSync(file); } catch { return null; }
  if (!st.isFile() || st.size > 1024 * 1024) { console.error(JSON.stringify({ status: 'invalid', message: `${path.basename(file)} must be a regular file under 1 MiB` })); process.exit(1); }
  const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
  try { if (!fs.fstatSync(fd).isFile()) process.exit(1); return fs.readFileSync(fd, 'utf8'); } finally { fs.closeSync(fd); }
}
// MEGAI patch: never let a partial clone fetch objects; this check is read-only.
process.env.GIT_NO_LAZY_FETCH = '1';

const raw = readSmall(contextPath);
if (raw == null) {
  console.error(JSON.stringify({ status: 'missing', message: 'SECURITY_CONTEXT.md not found' }));
  process.exit(1);
}
const fmMatch = raw.match(/^---\r?\n([\s\S]*?)\r?\n---/);
if (!fmMatch) {
  console.error(JSON.stringify({ status: 'invalid', message: 'Missing YAML frontmatter' }));
  process.exit(1);
}

const fm = fmMatch[1];
const shaMatch = fm.match(/^last_synced_commit:\s*["']?([^"'\s]+)["']?/m);
const lastSha = shaMatch ? shaMatch[1] : null;
// MEGAI patch: required fields must be present and valid before any git call.
if (!/^schema_version:\s*1\s*(#.*)?$/m.test(fm) || !/^visibility:\s*(private|public)\s*(#.*)?$/m.test(fm) || !lastSha) {
  console.error(JSON.stringify({ status: 'invalid', message: 'Frontmatter needs schema_version: 1, visibility: private|public and last_synced_commit' }));
  process.exit(1);
}
// MEGAI patch: only a full commit hash or "uncommitted" may reach git (an option-shaped value could make git write files).
if (lastSha && !/^([0-9a-f]{40}|[0-9a-f]{64}|uncommitted)$/.test(lastSha)) {
  console.error(JSON.stringify({ status: 'invalid', message: 'last_synced_commit must be a full commit hash or "uncommitted"' }));
  process.exit(1);
}

// Extract security-relevant file paths & globs from SECURITY_CONTEXT.md body and AGENTS.md pointer block
const rootFiles = new Set();
function extractPathGlobs(text) {
  const globs = new Set();
  const backticks = text.matchAll(/`([^`\n]+)`/g);
  for (const m of backticks) {
    const token = m[1].trim().replace(/^\.\//, '');
    if (!token || token.includes(' ')) continue;
    // MEGAI patch: root-level files count when they are tracked (checked below), e.g. `middleware.ts`.
    if (!token.includes('/')) { if (/^[\w.-]+\.[A-Za-z0-9]+$/.test(token)) rootFiles.add(token); continue; }
    if (/^(https?:|mailto:|\/api\/)/.test(token)) continue;
    if (/^[a-zA-Z0-9._*@{},/-]+$/.test(token)) {
      globs.add(token);
    }
  }
  return [...globs];
}

const body = raw.slice(fmMatch[0].length);
const agentsPath = path.join(cwd, 'AGENTS.md');
let pointerBlock = '';
const agentsRaw = readSmall(agentsPath);
if (agentsRaw != null) {
  const secMatch = agentsRaw.match(/(?:^|\n)#{1,6}\s+Security Context[^\n]*\n([\s\S]*?)(?=\n#{1,6}\s|$)/i);
  if (secMatch) {
    pointerBlock = secMatch[1];
  } else {
    pointerBlock = agentsRaw
      .split(/\n{2,}/)
      .filter((p) => p.includes('SECURITY_CONTEXT.md'))
      .join('\n');
  }
}
const watchedPaths = [...new Set([...extractPathGlobs(body), ...extractPathGlobs(pointerBlock)])];
try {
  const tracked = new Set(execFileSync('git', ['-c', 'core.quotePath=false', 'ls-files', '-z'], { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], maxBuffer: 64 * 1024 * 1024 }).split('\0'));
  for (const f of rootFiles) if (tracked.has(f)) watchedPaths.push(f);
} catch { /* no git: handled below */ }

// MEGAI patch: one pass, so "**" is never rewritten by the single-star rule.
function globToRegex(glob) {
  let out = '';
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i];
    if (c === '*' && glob[i + 1] === '*') {
      if (glob[i + 2] === '/') { out += '(?:.*/)?'; i += 2; } else { out += '.*'; i += 1; }
    } else if (c === '*') out += '[^/]*';
    else out += c.replace(/[.+^${}()|[\]\\?]/g, '\\$&');
  }
  return new RegExp(`^${out}$`);
}

function git(args) {
  return execFileSync('git', args, { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
}

let headSha = 'uncommitted';
try {
  headSha = git(['rev-parse', '--verify', 'HEAD^{commit}']);
} catch {
  // MEGAI patch: unreadable history is not a clean result.
  console.error(JSON.stringify({ status: 'no_git_history', lastSha }));
  process.exit(1);
}

if (!lastSha || lastSha === 'uncommitted') {
  console.log(JSON.stringify({ status: 'drift', reason: 'unrecorded_commit', headSha, changedFiles: [] }));
  process.exit(2);
}

let changedFiles = [];
try {
  git(['rev-parse', '--verify', '--quiet', `${lastSha}^{commit}`]);
  // NUL-separated, unquoted names; no rename pairing, so both the old and the new path count.
  const diffOut = execFileSync('git', ['-c', 'core.quotePath=false', 'diff', '--no-ext-diff', '--no-textconv', '--no-renames', '--relative', '--name-only', '-z', lastSha, headSha, '--'],
    { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], maxBuffer: 64 * 1024 * 1024 });
  changedFiles = diffOut.split('\0').filter(Boolean);
} catch {
  console.log(JSON.stringify({ status: 'drift', reason: 'unknown_last_commit', lastSha, headSha }));
  process.exit(2);
}

const manifestRegex = /(package\.json|pyproject\.toml|requirements.*\.txt|go\.mod|Cargo\.toml|Dockerfile|docker-compose|terraform|\.github\/workflows)/i;
const watchedRegexes = watchedPaths.map(globToRegex);

const securityRelevantChanges = changedFiles.filter(
  (file) => manifestRegex.test(file) || watchedRegexes.some((rx) => rx.test(file))
);

if (securityRelevantChanges.length > 0) {
  console.log(
    JSON.stringify({
      status: 'drift',
      lastSha,
      headSha,
      totalChanged: changedFiles.length,
      securityRelevantChanges,
    })
  );
  process.exit(2);
}

console.log(
  JSON.stringify({
    status: 'clean',
    lastSha,
    headSha,
    totalChanged: changedFiles.length,
    securityRelevantChanges: [],
  })
);
process.exit(0);

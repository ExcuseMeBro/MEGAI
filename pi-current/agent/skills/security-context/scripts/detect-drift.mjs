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

if (!fs.existsSync(contextPath)) {
  console.error(JSON.stringify({ status: 'missing', message: 'SECURITY_CONTEXT.md not found' }));
  process.exit(1);
}

const raw = fs.readFileSync(contextPath, 'utf8');
const fmMatch = raw.match(/^---\n([\s\S]*?)\n---/);
if (!fmMatch) {
  console.error(JSON.stringify({ status: 'invalid', message: 'Missing YAML frontmatter' }));
  process.exit(1);
}

const fm = fmMatch[1];
const shaMatch = fm.match(/^last_synced_commit:\s*["']?([^"'\s]+)["']?/m);
const lastSha = shaMatch ? shaMatch[1] : null;

// Extract security-relevant file paths & globs from SECURITY_CONTEXT.md body and AGENTS.md pointer block
function extractPathGlobs(text) {
  const globs = new Set();
  const backticks = text.matchAll(/`([^`\n]+)`/g);
  for (const m of backticks) {
    const token = m[1].trim().replace(/^\.\//, '');
    if (!token || token.includes(' ') || !token.includes('/')) continue;
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
if (fs.existsSync(agentsPath)) {
  const agentsRaw = fs.readFileSync(agentsPath, 'utf8');
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

function globToRegex(glob) {
  const escaped = glob
    .replace(/[.+^${}()|[\]\\]/g, '\\$&')
    .replace(/\*\*\//g, '(?:.*/)?')
    .replace(/\*\*/g, '.*')
    .replace(/\*/g, '[^/]*');
  return new RegExp(`^${escaped}$`);
}

function git(args) {
  return execFileSync('git', args, { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
}

let headSha = 'uncommitted';
try {
  headSha = git(['rev-parse', 'HEAD']);
} catch {
  console.log(JSON.stringify({ status: 'no_git_commits', lastSha, headSha }));
  process.exit(0);
}

if (!lastSha || lastSha === 'uncommitted') {
  console.log(JSON.stringify({ status: 'drift', reason: 'unrecorded_commit', headSha, changedFiles: [] }));
  process.exit(2);
}

let changedFiles = [];
try {
  const diffOut = git(['diff', '--name-only', `${lastSha}..HEAD`]);
  changedFiles = diffOut ? diffOut.split('\n').filter(Boolean) : [];
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

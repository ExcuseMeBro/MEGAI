#!/usr/bin/env node
// Scan a worktree through the guard, parse the complete JSON report locally, and print a short triage list:
// files with secret findings (rule, file, line only; never opened), and the other findings in changed files, with any
// finding in a secret-holding file marked unverified. Incomplete or failed scans exit 3 ("scan: unavailable").
// Usage: node triage.mjs <worktree> [--base REF] [--all]
import { execFileSync, spawnSync } from 'node:child_process';
import { homedir } from 'node:os';
import { join, resolve } from 'node:path';

const args = process.argv.slice(2);
const root = resolve(args[0] ?? '.');
const base = args.includes('--base') ? args[args.indexOf('--base') + 1] : null;
const all = args.includes('--all');
const unavailable = why => { console.log(`scan: unavailable (${why})`); process.exit(3); };
if (base && !/^[A-Za-z0-9][A-Za-z0-9._\/-]{0,99}$/.test(base)) unavailable('invalid --base');

const guard = process.env.SAFE_ANYTHING_GUARD || join(homedir(), '.local/bin/safe-anything');
const scan = spawnSync('/bin/bash', [guard, root, '--offline', '--json', '--severity', 'medium', '--fail-on', 'never'],
  { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
if (scan.status !== 0) unavailable(`guard exit ${scan.status}`);
let report;
try { report = JSON.parse(scan.stdout); } catch { unavailable('report is not valid JSON'); }
if (!Array.isArray(report?.findings)) unavailable('report has no findings list');

let changed = null;
if (base && !all) {
  try {
    changed = new Set(execFileSync('git', ['-c', 'core.quotePath=false', 'diff', '--no-ext-diff', '--no-textconv', '--no-renames', '--name-only', '-z', `${base}...HEAD`],
      { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).split('\0').filter(Boolean));
  } catch { unavailable('cannot list changed files'); }
}
const rel = p => String(p ?? '').replace(/^\.\//, '');
const findings = report.findings.map(f => ({ ...f, path: rel(f.path) }));
const secretFiles = new Set(findings.filter(f => String(f.rule).startsWith('secret.')).map(f => f.path));
const inScope = f => !changed || changed.has(f.path);

const secrets = findings.filter(f => String(f.rule).startsWith('secret.') && inScope(f));
const others = findings.filter(f => !String(f.rule).startsWith('secret.') && inScope(f));
console.log(`scan: ${findings.length} findings (medium+, offline)${changed ? `; ${changed.size} changed files in scope` : ''}`);
if (secrets.length) {
  console.log('SECRET findings - do not open these files; rotate if real:');
  for (const f of secrets) console.log(`  ${f.severity} ${f.rule} ${f.path}:${f.line}`);
}
if (others.length) {
  console.log('Other findings - open the line and judge real or false positive:');
  for (const f of others) console.log(`  ${f.severity} ${f.rule} ${f.path}:${f.line}${secretFiles.has(f.path) ? '  [unverified: file holds a flagged secret, do not open]' : ` - ${String(f.message ?? '').slice(0, 160)}`}`);
}
if (!secrets.length && !others.length) console.log('No findings in scope. (A clean scan is not proof of safety.)');

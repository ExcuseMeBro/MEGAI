// Counter-metric for autonomous delivery: before a push to `dev`, look at the pushed
// commits and refuse when they reach "green" by weakening tests (skips, focus markers,
// deleted test files, dropped assertions, non-blocking CI), unless a commit explains
// the change with a `Test-Change: <reason>` trailer. Pure parsing plus git reads; no writes.
import { execFileSync } from 'node:child_process';
import { existsSync, statSync } from 'node:fs';
import { homedir } from 'node:os';
import { isAbsolute, resolve } from 'node:path';

export const TRAILER = /^Test-Change:\s*\S.{3,}$/im;
const PROTECTED_TARGET = /^(?:dev)$/;
const PREFIX = new Set(['command', 'exec', 'time', 'env', 'nohup', 'then', 'do', 'else']);
const MAX_DIFF = 8 * 1024 * 1024;

const TEST_PATH = /(?:^|\/)(?:tests?|__tests__|specs?|integration_tests|androidTest|testFixtures)\/|(?:^|\/)test_[^/]+\.py$|[._-](?:test|spec)s?\.[cm]?[jt]sx?$|_test\.(?:go|py|rb|exs?|dart)$|_spec\.rb$|Tests?\.(?:java|kt|swift|cs|scala)$|(?:^|\/)conftest\.py$/i;
const DOC_PATH = /\.(?:md|mdx|markdown|rst|adoc|txt)$/i;
const CI_PATH = /(?:^|\/)(?:\.github\/workflows\/[^/]+\.ya?ml|\.gitlab-ci\.ya?ml|\.circleci\/config\.ya?ml|azure-pipelines\.ya?ml|Jenkinsfile|bitbucket-pipelines\.ya?ml)$/;

// Added lines that disable or narrow tests.
const SKIP_MARKERS = [
  [/\b(?:it|test|describe|context|suite)\.(?:skip|only|todo)\s*\(/, 'skip/only marker'],
  [/(?:^|[^\w.])(?:xit|xtest|xdescribe|fit|fdescribe)\s*\(/, 'skip/focus marker'],
  [/@pytest\.mark\.(?:skip|skipif|xfail)\b|\bpytest\.(?:skip|xfail)\s*\(|@unittest\.(?:skip|expectedFailure)\w*|\bself\.skipTest\s*\(/, 'pytest/unittest skip or xfail'],
  [/\bt\.Skip(?:f|Now)?\s*\(/, 'Go t.Skip'],
  [/#\[ignore\b/, 'Rust #[ignore]'],
  [/@(?:Disabled|Ignore)\b/, 'JUnit @Disabled/@Ignore'],
  [/\bskip:\s*(?:true|['"])/, 'skip: option'],
  [/\bXCTSkip\w*\s*\(/, 'XCTSkip'],
];
// A skip gated on the environment ("DSN not set", "pwsh not installed", platform-only)
// is how integration tests stay runnable everywhere; it is not a weakened test.
const ENV_GATE = /skip(?:if|unless)\b|\bskipIf\b|not (?:set|installed|available|configured|found)|unset|unavailable|\brequire[sd]?\b|only on|platform|darwin|linux|windows|win32|\benv\b|getenv|environ|_DSN|_URL|_KEY|_TOKEN|which\(|consent|explicit/i;
// `test.skip(condition, reason)`: Playwright's conditional form.
const CONDITIONAL_SKIP = /\b(?:test|it|describe)\.skip\s*\([^'"`)]/;
const ASSERTION = /\b(?:assert\w*|expect\s*\(|XCTAssert\w*|require\.\w+\(|t\.(?:Error|Errorf|Fatal|Fatalf)\(|should\.|\.to(?:Be|Equal|Match|Throw|Have)\w*\()/;
const CI_WEAKENING = [
  [/continue-on-error:\s*true/, 'continue-on-error: true'],
  [/allow_failure:\s*true/, 'allow_failure: true'],
  [/\b(?:test|tests|pytest|jest|vitest|mocha|go test|cargo test|gradle\w*|mvn|lint|tsc)\b[^#\n]*\|\|\s*(?:true|exit 0|:)\b/, 'test command made non-blocking (|| true)'],
  [/--passWithNoTests\b/, '--passWithNoTests'],
];

/** Split a unified diff into per-file added/removed lines. */
export function parseDiff(diff) {
  const files = [];
  let file;
  for (const line of String(diff).split('\n')) {
    if (line.startsWith('diff --git ')) {
      const m = / b\/(.+)$/.exec(line);
      file = { path: m ? m[1] : '', added: [], removed: [], deleted: false, created: false };
      files.push(file);
    } else if (!file) continue;
    else if (line.startsWith('deleted file mode')) file.deleted = true;
    else if (line.startsWith('new file mode')) file.created = true;
    else if (line.startsWith('+++') || line.startsWith('---')) continue;
    else if (line.startsWith('+')) file.added.push(line.slice(1));
    else if (line.startsWith('-')) file.removed.push(line.slice(1));
  }
  return files;
}

/** Findings for a diff; empty when it does not weaken tests. */
export function findWeakening(diff) {
  const findings = [];
  const files = parseDiff(diff);
  const isTest = (f) => TEST_PATH.test(f.path) && !DOC_PATH.test(f.path);
  // Removing a feature removes its tests too: deleted tests count only when no
  // non-test source was deleted in the same range.
  const featureRemoved = files.some((f) => f.deleted && !isTest(f) && !DOC_PATH.test(f.path));
  for (const f of files) {
    const test = isTest(f);
    if (f.deleted) {
      if (test && !featureRemoved) findings.push(`${f.path}: test file deleted`);
      continue;
    }
    // Markers count only in existing test files; a new test file may gate itself on the environment.
    // Rust keeps unit tests inside source files, so its #[ignore] counts in any .rs file.
    for (const line of (test || /\.rs$/.test(f.path)) && !f.created ? f.added : []) {
      if (ENV_GATE.test(line) || CONDITIONAL_SKIP.test(line)) continue;
      for (const [re, label] of SKIP_MARKERS) {
        if (re.test(line)) { findings.push(`${f.path}: ${label}: ${line.trim().slice(0, 120)}`); break; }
      }
    }
    for (const line of f.added) {
      if (CI_PATH.test(f.path) || /(?:^|\/)package\.json$/.test(f.path)) {
        for (const [re, label] of CI_WEAKENING) {
          if (re.test(line)) { findings.push(`${f.path}: ${label}`); break; }
        }
      }
    }
    if (test) {
      // Rewritten tests keep most of their checks; flag only a clear net loss.
      const removed = f.removed.filter((l) => ASSERTION.test(l)).length;
      const added = f.added.filter((l) => ASSERTION.test(l)).length;
      if (removed - added >= 5 && added * 4 <= removed) findings.push(`${f.path}: ${removed - added} assertions removed`);
    }
  }
  return [...new Set(findings)];
}

// ---- command parsing -------------------------------------------------------

const unquote = (s) => s.replace(/^(['"])(.*)\1$/, '$2');
const tokens = (segment) => (segment.match(/"[^"]*"|'[^']*'|\S+/g) ?? []).map(unquote);

/**
 * Pushes to `dev` in a shell command, with the directory each runs in.
 * @returns {{ dir: string|null, remote: string, src: string, dst: string }[]}
 */
export function findDevPushes(command, cwd) {
  const pushes = [];
  let dir = cwd;
  // Heredoc bodies and quoted strings are data; strip heredocs before splitting.
  const text = String(command).replace(/<<-?\s*['"]?(\w+)['"]?[\s\S]*?\n\1\b/g, ' ');
  for (const raw of text.split(/&&|\|\||;|\n|\|/)) {
    const words = tokens(raw.trim().replace(/^[({\s]+|[)}\s]+$/g, ''));
    if (!words.length) continue;
    if (words[0] === 'cd' && words[1]) { dir = resolveDir(words[1], dir); continue; }
    // `git` must be the command itself (after env assignments or a wrapper), not an argument.
    let i = 0;
    while (i < words.length && (/^\w+=/.test(words[i]) || PREFIX.has(words[i]))) i++;
    if (words[i] !== 'git' && !words[i]?.endsWith('/git')) continue;
    let gitDir = dir;
    i++;
    while (i < words.length && words[i].startsWith('-')) {
      if (words[i] === '-C') { gitDir = resolveDir(words[i + 1] ?? '', gitDir); i += 2; }
      else if (words[i] === '-c') i += 2;
      else i++;
    }
    if (words[i] !== 'push') continue;
    const rest = words.slice(i + 1);
    if (rest.some((w) => w === '--delete' || w === '-d')) continue;
    const args = rest.filter((w) => !w.startsWith('-'));
    const remote = args[0] ?? 'origin';
    const specs = args.slice(1);
    if (!specs.length) {
      // `git push` / `git push origin`: the current branch.
      pushes.push({ dir: gitDir, remote, src: 'HEAD', dst: '@current' });
      continue;
    }
    for (const spec of specs) {
      const clean = spec.replace(/^\+/, '');
      const [src, dstRaw] = clean.includes(':') ? clean.split(':', 2) : [clean, clean];
      const dst = dstRaw.replace(/^refs\/heads\//, '');
      if (PROTECTED_TARGET.test(dst) && src) pushes.push({ dir: gitDir, remote, src, dst });
    }
  }
  return pushes;
}

// ---- ipython cells ------------------------------------------------------

/** Python string literals in a cell (comments skipped, escapes decoded), in source order. */
function pythonStrings(code) {
  const out = [];
  const n = code.length;
  let i = 0;
  while (i < n) {
    const ch = code[i];
    if (ch === '#') { while (i < n && code[i] !== '\n') i++; continue; }
    if (ch !== "'" && ch !== '"') { i++; continue; }
    let p = i;
    while (p > 0 && p > i - 2 && /[rRbBuUfF]/.test(code[p - 1])) p--;
    if (p > 0 && /\w/.test(code[p - 1])) p = i; // part of an identifier, not a prefix
    const raw = code.slice(p, i).toLowerCase().includes('r');
    const q = code.startsWith(ch.repeat(3), i) ? ch.repeat(3) : ch;
    let j = i + q.length;
    let text = '';
    while (j < n && !code.startsWith(q, j)) {
      if (q.length === 1 && code[j] === '\n') break;
      if (code[j] === '\\' && j + 1 < n) {
        const e = code[j + 1];
        text += raw ? code[j] + e : ({ n: '\n', t: '\t', '\\': '\\', "'": "'", '"': '"', '\n': '' }[e] ?? code[j] + e);
        j += 2;
        continue;
      }
      text += code[j++];
    }
    out.push({ start: p, end: Math.min(n, j + q.length), text });
    i = j + q.length;
  }
  return out;
}

/**
 * Shell commands visible in a Pi `ipython` cell: every string literal (bash('…'),
 * os.system('…'), subprocess.run('…', shell=True)) and literal argv lists
 * (subprocess.run(["git", "push", "origin", "dev"])). Computed strings are not visible.
 * @returns {string[]}
 */
export function cellCommands(code) {
  const strings = pythonStrings(String(code ?? ''));
  const commands = new Set(strings.map((s) => s.text).filter((t) => t.trim()));
  let masked = '';
  let last = 0;
  strings.forEach((s, k) => { masked += code.slice(last, s.start) + `\u0001${k}\u0001`; last = s.end; });
  masked += code.slice(last);
  const lit = '\u0001(\\d+)\u0001';
  const list = new RegExp(`[\\[(]\\s*(${lit}(?:\\s*,\\s*${lit})+)\\s*,?\\s*[\\])]`, 'g');
  for (const m of masked.matchAll(list)) {
    const argv = [...m[1].matchAll(new RegExp(lit, 'g'))].map((x) => strings[Number(x[1])].text);
    commands.add(argv.map((a) => (/^[\w@%+=:,./-]+$/.test(a) ? a : `'${a.replace(/'/g, "'\\''")}'`)).join(' '));
  }
  return [...commands];
}

/** Shell commands a Pi tool call runs: a bash command, or the commands visible in an ipython cell. */
export function toolCommands(event) {
  if (event?.toolName === 'bash') return [String(event.input?.command ?? '')];
  if (event?.toolName === 'ipython') return cellCommands(String(event.input?.code ?? ''));
  return [];
}

function resolveDir(path, base) {
  if (!path || base === null) return null;
  if (/[$`*?]|\$\(/.test(path)) return null; // Unresolvable: variables, globs, substitutions.
  const expanded = path === '~' ? homedir() : path.startsWith('~/') ? resolve(homedir(), path.slice(2)) : path;
  return isAbsolute(expanded) ? expanded : resolve(base, expanded);
}

// ---- git ------------------------------------------------------------------

function git(dir, args) {
  return execFileSync('git', ['-C', dir, ...args], {
    encoding: 'utf8', timeout: 15_000, maxBuffer: MAX_DIFF, stdio: ['ignore', 'pipe', 'ignore'],
    env: { ...process.env, GIT_TERMINAL_PROMPT: '0' },
  });
}

/**
 * Check one push. Returns findings to block on, or [] to allow.
 * Any git problem (unknown ref, no repo) allows the push: this is a guard, not a gate.
 */
// The pushed range as [base, head] commits, or undefined when it cannot be read.
function pushedRange(push) {
  if (!push.dir || !existsSync(push.dir) || !statSync(push.dir).isDirectory()) return undefined;
  let { src, dst } = push;
  if (dst === '@current') {
    dst = git(push.dir, ['rev-parse', '--abbrev-ref', 'HEAD']).trim();
    if (!PROTECTED_TARGET.test(dst)) return undefined;
  }
  const head = git(push.dir, ['rev-parse', '--verify', '--quiet', `${src}^{commit}`]).trim();
  const base = git(push.dir, ['rev-parse', '--verify', '--quiet', `refs/remotes/${push.remote}/${dst}^{commit}`]).trim();
  if (!head || !base || head === base) return undefined;
  return [base, head];
}

export function checkPush(push) {
  try {
    const range = pushedRange(push)?.join('..');
    if (!range) return [];
    if (TRAILER.test(git(push.dir, ['log', '--format=%B', range]))) return [];
    return findWeakening(git(push.dir, ['diff', '--no-color', '--no-ext-diff', '-U0', range]));
  } catch {
    return [];
  }
}

// Generated lockfiles do not count toward a diff budget.
const LOCKFILE = /(?:^|\/)(?:package-lock\.json|npm-shrinkwrap\.json|pnpm-lock\.yaml|yarn\.lock|bun\.lockb?|Cargo\.lock|go\.sum|poetry\.lock|uv\.lock|Pipfile\.lock|Gemfile\.lock|composer\.lock|Podfile\.lock|pubspec\.lock|gradle\.lockfile|flake\.lock)$/;
export const DIFF_LIMIT = Symbol.for('megai.diff-limit');

/** Changed lines (added + removed) in `git diff --numstat` output, lockfiles and binaries excluded. */
export function countChanged(numstat) {
  let total = 0;
  for (const line of String(numstat).split('\n')) {
    const [added, removed, ...path] = line.split('\t');
    if (!path.length || LOCKFILE.test(path.join('\t').replace(/^.*=> /, '').replace(/}$/, ''))) continue;
    total += (Number(added) || 0) + (Number(removed) || 0);
  }
  return total;
}

/**
 * The active diff budget: set by Factory for a routine task (globalThis[DIFF_LIMIT] =
 * { lines, label }), or MEGAI_DIFF_LIMIT=<lines> for a manual session.
 */
export function diffLimit(env = process.env) {
  const active = globalThis[DIFF_LIMIT];
  if (active && Number.isSafeInteger(active.lines) && active.lines > 0) return { lines: active.lines, label: String(active.label ?? 'Factory routine') };
  const lines = Number(env.MEGAI_DIFF_LIMIT);
  return Number.isSafeInteger(lines) && lines > 0 ? { lines, label: 'MEGAI_DIFF_LIMIT' } : undefined;
}

/** A finding when the pushed range (merge-base to source) changes more lines than `limit` allows. */
export function checkSize(push, limit) {
  try {
    const range = pushedRange(push);
    if (!range || !limit) return [];
    const changed = countChanged(git(push.dir, ['diff', '--numstat', '--no-color', '--no-ext-diff', `${range[0]}...${range[1]}`]));
    return changed > limit.lines ? [`${changed} changed lines exceed the ${limit.lines}-line budget of ${limit.label} (lockfiles excluded)`] : [];
  } catch {
    return [];
  }
}

export function sizeReason(findings) {
  return [
    'megai-test-guard blocked this push to dev: the change is larger than this task allows.',
    ...findings.map((f) => `- ${f}`),
    'Keep the most valuable part within the budget and push that, or push nothing. List what is left in a Brokan task note',
    'and move the task to review. Do not split the same change into several pushes to get around the budget.',
  ].join('\n');
}

export function blockReason(findings) {
  const list = findings.slice(0, 8).map((f) => `- ${f}`).join('\n');
  return [
    'megai-test-guard blocked this push to dev: the pushed commits weaken tests.',
    list + (findings.length > 8 ? `\n- …and ${findings.length - 8} more` : ''),
    'Make the code pass the original tests instead. If the test change itself is correct (the behavior was removed or the test was wrong),',
    'add a commit-message trailer `Test-Change: <why>` to a commit in the range (amend the unpushed commit), mention it in the task note, then push again.',
  ].join('\n');
}

export function guardEnabled(env = process.env) {
  return !/^(?:0|off|false)$/i.test(String(env.MEGAI_TEST_GUARD ?? '').trim());
}

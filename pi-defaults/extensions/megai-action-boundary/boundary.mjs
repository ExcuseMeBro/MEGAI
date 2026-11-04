import { randomUUID } from 'node:crypto';
import { constants as fsFlags, mkdirSync, lstatSync, openSync, writeSync, closeSync } from 'node:fs';
import { join } from 'node:path';

// A visible, best-effort Pi tool-call approval boundary, NOT an OS sandbox or a
// shell interpreter. Keep classifications conservative and report uncovered paths.
// Dangerous patterns run on a quote-masked segment: text inside quotes ('git push' in an
// rg pattern or a commit message) is data, not a command. Shell code passed as a string
// (`bash -c '…'`, `eval`, `trap`, `ssh host '…'`) is extracted and classified on its own.
const AT_COMMAND = String.raw`(?:^|[|(\x60]\s*|\b(?:xargs|sudo|exec|nohup|env|command|builtin|timeout(?:\s+-\S+)*\s+\S+)\s+(?:-\S+\s+)*)`;
const GIT_CMD = String.raw`\bgit\s+(?:-[Cc]\s+\S+\s+)*`;
const DANGEROUS_SHELL = [
  ['session-stop', new RegExp(String.raw`${AT_COMMAND}(?:killall|pkill|kill(?!\s+-0\b))(?![\w-])|\b(?:launchctl\s+(?:stop|remove|bootout|kill)|systemctl\s+(?:stop|restart|kill))\b`, 'i')],
  ['destructive-file', new RegExp(String.raw`${GIT_CMD}(?:reset\s+--hard|clean\s+-[\w]*f[\w]*)\b`, 'i')],
  // Case-sensitive: `git branch -d` (merged-only delete) is the normal cleanup step.
  ['destructive-file', new RegExp(String.raw`${GIT_CMD}branch\s+(?:-D|--delete\s+--force|-d\s+--force|--force\s+-d|-df|-fd)\b`)],
  // Listing tags (`git tag`, `git tag -l`) is read-only; creating/deleting one is reserved.
  ['publish', new RegExp(String.raw`${GIT_CMD}push\b|${GIT_CMD}tag\s+(?!-l\b|--list\b|-n\d*\b|--contains\b|--points-at\b|--merged\b|--no-merged\b|-v\b|--verify\b|--sort\b|--column\b)[^\s|)&;]|\b(?:npm\s+publish|eas\s+(?:deploy|submit|update)|docker\s+push)\b`, 'i')],
  ['remote-script', /\b(?:curl|wget)\b[^\n;]{0,500}\|\s*(?:sh|bash|zsh)\b/i],
  ['privilege', /(?:^|[\s;&|(])(?:sudo(?=\s)|chmod\s+-R\s+777\b)/i],
];
const BROKAN_DESTRUCTIVE = /^mcp__brokan__(?:delete_task|delete_project)$/;

// STANDING APPROVAL (see AGENTS.md "Autonomous dev delivery"): these shapes run without
// a prompt. Force flags, tags, --all/--mirror and protected branches still need one.
const GIT = String.raw`git (?:-C (?:"[^"\x60]+"|[^\s;&|\x60'"]+) )?`;
const NAME = String.raw`(?!-)[\w.\/-]+`;
const REMOTE = String.raw`(?!-)[\w.-]+`;
const VAR = String.raw`"?\$\{?\w+\}?"?`;
const REV_PARSE = String.raw`"?\$\(git (?:-C [^\s()]+ )?rev-parse(?: --verify)? [\w.\/^~@{}-]+\)"?`;
const PUSH_PROTECTED = /^(?:main|master|prod|production|release(?:[\/-].*)?|gh-pages|v?\d+(?:\.\d+)+.*)$/;
const DELETE_PROTECTED = /^(?:main|master|dev|develop|staging|prod|production|release(?:[\/-].*)?|pi|for-ustama|validationsdk|gh-pages)$/;
// `git [-C dir] [-c k=v] push [-u|-q] <remote> <refspec>…`: approved when every refspec
// targets a literal, unprotected branch. Force (`+src:dst`, --force*), --tags/--all/
// --mirror, a ref held in a variable (`$sha:$ref`) or a protected target still prompt.
const PUSH_OK_FLAGS = new Set(['-u', '--set-upstream', '-q', '--quiet', '--porcelain', '-v', '--verbose', '--progress', '--no-progress', '--atomic']);
const SOURCE = /^(?:HEAD|@|[a-f0-9]{7,40}|[\w.\/-]+|\$\{?\w+\}?|\$\(git (?:-C \S+ )?rev-parse(?: --verify)? [\w.\/^~@{}-]+\))$/;
function words(text) { return text.match(/(?:\$\([^()]*\)|[^\s"']+|"[^"]*"|'[^']*')+/g) || []; }
function pushTargets(raw) {
  const w = words(raw); let i = 0;
  if (w[i++] !== 'git') return null;
  while (w[i] === '-C' || w[i] === '-c') i += 2;
  if (w[i++] !== 'push') return null;
  while (PUSH_OK_FLAGS.has(w[i])) i += 1;
  const remote = w[i++];
  if (!remote || remote.startsWith('-') || i >= w.length) return null;
  const targets = [];
  for (const spec of w.slice(i).map(unquote)) {
    if (spec.startsWith('-') || spec.startsWith('+')) return null;
    const colon = spec.indexOf(':');
    const src = colon < 0 ? spec : spec.slice(0, colon);
    const dst = (colon < 0 ? spec : spec.slice(colon + 1)).replace(/^refs\/heads\//, '');
    if (!SOURCE.test(src) || !new RegExp(`^${NAME}$`).test(dst) || dst.startsWith('refs/')) return null;
    targets.push(dst);
  }
  return targets;
}
const REF = String.raw`(?:refs\/heads\/)?(?:${NAME}|${VAR})`;
const DELETE = new RegExp(`^${GIT}push (?:-q |--quiet )?${REMOTE} (?:--delete |-d |:)(${REF}(?: ${REF})*)$`);
// Every named branch must be deletable; one protected name keeps the prompt.
const allDeletable = (names) => names.trim().split(/\s+/).every(n => !DELETE_PROTECTED.test(n.replace(/^"|"$/g, '').replace(/^refs\/heads\//, '')));
const PID = String.raw`(?:-?\d{2,}|\d+|${VAR}|"?\$!"?|"?\$\((?:<\s*|cat )[^()]+\)"?)`;
const STANDING_APPROVED = [
  ['branch-push', (part) => { const t = pushTargets(part); return !!t && t.every(dst => !PUSH_PROTECTED.test(dst)); }],
  ['branch-cleanup', (part) => { const m = DELETE.exec(part); return !!m && allDeletable(m[1]); }],
  // Squash/ours-merged task branches need -D (one or many at once); protected
  // long-lived branches still prompt.
  ['branch-cleanup', (part) => { const m = new RegExp(`^${GIT}branch (?:-D|-d --force|--delete --force|-f -d|-df|-fd) (${REF}(?: ${REF})*)$`).exec(part); return !!m && allDeletable(m[1]); }],
  // `git clean` scoped to a build/output subdirectory; a bare repo-wide clean still prompts.
  ['scoped-clean', (part) => { const m = new RegExp(`^${GIT}clean -[dfqxX]+ (?:-- )?((?:[^\\s;&|\x60$/-][^\\s;&|\x60$]*\\s*)+)$`).exec(part); return !!m && !/(?:^|\s)\.\.?(?:\/|\s|$)/.test(m[1]); }],
  // `-X` removes only ignored files (build output), never untracked work.
  ['ignored-clean', (part) => new RegExp(`^${GIT}clean -[dfqX]*X[dfqX]*$`).test(part)],
  // One named launchd job (a dev daemon), not a broad stop.
  ['targeted-service-stop', (part) => { const m = /^launchctl (?:stop|bootout|remove|kill \w+) "?((?:[\w.\/{}$-]|\$\(id -u\))+)"?$/.exec(part); return !!m && !/^(?:system|(?:gui|user)\/[^/]+)\/?$/.test(m[1]); }],
  ['task-worktree-cleanup', (part) => new RegExp(`^${GIT}worktree remove (?:--force |-f )?[^\\s;&|\\x60$]+$`).test(part)],
  // One blocking process (or its own process group) by exact PID, a script's own child
  // in a variable, or a PID file. Broad name-based pkill/killall stays blocked: it would
  // stop every session, including the agent itself. `kill -0` only checks liveness.
  ['targeted-session-stop', (part) => new RegExp(`^kill (?:-(?:TERM|15|9|KILL|INT|2|HUP|1|QUIT|3|USR1|USR2|STOP|CONT) |-s (?:TERM|KILL|INT|HUP|USR1|USR2) )?${PID}(?: ${PID})*$`).test(part)],
  ['process-check', (part) => /^kill -0(?:\s|$)/.test(part)],
];
const SEVERITY = { normal: 0, approval: 1, block: 2 };

// `rm -rf` is routine for temp dirs, build output and task cleanup. Prompt only when a
// target could wipe a root, home, a repository's .git or an unknown expansion.
const TEMP_ROOT = /^(?:\/tmp|\/private\/tmp|\/var\/folders|\/private\/var\/folders)\/[^/]+/;
const HOME_VAR = /^(?:~|\$HOME|\$\{HOME\})(?=\/|$)/;
function riskyRmTarget(raw) {
  const target = raw.replace(/^(['"])(.*)\1$/, '$2').replace(/["']/g, '');
  if (!target || /\$\(|\x60/.test(target)) return true;
  const parts = target.split('/').filter(Boolean);
  if (parts.some(part => part === '.git')) return true;
  if (HOME_VAR.test(target)) return parts.length < 3 || target.includes('*') && parts.length < 4;
  if (/^\$(?:PWD|USER|TMPDIR|OLDPWD)\b|^\$\{(?:PWD|USER|TMPDIR|OLDPWD)\}/.test(target)) return true;
  if (/^\$\{?\w+\}?/.test(target)) {
    const rest = target.replace(/^\$\{?\w+\}?/, '');
    return rest !== '' && !/^\/[^*/][^*]*$/.test(rest);   // $x or ${x}/sub; never $x/ or $x/*
  }
  if (target.startsWith('/')) {
    if (TEMP_ROOT.test(target)) return false;
    return parts.length < 5 || target.includes('*') && parts.length < 6;
  }
  return /^\.\.?(?:\/|$)\*?$|^\*$|^\.\.\//.test(target);
}
// `masked` finds a real `rm` (not one inside a quoted pattern); targets are read unmasked.
function rmIsRisky(masked, unmask = (text) => text) {
  const match = /(?:^|[\s(])rm\s+(.*)$/.exec(masked);
  if (!match) return false;
  const tokens = unmask(match[1]).match(/"[^"]*"|'[^']*'|\S+/g) || [];
  const flags = tokens.filter(token => /^-/.test(token)).join(' ');
  if (!/(?:^|\s)-(?:\w*r\w*f|\w*f\w*r)\b|-r\s+-f|-f\s+-r|--recursive|-R\b/.test(flags)) return false;
  const targets = tokens.filter(token => !/^-/.test(token));
  return targets.length === 0 || targets.some(riskyRmTarget);
}

function dangerous(masked, unmask) {
  if (rmIsRisky(masked, unmask)) return { risk: 'approval', category: 'destructive-file' };
  for (const [category, pattern] of DANGEROUS_SHELL) {
    if (pattern.test(masked)) return { risk: category === 'session-stop' ? 'block' : 'approval', category };
  }
  return { risk: 'normal', category: 'unclassified' };
}

// Replace quoted text with placeholders so separators and keywords inside quotes are
// not mistaken for commands. Double quotes holding `$(…)`/backticks stay visible (they
// run code). A quoted argument of `bash -c`, `sh -c`, `eval`, `trap` or `watch` is shell
// code: it is returned in `inner` and classified separately.
const SHELL_ARG = /(?:\b(?:ba|z|da|k)?sh\s+(?:-[a-z]+\s+)*-[a-z]*c[a-z]*|\beval|\btrap|\bwatch(?:\s+-\S+)*)\s*$/;
function mask(command) {
  const saved = []; const inner = [];
  let out = ''; let i = 0;
  while (i < command.length) {
    const ch = command[i];
    if (ch === '\\') { out += command.slice(i, i + 2); i += 2; continue; }
    if (ch === "'" || ch === '"') {
      let j = i + 1;
      while (j < command.length && command[j] !== ch) j += ch === '"' && command[j] === '\\' ? 2 : 1;
      if (j >= command.length) { out += command.slice(i); break; }
      const body = command.slice(i + 1, j);
      if (ch === '"' && /\$\(|\x60/.test(body)) { out += command.slice(i, j + 1); i = j + 1; continue; }
      if (SHELL_ARG.test(out)) inner.push(body);
      out += `${ch}\u0001${saved.push(body) - 1}\u0001${ch}`; i = j + 1; continue;
    }
    out += ch; i += 1;
  }
  return { masked: out, inner, unmask: (text) => text.replace(/\u0001(\d+)\u0001/g, (_, n) => saved[Number(n)]) };
}

// Split `cd X && cmd 2>&1 | tail` chains and scripts (lines, ;, &, &&, ||, braces) so an
// approved step is not re-prompted and every risky step is still classified on its own.
// Heredoc bodies fed to a non-shell program (python, node, psql, cat …) are data or
// code in another language, not shell commands; drop them so `proc.kill()` or a quoted
// "git push" in evidence text is not mistaken for a command. Shell heredocs stay.
const DATA_HEREDOC = /^([^\n]*\b(?:python3?|node|deno|ruby|perl|cat|tee|psql|sqlite3|mysql|jq|osascript|swift|go\s+run)\b[^\n]*<<-?\s*(['"]?)(\w+)\2[^\n]*)\n[\s\S]*?(?:\n[ \t]*\3[ \t]*$|(?![\s\S]))/gm;
// `ssh host 'bash -s' <<'SH' … SH`: the heredoc body is the remote script. Like bash, an
// unterminated heredoc runs to the end of the command.
const SSH_HEREDOC = /^([^\n]*(?:^|[\s;&|(])ssh\s[^\n]*<<-?\s*(['"]?)(\w+)\2[^\n]*)\n([\s\S]*?)(?:\n[ \t]*\3[ \t]*$|(?![\s\S]))/gm;
function segments(masked) {
  return masked.split(/&&|\|\||;|\n|\{|\}|(?<![>&<|])&(?![>&])/).map(part => part
    .replace(/^\s*\(+\s*/, '')
    .replace(/^\s*(?:(?:then|do|else|elif|if|while|until|!|time|nohup|exec|command|builtin|env|timeout(?:\s+-\S+)*\s+\d[\w.]*)\s+)+/, '')
    .replace(/^\s*[^\s()]*\)\s+/, '')
    .replace(/^\s*(?:[A-Za-z_]\w*=(?:'[^']*'|"[^"]*"|[^\s'"]*)\s+)+(?=\S)/, '')
    .replace(/\s*\d?>&\d/g, '')
    .replace(/(?:\s*\|&?\s*(?:tail|head|cat|grep|wc|tee|sed|sort|uniq|cut|tr)\b[^|]*)+$/, '')
    .replace(/\s*(?:\d|&)?>>?\s*(?:"[^"]*"|[^\s"'|;&]+)/g, '')
    .replace(/\s*\)+\s*$/, '')
    .trim()).filter(Boolean);
}

// `ssh host 'cmd'` runs cmd on a remote server. Pull that remote command out so its own
// steps are classified one by one; `sudo` and stopping processes there is routine server
// work (standing approval), but remote steps still face every other rule (`rm -rf /`).
const SSH_OPTS_WITH_ARG = new Set(['-i', '-o', '-p', '-l', '-F', '-J', '-L', '-R', '-D', '-c', '-m', '-b', '-E', '-S', '-W', '-O', '-Q', '-w', '-e', '-B', '-I']);
// End index (exclusive) of a quoted run starting at `i`; -1 if unterminated.
function quoteEnd(command, i) {
  const q = command[i]; let j = i + 1;
  while (j < command.length && command[j] !== q) j += q === '"' && command[j] === '\\' ? 2 : 1;
  return j < command.length ? j + 1 : -1;
}
function sshTokens(command, start) {
  const tokens = []; let i = start;
  while (i < command.length) {
    while (command[i] === ' ' || command[i] === '\t') i += 1;
    const ch = command[i];
    if (ch === undefined || ch === '\n' || ch === ';' || ch === '|' || ch === '&' || ch === '<' || ch === '>' || ch === ')') break;
    let j = i;
    // A word may glue several quoted and bare pieces: 'a'"'"'b', x="$y".
    while (j < command.length && !/[\s;|&<>)]/.test(command[j])) {
      if (command[j] === "'" || command[j] === '"') { j = quoteEnd(command, j); if (j < 0) return null; }
      else j += command[j] === '\\' ? 2 : 1;
    }
    tokens.push(command.slice(i, j)); i = j;
  }
  return { tokens, end: i };
}
// Shell-unquote one word the way the remote side receives it.
function unquote(word) {
  let out = ''; let i = 0;
  while (i < word.length) {
    const ch = word[i];
    if (ch === "'") { const j = word.indexOf("'", i + 1); if (j < 0) return out + word.slice(i + 1); out += word.slice(i + 1, j); i = j + 1; }
    else if (ch === '"') { let j = i + 1; while (j < word.length && word[j] !== '"') { if (word[j] === '\\' && /["\\$\x60]/.test(word[j + 1])) j += 1; out += word[j]; j += 1; } i = j + 1; }
    else if (ch === '\\') { out += word[i + 1] ?? ''; i += 2; }
    else { out += ch; i += 1; }
  }
  return out;
}
function splitRemote(command) {
  const remotes = []; let local = ''; let last = 0;
  const re = /(^|[\s;&|(])ssh(?=\s)/g; let m;
  while ((m = re.exec(command))) {
    const at = m.index + m[1].length; const scan = sshTokens(command, at + 3);
    if (!scan) return null;
    let k = 0;
    while (k < scan.tokens.length && scan.tokens[k].startsWith('-')) k += SSH_OPTS_WITH_ARG.has(scan.tokens[k]) ? 2 : 1;
    const host = scan.tokens[k]; const rest = scan.tokens.slice(k + 1);
    if (!host || !rest.length) continue;
    remotes.push(rest.map(unquote).join(' '));
    local += command.slice(last, at) + 'ssh ' + host; last = scan.end; re.lastIndex = scan.end;
  }
  return { local: local + command.slice(last), remotes };
}
const REMOTE_SUDO = /(^|[\s;&|(])sudo(?:\s+-[A-Za-z]+)*\s+/g;
const REMOTE_ROUTINE = new Set(['privilege', 'session-stop']);

function worse(a, b) {
  return SEVERITY[b.risk] > SEVERITY[a.risk] || (a.category === 'unclassified' && b.category !== 'unclassified' && b.risk === a.risk) ? b : a;
}
function classifyShell(command, remote, depth) {
  if (depth > 4) return { risk: 'approval', category: 'uninspectable-shell' };
  let text = command.replace(DATA_HEREDOC, '$1');
  const remoteScripts = [];
  text = text.replace(SSH_HEREDOC, (_, head, _q, _tag, body) => { remoteScripts.push(body); return head; });
  const split = splitRemote(text);
  const local = split ? split.local : text;
  const remotes = split ? [...split.remotes, ...remoteScripts] : remoteScripts;
  let worst = { risk: 'normal', category: 'unclassified' };
  const { masked, inner, unmask } = mask(remote ? local.replace(REMOTE_SUDO, '$1') : local);
  for (const part of segments(masked)) {
    const raw = unmask(part);
    const approved = STANDING_APPROVED.find(([, ok]) => ok(raw));
    let decision = approved ? { risk: 'normal', category: approved[0] } : dangerous(part, unmask);
    if (remote && REMOTE_ROUTINE.has(decision.category)) decision = { risk: 'normal', category: `remote-${decision.category === 'privilege' ? 'sudo' : 'process-stop'}` };
    worst = worse(worst, decision);
  }
  for (const code of inner) worst = worse(worst, classifyShell(code, remote, depth + 1));
  for (const code of remotes) worst = worse(worst, classifyShell(code, true, depth + 1));
  return worst;
}

export function classify(event) {
  const name = event?.toolName;
  if (BROKAN_DESTRUCTIVE.test(name)) return { risk: 'approval', category: 'brokan-destructive' };
  if (name !== 'bash') return { risk: 'normal', category: 'unclassified' };
  const command = event?.input?.command;
  if (typeof command !== 'string' || !command.trim()) return { risk: 'approval', category: 'uninspectable-shell' };
  return classifyShell(command, false, 0);
}

// Never log arbitrary tool names: a provider or malicious extension can supply a
// name containing credentials. No paths, prompts, arguments, call IDs or results.
export function safeTelemetry(name) {
  if (['bash', 'read', 'write', 'edit', 'tool_search', 'web_search', 'fetch_content'].includes(name)) return name;
  if (typeof name === 'string' && name.startsWith('mcp__brokan__')) return 'brokan';
  return 'other';
}

function subjectFor(event) {
  if (event.toolName === 'bash') {
    const command = event.input?.command;
    if (typeof command !== 'string' || command.length > 1024 || /[\x00-\x08\x0b-\x1f\x7f]/.test(command)) return null;
    return command;
  }
  const value = event.input?.file_path ?? event.input?.path ?? event.input?.from ?? event.input?.id;
  if (typeof value !== 'string' || !value || value.length > 512 || /[\x00-\x1f\x7f]/.test(value)) return null;
  return value;
}

export function createBoundary({ traceDir } = {}) {
  let fd;
  let file;
  function traceFile() { return file; }
  function record(action, category, name, error = null, durationMs = null) {
    if (traceDir === null) return;
    if (typeof traceDir !== 'string' || !traceDir) throw Error('private trace directory not configured');
    if (fd === undefined) {
      mkdirSync(traceDir, { recursive: true, mode: 0o700 });
      const stat = lstatSync(traceDir);
      if (!stat.isDirectory() || (stat.mode & 0o077)) throw Error('private trace directory must be a real 0700 directory');
      file = join(traceDir, `pi-tool-${randomUUID()}.jsonl`);
      fd = openSync(file, fsFlags.O_CREAT | fsFlags.O_EXCL | fsFlags.O_WRONLY | (fsFlags.O_NOFOLLOW ?? 0), 0o600);
    }
    const row = { at: new Date().toISOString(), action, category, tool: safeTelemetry(name), error, durationMs };
    writeSync(fd, JSON.stringify(row) + '\n');
  }
  async function onToolCall(event, ctx) {
    const decision = classify(event);
    if (decision.risk === 'normal') {
      try { record('allow', decision.category, event.toolName); } catch { /* normal tools must not fail for optional telemetry */ }
      return;
    }
    if (decision.risk === 'block') {
      try { record('deny', decision.category, event.toolName); } catch { /* denied regardless of trace availability */ }
      return { block: true, reason: 'Broad process stop blocked: pkill/killall/launchctl/systemctl can stop every session, including this one. Stop only the exact blocking process with `kill <PID>`; do not retry this tool call.' };
    }
    const subject = subjectFor(event);
    let approved = false;
    if (subject && ctx?.hasUI && typeof ctx.ui?.confirm === 'function') {
      try { approved = await ctx.ui.confirm('Approve risky tool call?', `${decision.category}: ${event.toolName}\n${subject}`) === true; }
      catch { /* unavailable UI must deny, never silently approve */ }
    }
    try { record(approved ? 'approve' : 'deny', decision.category, event.toolName); }
    catch { return { block: true, reason: 'Risky Pi tool call blocked: private trace unavailable; request explicit approval after fixing trace storage.' }; }
    if (!approved) return { block: true, reason: `Risky Pi tool call not approved (${decision.category}); request explicit interactive approval. No automatic retry.` };
  }
  function onToolEnd(event) {
    const duration = typeof event.durationMs === 'number' && Number.isFinite(event.durationMs)
      ? Math.max(0, Math.round(event.durationMs)) : null;
    try { record('complete', 'tool-result', event.toolName, event.isError === true, duration); }
    catch { /* execution has already ended; cannot change the outcome */ }
  }
  function close() { if (fd !== undefined) { closeSync(fd); fd = undefined; } }
  return { onToolCall, onToolEnd, traceFile, close };
}

import { randomUUID } from 'node:crypto';
import { constants as fsFlags, mkdirSync, lstatSync, openSync, writeSync, closeSync } from 'node:fs';
import { join } from 'node:path';

// A visible, best-effort Pi tool-call approval boundary, NOT an OS sandbox or a
// shell interpreter. Keep classifications conservative and report uncovered paths.
const DANGEROUS_SHELL = [
  ['session-stop', /\b(?:killall|pkill|kill|launchctl\s+(?:stop|remove)|systemctl\s+(?:stop|restart))\b/i],
  ['destructive-file', /\b(?:git\s+(?:reset\s+--hard|clean\s+-[\w]*f[\w]*))\b/i],
  // Case-sensitive: `git branch -d` (merged-only delete) is the normal cleanup step.
  ['destructive-file', /\bgit\s+branch\s+(?:-D|--delete\s+--force|-d\s+--force|--force\s+-d)\b/],
  ['publish', /\b(?:git\s+push|git\s+tag|npm\s+publish|eas\s+(?:deploy|submit|update)|docker\s+push)\b/i],
  ['remote-script', /\b(?:curl|wget)\b[^\n;]{0,500}\|\s*(?:sh|bash|zsh)\b/i],
  ['privilege', /(?:^|[\s;&|(])(?:sudo(?=\s)|chmod\s+-R\s+777\b)/i],
];
const BROKAN_DESTRUCTIVE = /^mcp__brokan__(?:delete_task|delete_project)$/;

// STANDING APPROVAL (see AGENTS.md "Autonomous dev delivery"): these shapes run without
// a prompt. Force flags, tags, --all/--mirror and protected branches still need one.
const GIT = String.raw`git (?:-C [^\s;&|\x60$'"]+ )?`;
const NAME = String.raw`(?!-)[\w.\/-]+`;
const REMOTE = String.raw`(?!-)[\w.-]+`;
const PUSH_PROTECTED = /^(?:main|master|prod|production|release(?:[\/-].*)?|gh-pages|v?\d+(?:\.\d+)+.*)$/;
const DELETE_PROTECTED = /^(?:main|master|dev|develop|staging|prod|production|release(?:[\/-].*)?|pi|for-ustama|validationsdk|gh-pages)$/;
const PUSH = new RegExp(`^${GIT}push (?:-u |--set-upstream )?${REMOTE} "?(?:(?:HEAD|[a-f0-9]{7,40}|"?\\$\\{?\\w+\\}?"?):)?(?:refs\\/heads\\/)?(${NAME})"?$`);
const DELETE = new RegExp(`^${GIT}push ${REMOTE} (?:--delete |-d |:)(?:refs\\/heads\\/)?(${NAME})$`);
const STANDING_APPROVED = [
  ['branch-push', (part) => { const m = PUSH.exec(part); return !!m && !PUSH_PROTECTED.test(m[1]); }],
  ['branch-cleanup', (part) => { const m = DELETE.exec(part); return !!m && !DELETE_PROTECTED.test(m[1]); }],
  // Squash/ours-merged task branches need -D; protected long-lived branches still prompt.
  ['branch-cleanup', (part) => { const m = new RegExp(`^${GIT}branch (?:-D|-d --force|--delete --force) (${NAME}|"?\\$\\{?\\w+\\}?"?)$`).exec(part); return !!m && !DELETE_PROTECTED.test(m[1]); }],
  // `git clean` scoped to a build/output subdirectory; a bare repo-wide clean still prompts.
  ['scoped-clean', (part) => { const m = new RegExp(`^${GIT}clean -[dfqxX]+ (?:-- )?((?:[^\\s;&|\x60$/-][^\\s;&|\x60$]*\\s*)+)$`).exec(part); return !!m && !/(?:^|\s)\.\.?(?:\/|\s|$)/.test(m[1]); }],
  ['task-worktree-cleanup', (part) => new RegExp(`^${GIT}worktree remove (?:--force |-f )?[^\\s;&|\\x60$]+$`).test(part)],
  // One blocking process by exact numeric PID. Broad name-based pkill/killall stays
  // blocked: it would stop every session, including the agent itself.
  // A literal PID, or a script's own child held in a variable (`kill "$server_pid"`).
  ['targeted-session-stop', (part) => /^kill (?:-(?:0|TERM|15|9|KILL|INT|2) )?(?:\d+|"?\$\{?\w+\}?"?)(?: (?:\d+|"?\$\{?\w+\}?"?))*$/.test(part)],
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
function rmIsRisky(part) {
  const match = /(?:^|[\s(])rm\s+(.*)$/.exec(part);
  if (!match) return false;
  const tokens = match[1].match(/"[^"]*"|'[^']*'|\S+/g) || [];
  const flags = tokens.filter(token => /^-/.test(token)).join(' ');
  if (!/(?:^|\s)-(?:\w*r\w*f|\w*f\w*r)\b|-r\s+-f|-f\s+-r|--recursive|-R\b/.test(flags)) return false;
  const targets = tokens.filter(token => !/^-/.test(token));
  return targets.length === 0 || targets.some(riskyRmTarget);
}

function dangerous(command) {
  if (rmIsRisky(command)) return { risk: 'approval', category: 'destructive-file' };
  for (const [category, pattern] of DANGEROUS_SHELL) {
    if (pattern.test(command)) return { risk: category === 'session-stop' ? 'block' : 'approval', category };
  }
  return { risk: 'normal', category: 'unclassified' };
}

// Split `cd X && cmd 2>&1 | tail` chains and scripts (lines, ;, &&, ||, braces) so an
// approved step is not re-prompted and every risky step is still classified on its own.
// Heredoc bodies fed to a non-shell program (python, node, psql, cat …) are data or
// code in another language, not shell commands; drop them so `proc.kill()` or a quoted
// "git push" in evidence text is not mistaken for a command. Shell heredocs stay.
const DATA_HEREDOC = /^([^\n]*\b(?:python3?|node|deno|ruby|perl|cat|tee|psql|sqlite3|mysql|jq|osascript|swift|go\s+run)\b[^\n]*<<-?\s*(['"]?)(\w+)\2[^\n]*)\n[\s\S]*?\n[ \t]*\3[ \t]*$/gm;
function segments(command) {
  return command.replace(DATA_HEREDOC, '$1').split(/&&|\|\||;|\n|\{|\}/).map(part => part
    .replace(/^\s*(?:(?:then|do|else|if|while|until|!|time)\s+)+/, '')
    .replace(/^\s*(?:[A-Za-z_]\w*=(?:'[^']*'|"[^"]*"|[^\s'"]*)\s+)+(?=\S)/, '')
    .replace(/\s*\d?>&\d/g, '')
    .replace(/\s*\d?>\s*\/dev\/null/g, '')
    .replace(/(?:\s*\|\s*(?:tail|head|cat|grep|wc|tee|sed|sort|uniq|cut|tr)\b[^|]*)+$/, '')
    .trim()).filter(Boolean);
}

// `ssh host 'cmd'` runs cmd on a remote server. Pull that remote command out so its own
// steps are classified one by one; `sudo` there is routine server work (standing
// approval), but the remote steps still face every other rule (e.g. `rm -rf /`).
const SSH_OPTS_WITH_ARG = new Set(['-i', '-o', '-p', '-l', '-F', '-J', '-L', '-R', '-D', '-c', '-m', '-b', '-E', '-S', '-W', '-O', '-Q', '-w', '-e', '-B', '-I']);
function sshTokens(command, start) {
  const tokens = []; let i = start;
  while (i < command.length) {
    while (command[i] === ' ' || command[i] === '\t') i += 1;
    const ch = command[i];
    if (ch === undefined || ch === '\n' || ch === ';' || ch === '|' || ch === '&' || ch === '<' || ch === '>' || ch === ')') break;
    let j = i;
    if (ch === "'" || ch === '"') { j = command.indexOf(ch, i + 1); if (j < 0) return null; j += 1; }
    else { while (j < command.length && !/[\s;|&<>)]/.test(command[j])) { if (command[j] === "'" || command[j] === '"') { const k = command.indexOf(command[j], j + 1); if (k < 0) return null; j = k; } j += 1; } }
    tokens.push(command.slice(i, j)); i = j;
  }
  return { tokens, end: i };
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
    remotes.push(rest.map(token => /^(['"])[\s\S]*\1$/.test(token) ? token.slice(1, -1) : token).join(' '));
    local += command.slice(last, at) + 'ssh ' + host; last = scan.end; re.lastIndex = scan.end;
  }
  return { local: local + command.slice(last), remotes };
}
const REMOTE_SUDO = /(^|[\s;&|(])sudo(?:\s+-[A-Za-z]+)*\s+/g;

export function classify(event) {
  const name = event?.toolName;
  if (BROKAN_DESTRUCTIVE.test(name)) return { risk: 'approval', category: 'brokan-destructive' };
  if (name !== 'bash') return { risk: 'normal', category: 'unclassified' };
  const command = event?.input?.command;
  if (typeof command !== 'string' || !command.trim()) return { risk: 'approval', category: 'uninspectable-shell' };
  const split = splitRemote(command.replace(DATA_HEREDOC, '$1'));
  const parts = split
    ? [...segments(split.local).map(text => ({ text })),
      ...split.remotes.flatMap(remote => segments(remote.replace(REMOTE_SUDO, '$1')).map(text => ({ text, remote: true })))]
    : segments(command).map(text => ({ text }));
  let worst = { risk: 'normal', category: 'unclassified' };
  for (const { text: part, remote } of parts) {
    const approved = STANDING_APPROVED.find(([, ok]) => ok(part));
    let decision = approved ? { risk: 'normal', category: approved[0] } : dangerous(part);
    if (remote && decision.category === 'privilege') decision = { risk: 'normal', category: 'remote-sudo' };
    if (SEVERITY[decision.risk] > SEVERITY[worst.risk] || (worst.category === 'unclassified' && decision.category !== 'unclassified' && decision.risk === worst.risk)) worst = decision;
  }
  return worst;
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

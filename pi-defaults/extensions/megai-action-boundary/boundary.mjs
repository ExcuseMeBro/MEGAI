import { randomUUID } from 'node:crypto';
import { constants as fsFlags, mkdirSync, lstatSync, openSync, writeSync, closeSync } from 'node:fs';
import { join } from 'node:path';

// A visible, best-effort Pi tool-call approval boundary, NOT an OS sandbox or a
// shell interpreter. Keep classifications conservative and report uncovered paths.
const DANGEROUS_SHELL = [
  ['session-stop', /\b(?:killall|pkill|kill|launchctl\s+(?:stop|remove)|systemctl\s+(?:stop|restart))\b/i],
  ['destructive-file', /\b(?:rm\s+(?:-[\w]*r[\w]*f|-[\w]*f[\w]*r|-[\w]*r\s+-[\w]*f)|git\s+(?:reset\s+--hard|clean\s+-[\w]*f[\w]*|worktree\s+remove\s+(?:--force|-f)|branch\s+-D))\b/i],
  ['publish', /\b(?:git\s+push|git\s+tag|npm\s+publish|eas\s+(?:deploy|submit|update)|docker\s+push)\b/i],
  ['remote-script', /\b(?:curl|wget)\b[^\n;]{0,500}\|\s*(?:sh|bash|zsh)\b/i],
  ['privilege', /\b(?:sudo|chmod\s+-R\s+777)\b/i],
];
const PELLET_DESTRUCTIVE = /^mcp__pellet__(?:delete_task|delete_note|delete_attachment|delete_canvas_nodes|rename_note|rename_tag|set_archived|restore_from_trash)$/;
const CANONICAL_DEV_PUSH = /^git push origin [a-f0-9]{40}:refs\/heads\/dev$/;

export function classify(event) {
  const name = event?.toolName;
  if (PELLET_DESTRUCTIVE.test(name)) return { risk: 'approval', category: 'pellet-destructive' };
  if (name !== 'bash') return { risk: 'normal', category: 'unclassified' };
  const command = event?.input?.command;
  if (typeof command !== 'string' || !command.trim()) return { risk: 'approval', category: 'uninspectable-shell' };
  if (CANONICAL_DEV_PUSH.test(command.trim())) return { risk: 'normal', category: 'dev-push-policy' };
  for (const [category, pattern] of DANGEROUS_SHELL) {
    if (pattern.test(command)) return { risk: category === 'session-stop' ? 'block' : 'approval', category };
  }
  return { risk: 'normal', category: 'unclassified' };
}

// Never log arbitrary tool names: a provider or malicious extension can supply a
// name containing credentials. No paths, prompts, arguments, call IDs or results.
export function safeTelemetry(name) {
  if (['bash', 'read', 'write', 'edit', 'tool_search', 'web_search', 'fetch_content'].includes(name)) return name;
  if (typeof name === 'string' && name.startsWith('mcp__pellet__')) return 'pellet';
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
      return { block: true, reason: 'Pi/Paseo session/process stop blocked. Ask the owner for fresh explicit permission naming the exact resource and action; do not retry this tool call.' };
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

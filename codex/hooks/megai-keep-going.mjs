#!/usr/bin/env node
// Codex Stop hook: when the final message asks for permission/confirmation (or says
// nothing was changed) instead of finishing, continue ONCE per turn with a short
// "decide and finish" prompt. Always exits 0 with valid JSON; any error = no-op.
import { readFileSync } from 'node:fs';
import { NUDGE, classifyFinal, isQuestionPrompt, modeFromEnv } from './keep-going-core.mjs';

const EDIT_TOOL = /apply_patch|(?:^|_)(?:edit|write)(?:_|$)/i;
// Code mode routes edits through `exec` (shell/JS), so inspect the call body too.
const EDIT_BODY = /\*\*\* Begin Patch|apply_patch|sed -i|perl -pi|cat\s*>|\btee\s|writeFile|git (?:commit|apply)|>\s*["']?[\w./~-]+\.[A-Za-z]{1,6}\b/;

/** Last real user prompt and whether file-edit tools ran after it. */
function readTurn(transcriptPath) {
  const turn = { prompt: '', edited: false };
  if (!transcriptPath) return turn;
  for (const line of readFileSync(transcriptPath, 'utf8').split('\n')) {
    if (!line.includes('"response_item"')) continue;
    let p;
    try { p = JSON.parse(line).payload; } catch { continue; }
    if (p?.type === 'message' && p.role === 'user') {
      const text = (p.content ?? []).filter((c) => c?.type === 'input_text').map((c) => c.text).join('\n').trim();
      if (text && !text.startsWith('<')) { turn.prompt = text; turn.edited = false; }
    } else if (p?.type === 'custom_tool_call' || p?.type === 'function_call') {
      const body = String(p.input ?? p.arguments ?? '');
      if (EDIT_TOOL.test(String(p.name ?? '')) || EDIT_BODY.test(body)) turn.edited = true;
    }
  }
  return turn;
}

let out = {};
try {
  const input = JSON.parse(readFileSync(0, 'utf8') || '{}');
  if (modeFromEnv() !== 'off' && !input.stop_hook_active) {
    let turn = { prompt: '', edited: false };
    try { turn = readTurn(input.transcript_path); } catch { /* unknown transcript */ }
    if (!isQuestionPrompt(turn.prompt) && classifyFinal(input.last_assistant_message ?? '', { edited: turn.edited })) {
      out = { decision: 'block', reason: NUDGE };
    }
  }
} catch {
  out = {};
}
process.stdout.write(JSON.stringify(out) + '\n');

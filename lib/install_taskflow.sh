#!/usr/bin/env bash
# task-flow — priority-driven .todos board + full-ADLC protocol for Claude Code.
# Installs the skill, the TaskCreate/TaskUpdate state hook, and a board-aware
# statusline, then wires them into ~/.claude (idempotent, non-destructive).
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

SRC="$MEGAI_HOME/task-flow"
CLAUDE_DIR="$HOME/.claude"
SETTINGS="$CLAUDE_DIR/settings.json"
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
MODE="${1:-install}"  # install | --remove

if [ "$MODE" = "--remove" ]; then
  rm -rf "$CLAUDE_DIR/skills/task-flow"
  rm -f "$CLAUDE_DIR/hooks/task-state.js" "$CLAUDE_DIR/hooks/taskflow-session.js" "$CLAUDE_DIR/statusline-taskflow.sh"
  # strip the markered CLAUDE.md block
  if [ -f "$CLAUDE_MD" ] && grep -q "megai:task-flow:begin" "$CLAUDE_MD" 2>/dev/null; then
    tmp="$(mktemp)"
    sed '/<!-- megai:task-flow:begin -->/,/<!-- megai:task-flow:end -->/d' "$CLAUDE_MD" > "$tmp" && mv "$tmp" "$CLAUDE_MD"
  fi
  if command -v jq >/dev/null 2>&1 && [ -f "$SETTINGS" ]; then
    tmp="$(mktemp)"
    jq '
      (.hooks.PostToolUse) |= ( (. // []) | map(select(
        ([.hooks[]?.command // ""] | map(test("task-state.js")) | any) | not
      )) ) |
      (.hooks.SessionStart) |= ( (. // []) | map(select(
        ([.hooks[]?.command // ""] | map(test("taskflow-session.js")) | any) | not
      )) ) |
      if (.statusLine.command // "") | test("statusline-taskflow.sh") then del(.statusLine) else . end
    ' "$SETTINGS" > "$tmp" && mv "$tmp" "$SETTINGS"
  fi
  ok "task-flow: removed from $CLAUDE_DIR"
  exit 0
fi

[ -d "$SRC" ] || { warn "task-flow source missing ($SRC) — skipped"; exit 0; }

mkdir -p "$CLAUDE_DIR/skills/task-flow" "$CLAUDE_DIR/hooks"
cp -f "$SRC/skills/task-flow/SKILL.md"  "$CLAUDE_DIR/skills/task-flow/SKILL.md"
cp -f "$SRC/hooks/task-state.js"        "$CLAUDE_DIR/hooks/task-state.js"
cp -f "$SRC/hooks/taskflow-session.js"  "$CLAUDE_DIR/hooks/taskflow-session.js"
cp -f "$SRC/bin/statusline-taskflow.sh" "$CLAUDE_DIR/statusline-taskflow.sh"
chmod +x "$CLAUDE_DIR/statusline-taskflow.sh" 2>/dev/null || true
ok "task-flow: skill + hook + statusline copied -> $CLAUDE_DIR"

# Always-on rule in CLAUDE.md (markered, idempotent).
if [ -f "$CLAUDE_MD" ] && grep -q "megai:task-flow:begin" "$CLAUDE_MD" 2>/dev/null; then
  ok "task-flow: CLAUDE.md rule already present"
else
  { [ -f "$CLAUDE_MD" ] && echo ""; cat "$SRC/CLAUDE.snippet.md"; } >> "$CLAUDE_MD"
  ok "task-flow: always-on rule added to CLAUDE.md"
fi

if ! command -v jq >/dev/null 2>&1; then
  warn "jq missing — settings.json not auto-wired (hook + statusline). Re-run after installing jq."
  state_set '.tools["task-flow"]' "{\"skill\":\"$CLAUDE_DIR/skills/task-flow/SKILL.md\",\"wired\":false}"
  exit 0
fi

[ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"
mkdir -p "$MEGAI_HOME/backups"
cp "$SETTINGS" "$MEGAI_HOME/backups/settings.json.bak.$(date +%s)" 2>/dev/null || true

NODE_BIN="$(command -v node || echo node)"
HOOK_CMD="$NODE_BIN \"$CLAUDE_DIR/hooks/task-state.js\""
SESS_CMD="$NODE_BIN \"$CLAUDE_DIR/hooks/taskflow-session.js\""
SL_CMD="bash \"$CLAUDE_DIR/statusline-taskflow.sh\""

# 1) PostToolUse hook for TaskCreate|TaskUpdate (idempotent by command match).
already="$(jq '[.. | objects | .command? // empty] | map(select(test("task-state.js"))) | length' "$SETTINGS" 2>/dev/null || echo 0)"
if [ "${already:-0}" = "0" ]; then
  tmp="$(mktemp)"
  jq --arg cmd "$HOOK_CMD" '
    .hooks = (.hooks // {}) |
    .hooks.PostToolUse = ((.hooks.PostToolUse // []) + [
      { "matcher": "TaskCreate|TaskUpdate",
        "hooks": [ { "type": "command", "command": $cmd, "timeout": 5 } ] }
    ])
  ' "$SETTINGS" > "$tmp" && mv "$tmp" "$SETTINGS"
  ok "task-flow: PostToolUse hook registered"
else
  ok "task-flow: hook already registered"
fi

# 2) SessionStart hook — ensure/init the .todos board on every new session.
sess_already="$(jq '[.. | objects | .command? // empty] | map(select(test("taskflow-session.js"))) | length' "$SETTINGS" 2>/dev/null || echo 0)"
if [ "${sess_already:-0}" = "0" ]; then
  tmp="$(mktemp)"
  jq --arg cmd "$SESS_CMD" '
    .hooks = (.hooks // {}) |
    .hooks.SessionStart = ((.hooks.SessionStart // []) + [
      { "hooks": [ { "type": "command", "command": $cmd, "timeout": 5 } ] }
    ])
  ' "$SETTINGS" > "$tmp" && mv "$tmp" "$SETTINGS"
  ok "task-flow: SessionStart board hook registered"
else
  ok "task-flow: SessionStart hook already registered"
fi

# 3) statusLine — only set when the user has none, never clobber an existing one.
has_sl="$(jq 'has("statusLine")' "$SETTINGS" 2>/dev/null || echo false)"
if [ "$has_sl" != "true" ]; then
  tmp="$(mktemp)"
  jq --arg c "$SL_CMD" '.statusLine = { "type": "command", "command": $c }' "$SETTINGS" > "$tmp" && mv "$tmp" "$SETTINGS"
  ok "task-flow: board statusline enabled"
else
  warn "task-flow: existing statusLine kept — board view available via $CLAUDE_DIR/statusline-taskflow.sh"
fi

state_set '.tools["task-flow"]' "{\"skill\":\"$CLAUDE_DIR/skills/task-flow/SKILL.md\",\"hook\":\"$CLAUDE_DIR/hooks/task-state.js\",\"wired\":true}"
ok "task-flow ready"

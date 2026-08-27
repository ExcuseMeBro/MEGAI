#!/usr/bin/env bash
# task-flow — pure `.todos` board + full-ADLC protocol for Claude Code.
# The .todos/{todo,inprogress,done}.md files are the single source of truth.
# Installs: the skill, a SessionStart board-init hook, a UserPromptSubmit
# order-enforcer hook, the `/ta` add command, and a board statusline.
# Idempotent and non-destructive (an existing statusLine is never overwritten).
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
  rm -f "$CLAUDE_DIR/hooks/taskflow-session.js" \
        "$CLAUDE_DIR/hooks/taskflow-prompt.sh" \
        "$CLAUDE_DIR/hooks/taskflow-monitor.js" \
        "$CLAUDE_DIR/hooks/taskflow-move.js" \
        "$CLAUDE_DIR/hooks/task-state.js" \
        "$CLAUDE_DIR/bin/taskflow-add.sh" \
        "$CLAUDE_DIR/commands/ta.md" \
        "$CLAUDE_DIR/commands/ts.md" \
        "$CLAUDE_DIR/commands/td.md" \
        "$CLAUDE_DIR/commands/tp.md" \
        "$CLAUDE_DIR/commands/tg.md" \
        "$CLAUDE_DIR/statusline-taskflow.sh"
  if [ -f "$CLAUDE_MD" ] && grep -q "megai:task-flow:begin" "$CLAUDE_MD" 2>/dev/null; then
    tmp="$(mktemp)"
    sed '/<!-- megai:task-flow:begin -->/,/<!-- megai:task-flow:end -->/d' "$CLAUDE_MD" > "$tmp" && mv "$tmp" "$CLAUDE_MD"
  fi
  if command -v jq >/dev/null 2>&1 && [ -f "$SETTINGS" ]; then
    tmp="$(mktemp)"
    jq '
      (.hooks.PostToolUse) |= ( (. // []) | map(select(
        ([.hooks[]?.command // ""] | map(test("task-state.js|taskflow-monitor.js")) | any) | not
      )) ) |
      (.hooks.SessionStart) |= ( (. // []) | map(select(
        ([.hooks[]?.command // ""] | map(test("taskflow-session.js")) | any) | not
      )) ) |
      (.hooks.UserPromptSubmit) |= ( (. // []) | map(select(
        ([.hooks[]?.command // ""] | map(test("taskflow-prompt.sh")) | any) | not
      )) ) |
      if (.statusLine.command // "") | test("statusline-taskflow.sh") then del(.statusLine) else . end
    ' "$SETTINGS" > "$tmp" && mv "$tmp" "$SETTINGS"
  fi
  ok "task-flow: removed from $CLAUDE_DIR"
  exit 0
fi

[ -d "$SRC" ] || { warn "task-flow source missing ($SRC) — skipped"; exit 0; }

mkdir -p "$CLAUDE_DIR/skills/task-flow" "$CLAUDE_DIR/hooks" "$CLAUDE_DIR/bin" "$CLAUDE_DIR/commands"
cp -f "$SRC/skills/task-flow/SKILL.md"  "$CLAUDE_DIR/skills/task-flow/SKILL.md"
cp -f "$SRC/hooks/taskflow-session.js"  "$CLAUDE_DIR/hooks/taskflow-session.js"
cp -f "$SRC/hooks/taskflow-prompt.sh"   "$CLAUDE_DIR/hooks/taskflow-prompt.sh"
cp -f "$SRC/hooks/taskflow-monitor.js"  "$CLAUDE_DIR/hooks/taskflow-monitor.js"
cp -f "$SRC/hooks/taskflow-move.js"     "$CLAUDE_DIR/hooks/taskflow-move.js"
cp -f "$SRC/bin/taskflow-add.sh"        "$CLAUDE_DIR/bin/taskflow-add.sh"
cp -f "$SRC/bin/statusline-taskflow.sh" "$CLAUDE_DIR/statusline-taskflow.sh"
cp -f "$SRC/commands/"*.md              "$CLAUDE_DIR/commands/"
chmod +x "$CLAUDE_DIR/statusline-taskflow.sh" "$CLAUDE_DIR/hooks/taskflow-prompt.sh" "$CLAUDE_DIR/bin/taskflow-add.sh" 2>/dev/null || true
# Drop the legacy Task-tools mirror hook — the board is the single source now.
rm -f "$CLAUDE_DIR/hooks/task-state.js"
ok "task-flow: skill + hooks + /ta command + statusline copied -> $CLAUDE_DIR"

# Always refresh the managed CLAUDE.md rule so policy improvements replace
# stale installs without disturbing user-authored content around the block.
if [ -f "$CLAUDE_MD" ] && grep -q "megai:task-flow:begin" "$CLAUDE_MD" 2>/dev/null; then
  tmp="$(mktemp)"
  awk -v replacement="$SRC/CLAUDE.snippet.md" '
    /<!-- megai:task-flow:begin -->/ {
      if (!emitted) {
        while ((getline line < replacement) > 0) print line
        close(replacement)
        emitted=1
      }
      skip=1
      next
    }
    skip && /<!-- megai:task-flow:end -->/ { skip=0; next }
    !skip { print }
  ' "$CLAUDE_MD" >"$tmp" && mv "$tmp" "$CLAUDE_MD"
  ok "task-flow: CLAUDE.md rule refreshed"
else
  { [ -f "$CLAUDE_MD" ] && echo ""; cat "$SRC/CLAUDE.snippet.md"; } >>"$CLAUDE_MD"
  ok "task-flow: always-on rule added to CLAUDE.md"
fi

if ! command -v jq >/dev/null 2>&1; then
  warn "jq missing — settings.json not auto-wired (hooks + statusline). Re-run after installing jq."
  state_set '.tools["task-flow"]' "{\"skill\":\"$CLAUDE_DIR/skills/task-flow/SKILL.md\",\"wired\":false}"
  exit 0
fi

[ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"
mkdir -p "$MEGAI_HOME/backups"
cp "$SETTINGS" "$MEGAI_HOME/backups/settings.json.bak.$(date +%s)" 2>/dev/null || true

NODE_BIN="$(command -v node || echo node)"
SESS_CMD="$NODE_BIN \"$CLAUDE_DIR/hooks/taskflow-session.js\""
PROMPT_CMD="bash \"$CLAUDE_DIR/hooks/taskflow-prompt.sh\""
MON_CMD="$NODE_BIN \"$CLAUDE_DIR/hooks/taskflow-monitor.js\""
SL_CMD="bash \"$CLAUDE_DIR/statusline-taskflow.sh\""

# Drop any legacy PostToolUse task-state.js hook from prior versions (pure .todos now).
tmp="$(mktemp)"
jq '(.hooks.PostToolUse) |= ( (. // []) | map(select(
      ([.hooks[]?.command // ""] | map(test("task-state.js")) | any) | not )) )' \
  "$SETTINGS" > "$tmp" && mv "$tmp" "$SETTINGS"

# 1) SessionStart hook — ensure/init the .todos board on every new session.
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

# 2) UserPromptSubmit hook — analyze prompt -> create task first -> run ADLC.
prompt_already="$(jq '[.. | objects | .command? // empty] | map(select(test("taskflow-prompt.sh"))) | length' "$SETTINGS" 2>/dev/null || echo 0)"
if [ "${prompt_already:-0}" = "0" ]; then
  tmp="$(mktemp)"
  jq --arg cmd "$PROMPT_CMD" '
    .hooks = (.hooks // {}) |
    .hooks.UserPromptSubmit = ((.hooks.UserPromptSubmit // []) + [
      { "hooks": [ { "type": "command", "command": $cmd, "timeout": 5 } ] }
    ])
  ' "$SETTINGS" > "$tmp" && mv "$tmp" "$SETTINGS"
  ok "task-flow: UserPromptSubmit (analyze->task->ADLC) hook registered"
else
  ok "task-flow: UserPromptSubmit hook already registered"
fi

# 3) PostToolUse hook — regenerate .todos/monitoring.md when the board changes.
mon_already="$(jq '[.. | objects | .command? // empty] | map(select(test("taskflow-monitor.js"))) | length' "$SETTINGS" 2>/dev/null || echo 0)"
if [ "${mon_already:-0}" = "0" ]; then
  tmp="$(mktemp)"
  jq --arg cmd "$MON_CMD" '
    .hooks = (.hooks // {}) |
    .hooks.PostToolUse = ((.hooks.PostToolUse // []) + [
      { "matcher": "Edit|Write|MultiEdit",
        "hooks": [ { "type": "command", "command": $cmd, "timeout": 5 } ] }
    ])
  ' "$SETTINGS" > "$tmp" && mv "$tmp" "$SETTINGS"
  ok "task-flow: monitoring.md auto-update hook registered"
else
  ok "task-flow: monitoring hook already registered"
fi

# 4) statusLine — only set when the user has none, never clobber an existing one.
has_sl="$(jq 'has("statusLine")' "$SETTINGS" 2>/dev/null || echo false)"
if [ "$has_sl" != "true" ]; then
  tmp="$(mktemp)"
  jq --arg c "$SL_CMD" '.statusLine = { "type": "command", "command": $c }' "$SETTINGS" > "$tmp" && mv "$tmp" "$SETTINGS"
  ok "task-flow: board statusline enabled"
else
  warn "task-flow: existing statusLine kept — board view available via $CLAUDE_DIR/statusline-taskflow.sh"
fi

state_set '.tools["task-flow"]' "{\"skill\":\"$CLAUDE_DIR/skills/task-flow/SKILL.md\",\"command\":\"/ta\",\"wired\":true}"
ok "task-flow ready"

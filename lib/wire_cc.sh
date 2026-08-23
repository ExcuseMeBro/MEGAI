#!/usr/bin/env bash
# Wire MCP servers into Claude Code config (~/.claude.json).
# Idempotent: keeps user's other mcpServers untouched, only manages megai-owned keys.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

CC_CONFIG="$HOME/.claude.json"
MODE="${1:-install}" # install | --remove

if ! command -v jq >/dev/null 2>&1; then
  warn "jq missing — skipping cc wire"
  exit 0
fi

[ -f "$CC_CONFIG" ] || echo '{}' >"$CC_CONFIG"

# backup
mkdir -p "$MEGAI_HOME/backups"
backup="$(mktemp "$MEGAI_HOME/backups/claude.json.bak.XXXXXX")"
cp "$CC_CONFIG" "$backup"

if [ "$MODE" = "--remove" ]; then
  tmp="$(mktemp)"
  jq 'del(.mcpServers.agentmemory, .mcpServers.codedb, .mcpServers["megai-dembrandt"], .mcpServers["megai-argent"], .mcpServers["megai-repowise"])' "$CC_CONFIG" >"$tmp" && mv "$tmp" "$CC_CONFIG"
  ok "cc: megai mcpServers removed"
  exit 0
fi

# Build megai mcpServers block
AGM_PORT="$(state_get '.ports["agent-memory"]')"
AGM_PORT="${AGM_PORT:-3111}"
AGM_BIN="$(state_get '.tools["agent-memory"].bin')"
CODEDB_BIN="$(state_get '.tools["codedb"].bin')"
DEMBRANDT_MCP_BIN="$(state_get '.tools["dembrandt"].mcpBin')"
ARGENT_BIN="$(state_get '.tools["argent"].bin')"
REPOWISE_BIN="$(state_get '.tools["repowise"].bin')"

mcp_block=$(
  cat <<EOF
{
  "agentmemory": {
    "command": "${AGM_BIN:-agentmemory}",
    "args": ["mcp"],
    "env": { "AGENTMEMORY_URL": "http://127.0.0.1:$AGM_PORT" }
  },
  "codedb": {
    "command": "${CODEDB_BIN:-codedb}",
    "args": ["mcp"]
  }
}
EOF
)

if [ -n "$DEMBRANDT_MCP_BIN" ] && [ -x "$DEMBRANDT_MCP_BIN" ]; then
  mcp_block="$(jq --arg command "$DEMBRANDT_MCP_BIN" '. + {"megai-dembrandt": {command: $command}}' <<<"$mcp_block")"
else
  warn "cc: Dembrandt MCP skipped — executable missing"
fi
if [ -n "$ARGENT_BIN" ] && [ -x "$ARGENT_BIN" ]; then
  mcp_block="$(jq --arg command "$ARGENT_BIN" '. + {"megai-argent": {command: $command, args: ["mcp"]}}' <<<"$mcp_block")"
else
  warn "cc: Argent MCP skipped — executable missing"
fi
if [ -n "$REPOWISE_BIN" ] && [ -x "$REPOWISE_BIN" ]; then
  mcp_block="$(jq --arg command "$REPOWISE_BIN" '. + {"megai-repowise": {command: $command, args: ["mcp"]}}' <<<"$mcp_block")"
else
  warn "cc: RepoWise MCP skipped — executable missing"
fi

tmp="$(mktemp)"
jq --argjson add "$mcp_block" '
  .mcpServers = (((.mcpServers // {}) | del(.["megai-dembrandt"], .["megai-argent"], .["megai-repowise"])) + $add)
' "$CC_CONFIG" >"$tmp" && mv "$tmp" "$CC_CONFIG"

ok "cc: available megai mcpServers wired"
state_set '.agents["cc"]' "{\"config\":\"$CC_CONFIG\",\"wired\":true}"

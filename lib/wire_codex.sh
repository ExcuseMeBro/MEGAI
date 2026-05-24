#!/usr/bin/env bash
# Wire MCP servers into Codex CLI config (~/.codex/config.toml).
# Uses marker block strategy because we don't bundle a TOML parser.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

CX_DIR="$HOME/.codex"
CX_FILE="$CX_DIR/config.toml"
MODE="${1:-install}"
MARK_BEG="# >>> megai-managed (do not edit) >>>"
MARK_END="# <<< megai-managed <<<"

mkdir -p "$CX_DIR"
[ -f "$CX_FILE" ] || : > "$CX_FILE"

# backup
ts="$(date +%s)"
cp "$CX_FILE" "$MEGAI_HOME/backups/codex.config.toml.bak.$ts"

strip_block() {
  awk -v b="$MARK_BEG" -v e="$MARK_END" '
    $0==b { skip=1; next }
    $0==e { skip=0; next }
    !skip { print }
  ' "$CX_FILE"
}

stripped="$(strip_block)"

if [ "$MODE" = "--remove" ]; then
  printf "%s\n" "$stripped" > "$CX_FILE"
  ok "codex: megai block removed"
  exit 0
fi

AGM_BIN="$(state_get '.tools["agent-memory"].bin')";  AGM_BIN="${AGM_BIN:-agentmemory}"
AGM_PORT="$(state_get '.ports["agent-memory"]')";     AGM_PORT="${AGM_PORT:-3111}"
CODEDB_BIN="$(state_get '.tools["codedb"].bin')";     CODEDB_BIN="${CODEDB_BIN:-codedb}"

{
  printf "%s\n" "$stripped"
  printf "\n%s\n" "$MARK_BEG"
  cat <<EOF
[mcp_servers.agentmemory]
command = "$AGM_BIN"
args    = ["mcp"]
env     = { AGENTMEMORY_PORT = "$AGM_PORT" }

[mcp_servers.codedb]
command = "$CODEDB_BIN"
args    = ["mcp"]
EOF
  printf "%s\n" "$MARK_END"
} > "$CX_FILE"

ok "codex: marker block written -> $CX_FILE"
state_set '.agents["codex"]' "{\"config\":\"$CX_FILE\",\"wired\":true}"

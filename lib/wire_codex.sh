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
[ -f "$CX_FILE" ] || : >"$CX_FILE"

# backup
mkdir -p "$MEGAI_HOME/backups"
backup="$(mktemp "$MEGAI_HOME/backups/codex.config.toml.bak.XXXXXX")"
cp "$CX_FILE" "$backup"

strip_block() {
  awk -v b="$MARK_BEG" -v e="$MARK_END" '
    function owned(section) {
      return section == "mcp_servers.agentmemory" \
        || index(section, "mcp_servers.agentmemory.") == 1 \
        || section == "mcp_servers.codedb" \
        || index(section, "mcp_servers.codedb.") == 1 \
        || section == "mcp_servers.megai-dembrandt" \
        || index(section, "mcp_servers.megai-dembrandt.") == 1 \
        || section == "mcp_servers.megai-argent" \
        || index(section, "mcp_servers.megai-argent.") == 1 \
        || section == "mcp_servers.megai-repowise" \
        || index(section, "mcp_servers.megai-repowise.") == 1
    }
    $0==b || $0==e { next }
    /^\[[^]]+\][[:space:]]*$/ {
      section=$0
      sub(/^\[/, "", section)
      sub(/\][[:space:]]*$/, "", section)
      drop=owned(section)
    }
    !drop { print }
  ' "$CX_FILE"
}

stripped="$(strip_block)"

if [ "$MODE" = "--remove" ]; then
  printf "%s\n" "$stripped" >"$CX_FILE"
  ok "codex: megai block removed"
  exit 0
fi

AGM_BIN="$(state_get '.tools["agent-memory"].bin')"
AGM_BIN="${AGM_BIN:-agentmemory}"
AGM_PORT="$(state_get '.ports["agent-memory"]')"
AGM_PORT="${AGM_PORT:-3111}"
CODEDB_BIN="$(state_get '.tools["codedb"].bin')"
CODEDB_BIN="${CODEDB_BIN:-codedb}"
DEMBRANDT_MCP_BIN="$(state_get '.tools["dembrandt"].mcpBin')"
ARGENT_BIN="$(state_get '.tools["argent"].bin')"
REPOWISE_BIN="$(state_get '.tools["repowise"].bin')"
[ -n "$DEMBRANDT_MCP_BIN" ] && [ -x "$DEMBRANDT_MCP_BIN" ] || warn "codex: Dembrandt MCP skipped — executable missing"
[ -n "$ARGENT_BIN" ] && [ -x "$ARGENT_BIN" ] || warn "codex: Argent MCP skipped — executable missing"
[ -n "$REPOWISE_BIN" ] && [ -x "$REPOWISE_BIN" ] || warn "codex: RepoWise MCP skipped — executable missing"

{
  printf "%s\n" "$stripped"
  printf "\n%s\n" "$MARK_BEG"
  cat <<EOF
[mcp_servers.agentmemory]
command = "$AGM_BIN"
args    = ["mcp"]
env     = { AGENTMEMORY_URL = "http://127.0.0.1:$AGM_PORT" }

[mcp_servers.codedb]
command = "$CODEDB_BIN"
args    = ["mcp"]
EOF
  if [ -n "$DEMBRANDT_MCP_BIN" ] && [ -x "$DEMBRANDT_MCP_BIN" ]; then
    cat <<EOF

[mcp_servers.megai-dembrandt]
command = "$DEMBRANDT_MCP_BIN"
EOF
  fi
  if [ -n "$ARGENT_BIN" ] && [ -x "$ARGENT_BIN" ]; then
    cat <<EOF

[mcp_servers.megai-argent]
command = "$ARGENT_BIN"
args    = ["mcp"]
EOF
  fi
  if [ -n "$REPOWISE_BIN" ] && [ -x "$REPOWISE_BIN" ]; then
    cat <<EOF

[mcp_servers.megai-repowise]
command = "$REPOWISE_BIN"
args    = ["mcp"]
EOF
  fi
  printf "%s\n" "$MARK_END"
} >"$CX_FILE"

ok "codex: marker block written -> $CX_FILE"
state_set '.agents["codex"]' "{\"config\":\"$CX_FILE\",\"wired\":true}"

#!/usr/bin/env bash
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=detect.sh
. "$MEGAI_HOME/lib/detect.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

if command -v agentmemory >/dev/null 2>&1; then
  ok "agent-memory already installed -> $(command -v agentmemory)"
else
  npm install -g @agentmemory/agentmemory >/dev/null 2>&1 || die "agent-memory npm install failed"
  ok "agent-memory installed"
fi

port="$(state_get '.ports["agent-memory"]')"
if ! [[ "$port" =~ ^[0-9]+$ ]]; then
  port="$(find_free_port 3111)"
elif ! AGENTMEMORY_URL="http://127.0.0.1:$port" agentmemory status >/dev/null 2>&1 &&
  lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
  warn "agent-memory port $port is occupied — selecting a free port"
  port="$(find_free_port 3111)"
fi
bin="$(command -v agentmemory || true)"
ver="$(agentmemory --version 2>/dev/null | head -n1 || echo "")"

state_set '.tools["agent-memory"]' "{\"bin\":\"$bin\",\"version\":\"$ver\",\"port\":$port}"
state_set '.ports["agent-memory"]' "$port"
ok "agent-memory port: $port"

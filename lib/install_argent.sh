#!/usr/bin/env bash
# Argent — agent-driven mobile, TV, Electron, and browser testing via CLI + MCP.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

if [ "${MEGAI_UPDATE:-0}" = "1" ]; then
  npm install -g @swmansion/argent@latest >/dev/null 2>&1 || {
    warn "Argent update failed — keeping current version"
    exit 0
  }
  hash -r
  ok "Argent updated"
elif command -v argent >/dev/null 2>&1; then
  ok "Argent already installed -> $(command -v argent)"
else
  npm install -g @swmansion/argent@latest >/dev/null 2>&1 || {
    warn "Argent npm install failed — skipping"
    exit 0
  }
  hash -r
  ok "Argent installed"
fi

bin="$(command -v argent || echo "")"
ver="$(argent --version 2>/dev/null | head -n1 || echo "")"
state_set '.tools["argent"]' "{\"bin\":\"$bin\",\"version\":\"$ver\"}"

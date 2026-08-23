#!/usr/bin/env bash
# Dembrandt — website design-system extraction CLI + MCP server.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

if [ "${MEGAI_UPDATE:-0}" = "1" ]; then
  npm install -g dembrandt@latest >/dev/null 2>&1 || { warn "dembrandt update failed — keeping current version"; exit 0; }
  hash -r
  ok "dembrandt updated"
elif command -v dembrandt >/dev/null 2>&1 && command -v dembrandt-mcp >/dev/null 2>&1; then
  ok "dembrandt already installed -> $(command -v dembrandt)"
else
  npm install -g dembrandt >/dev/null 2>&1 || { warn "dembrandt npm install failed — skipping"; exit 0; }
  hash -r
  ok "dembrandt installed"
fi

# The npm package intentionally ships without a browser binary.
dembrandt install-browser >/dev/null 2>&1 \
  && ok "dembrandt Chromium ready" \
  || warn "dembrandt browser install failed — retry later with: dembrandt install-browser"

bin="$(command -v dembrandt || echo "")"
mcp_bin="$(command -v dembrandt-mcp || echo "")"
ver="$(dembrandt --version 2>/dev/null | head -n1 || echo "")"
state_set '.tools["dembrandt"]' "{\"bin\":\"$bin\",\"mcpBin\":\"$mcp_bin\",\"version\":\"$ver\"}"

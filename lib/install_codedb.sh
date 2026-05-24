#!/usr/bin/env bash
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

if command -v codedb >/dev/null 2>&1; then
  ok "codedb already installed -> $(command -v codedb)"
else
  # Upstream installer auto-registers MCP for cc/codex/gemini/cursor.
  # We let it run, then re-wire via our own wiring scripts to keep megai-managed markers.
  curl -fsSL https://codedb.codegraff.com/install.sh | bash >/dev/null 2>&1 \
    || { warn "codedb installer failed — try manual: curl -fsSL https://codedb.codegraff.com/install.sh | bash"; exit 0; }
  hash -r
  ok "codedb installed"
fi

bin="$(command -v codedb || true)"
ver="$(codedb --version 2>/dev/null | head -n1 || echo "")"
state_set '.tools["codedb"]' "{\"bin\":\"$bin\",\"version\":\"$ver\"}"

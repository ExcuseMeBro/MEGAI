#!/usr/bin/env bash
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

if command -v fn >/dev/null 2>&1; then
  ok "fusion already installed -> $(command -v fn)"
else
  npm install -g @runfusion/fusion >/dev/null 2>&1 || { warn "fusion npm install failed (non-fatal)"; exit 0; }
  ok "fusion installed"
fi

bin="$(command -v fn || true)"
ver="$(fn --version 2>/dev/null | head -n1 || echo "")"
state_set '.tools["fusion"]' "{\"bin\":\"$bin\",\"version\":\"$ver\"}"

#!/usr/bin/env bash
# caveman — token-compression skill that self-installs into Claude Code / Codex / Pi / Cursor.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

if command -v caveman >/dev/null 2>&1; then
  ok "caveman already installed -> $(command -v caveman)"
else
  curl -fsSL https://raw.githubusercontent.com/JuliusBrussee/caveman/main/install.sh | bash \
    || { warn "caveman installer failed (non-fatal)"; exit 0; }
  ok "caveman installed"
fi

bin="$(command -v caveman || echo "")"
ver="$(caveman --version 2>/dev/null | head -n1 || echo "")"
state_set '.tools["caveman"]' "{\"bin\":\"$bin\",\"version\":\"$ver\"}"

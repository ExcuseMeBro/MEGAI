#!/usr/bin/env bash
# ui-craft — design-system installer for AI coding harnesses (educlopez/tap/ui-craft).
# Static installer: detects cc/codex/cursor/gemini/opencode and writes ui-craft
# skill+commands, MCP gates, review agents, and design-memory into each.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

if command -v ui-craft >/dev/null 2>&1; then
  ok "ui-craft already installed -> $(command -v ui-craft)"
else
  if command -v brew >/dev/null 2>&1; then
    brew install --cask educlopez/tap/ui-craft >/dev/null 2>&1 || true
  fi
  if ! command -v ui-craft >/dev/null 2>&1; then
    warn "ui-craft install failed — needs Homebrew (brew install --cask educlopez/tap/ui-craft). Skipping."
    exit 0
  fi
  hash -r
  ok "ui-craft installed"
fi

# Wire ui-craft components into every detected harness (idempotent).
ui-craft install --yes --quiet >/dev/null 2>&1 \
  && ok "ui-craft components wired into detected harnesses" \
  || warn "ui-craft install (component wiring) failed — re-run later with: ui-craft install --yes"

bin="$(command -v ui-craft || echo "")"
ver="$(ui-craft version 2>/dev/null | head -n1 || echo "")"
state_set '.tools["ui-craft"]' "{\"bin\":\"$bin\",\"version\":\"$ver\"}"

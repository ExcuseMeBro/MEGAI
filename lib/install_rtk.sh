#!/usr/bin/env bash
# rtk — Rust Token Killer. Single Rust binary that proxies/compresses dev command outputs.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

# Detect collision with the unrelated reachingforthejack/rtk (Rust Type Kit).
collision=0
if command -v rtk >/dev/null 2>&1; then
  if rtk gain >/dev/null 2>&1; then
    ok "rtk-ai already installed -> $(command -v rtk)"
  else
    warn "rtk binary found but 'rtk gain' failed — possible collision with another 'rtk' tool. Skipping."
    collision=1
  fi
else
  if command -v brew >/dev/null 2>&1; then
    brew install rtk >/dev/null 2>&1 || true
  fi
  if ! command -v rtk >/dev/null 2>&1; then
    curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh \
      || { warn "rtk installer failed (non-fatal)"; exit 0; }
  fi
  ok "rtk installed"
fi

# Register Claude Code PreToolUse hook (rtk's own command — idempotent).
if [ "$collision" = "0" ] && command -v rtk >/dev/null 2>&1; then
  rtk init -g >/dev/null 2>&1 && ok "rtk Claude Code hook registered" \
    || warn "rtk init -g failed (non-fatal)"
fi

bin="$(command -v rtk || echo "")"
ver="$(rtk --version 2>/dev/null | head -n1 || echo "")"
state_set '.tools["rtk"]' "{\"bin\":\"$bin\",\"version\":\"$ver\"}"

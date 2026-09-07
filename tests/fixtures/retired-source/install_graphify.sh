#!/usr/bin/env bash
# graphify — open-source knowledge-graph skill for AI coding assistants.
# PyPI package: graphifyy (double-y). CLI binary: graphify.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

if command -v graphify >/dev/null 2>&1; then
  ok "graphify already installed -> $(command -v graphify)"
else
  if command -v uv >/dev/null 2>&1; then
    uv tool install graphifyy >/dev/null 2>&1 || warn "uv tool install graphifyy failed"
  elif command -v pipx >/dev/null 2>&1; then
    pipx install graphifyy >/dev/null 2>&1 || warn "pipx install graphifyy failed"
  elif command -v python3 >/dev/null 2>&1; then
    venv="$MEGAI_HOME/venv/graphify"
    mkdir -p "$(dirname "$venv")"
    python3 -m venv "$venv"
    "$venv/bin/pip" install -U pip wheel >/dev/null 2>&1 || true
    "$venv/bin/pip" install graphifyy >/dev/null 2>&1 || { warn "pip install graphifyy failed"; exit 0; }
    ln -sf "$venv/bin/graphify" "$MEGAI_HOME/bin/graphify"
  else
    warn "no Python toolchain — graphify skipped"
    exit 0
  fi
  hash -r
  ok "graphify installed"
fi

# Register graphify as a skill with each detected AI assistant.
# graphify install scans for cc/codex/cursor/etc configs and writes its skill.
if command -v graphify >/dev/null 2>&1; then
  graphify install >/dev/null 2>&1 \
    && ok "graphify skill registered with detected AI assistants" \
    || warn "graphify install (skill registration) failed — re-run later with: graphify install"
fi

bin="$(command -v graphify || echo "$MEGAI_HOME/bin/graphify")"
ver="$("$bin" --version 2>/dev/null | head -n1 || echo "")"
state_set '.tools["graphify"]' "{\"bin\":\"$bin\",\"version\":\"$ver\"}"

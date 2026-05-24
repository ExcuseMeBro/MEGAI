#!/usr/bin/env bash
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

if command -v cocoindex >/dev/null 2>&1; then
  ok "cocoindex already installed -> $(command -v cocoindex)"
  bin="$(command -v cocoindex)"
  ver="$(cocoindex --version 2>/dev/null | head -n1 || echo "")"
  state_set '.tools["cocoindex"]' "{\"bin\":\"$bin\",\"version\":\"$ver\"}"
  exit 0
fi

if command -v pipx >/dev/null 2>&1; then
  pipx install cocoindex >/dev/null 2>&1 || warn "pipx install cocoindex failed"
elif command -v python3 >/dev/null 2>&1; then
  venv="$MEGAI_HOME/venv/cocoindex"
  mkdir -p "$(dirname "$venv")"
  python3 -m venv "$venv"
  "$venv/bin/pip" install -U pip wheel >/dev/null 2>&1 || true
  "$venv/bin/pip" install cocoindex >/dev/null 2>&1 || { warn "cocoindex pip install failed"; exit 0; }
  ln -sf "$venv/bin/cocoindex" "$MEGAI_HOME/bin/cocoindex"
else
  warn "python3 missing — cocoindex skipped"
  exit 0
fi

hash -r
bin="$(command -v cocoindex || echo "$MEGAI_HOME/bin/cocoindex")"
ver="$("$bin" --version 2>/dev/null | head -n1 || echo "")"
state_set '.tools["cocoindex"]' "{\"bin\":\"$bin\",\"version\":\"$ver\"}"
ok "cocoindex installed -> $bin"

#!/usr/bin/env bash
# RepoWise — local codebase intelligence, health, wiki, and MCP server.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

if [ "${MEGAI_UPDATE:-0}" = "1" ] && command -v repowise >/dev/null 2>&1; then
  if command -v uv >/dev/null 2>&1 && uv tool list 2>/dev/null | grep -q '^repowise '; then
    uv tool upgrade repowise >/dev/null 2>&1 || warn "RepoWise update failed — keeping current version"
  elif command -v pipx >/dev/null 2>&1 && pipx list --short 2>/dev/null | grep -q '^repowise '; then
    pipx upgrade repowise >/dev/null 2>&1 || warn "RepoWise update failed — keeping current version"
  else
    warn "RepoWise is managed outside MEGAI — package update skipped"
  fi
elif ! command -v repowise >/dev/null 2>&1; then
  if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1 \
      || { warn "uv install failed — RepoWise skipped"; exit 0; }
    hash -r
  fi
  uv tool install --python 3.11 repowise >/dev/null 2>&1 \
    || { warn "RepoWise install failed — skipping"; exit 0; }
  hash -r
else
  ok "RepoWise already installed -> $(command -v repowise)"
fi

target="$MEGAI_HOME/bin/repowise"
bin="$(command -v repowise || true)"
if [ "$bin" = "$target" ]; then bin="$(readlink "$target" 2>/dev/null || true)"; fi
[ -n "$bin" ] && [ -x "$bin" ] || { warn "RepoWise installed but binary was not found"; exit 0; }
ln -sf "$bin" "$target"
ver="$("$bin" --version 2>/dev/null | head -n1 || echo "")"
state_set '.tools["repowise"]' "{\"bin\":\"$MEGAI_HOME/bin/repowise\",\"version\":\"$ver\"}"
ok "RepoWise ready -> $bin"

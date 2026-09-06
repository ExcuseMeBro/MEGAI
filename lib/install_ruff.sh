#!/usr/bin/env bash
# ruff — extremely fast Python linter and formatter (uv tool / pipx).
# Reuse any working ruff on PATH; otherwise install via uv tool first, then pipx.
# No remote shell installer / new package manager. Removal clears only MEGAI state;
# the ruff CLI is retained so it stays independently usable.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

# uv puts uv-managed binaries under ~/.local/bin; ensure that is on PATH for
# detection without clobbering an existing ruff found anywhere else.
export PATH="$HOME/.local/bin:$PATH"

clear_state() {
  if [ -f "$STATE_FILE" ]; then
    tmp="$(mktemp "$MEGAI_HOME/.ruff-state.XXXXXX")"
    if ! jq 'del(.tools.ruff)' "$STATE_FILE" >"$tmp"; then
      rm -f "$tmp"
      die "ruff state cleanup failed; reconcile before continuing"
    fi
    mv "$tmp" "$STATE_FILE"
  fi
}

if [ "${1:-}" = "--remove" ]; then
  clear_state
  ok "Ruff metadata cleared; ruff CLI retained"
  exit 0
fi

# 1. Detect existing working ruff anywhere on PATH first.
bin=""
if command -v ruff >/dev/null 2>&1; then
  bin="$(command -v ruff)"
fi

# 2. Update path: refresh a MEGAI-detected uv/pipx install in place; leave
#    out-of-band installs (Homebrew, system, user-owned binary, etc.) alone.
if [ "${MEGAI_UPDATE:-0}" = "1" ] && [ -n "$bin" ]; then
  if command -v uv >/dev/null 2>&1 && uv tool list 2>/dev/null | grep -q '^ruff '; then
    uv tool upgrade ruff >/dev/null 2>&1 \
      || warn "ruff update via uv failed — keeping current version"
    hash -r
  elif command -v pipx >/dev/null 2>&1 && pipx list --short 2>/dev/null | grep -q '^ruff '; then
    pipx upgrade ruff >/dev/null 2>&1 \
      || warn "ruff update via pipx failed — keeping current version"
    hash -r
  else
    skip "ruff is managed outside MEGAI — update skipped"
  fi
  bin="$(command -v ruff || true)"
elif [ -z "$bin" ]; then
  # 3. Fresh install: prefer uv tool, fall back to pipx. Refuse other managers.
  if command -v uv >/dev/null 2>&1; then
    uv tool install ruff >/dev/null 2>&1 \
      || { warn "ruff install via uv failed — skipping"; exit 0; }
    hash -r
  elif command -v pipx >/dev/null 2>&1; then
    pipx install ruff >/dev/null 2>&1 \
      || { warn "ruff install via pipx failed — skipping"; exit 0; }
    hash -r
  else
    die "ruff requires uv or pipx; neither is installed"
  fi
  bin="$(command -v ruff || true)"
fi

# 4. Verify the resolved binary actually reports a version. Never record a
#    failed/unusable install as ready.
[ -n "$bin" ] && [ -x "$bin" ] || { warn "ruff binary unavailable after install"; exit 0; }
version="$(ruff --version 2>/dev/null | head -n1 || true)"
[ -n "$version" ] || { warn "ruff present but --version failed; not recorded"; exit 0; }

# 5. Record provenance so update/removal can find the right manager.
manager="path"
if command -v uv >/dev/null 2>&1 && uv tool list 2>/dev/null | grep -q '^ruff '; then
  manager="uv"
elif command -v pipx >/dev/null 2>&1 && pipx list --short 2>/dev/null | grep -q '^ruff '; then
  manager="pipx"
fi

metadata="$(jq -cn --arg bin "$bin" --arg version "$version" --arg manager "$manager" \
  '{bin:$bin,version:$version,manager:$manager}')"
state_set '.tools.ruff' "$metadata"
ok "Ruff ready -> $bin ($version, manager=$manager)"

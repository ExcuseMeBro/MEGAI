#!/usr/bin/env bash
# ruff — extremely fast Python linter and formatter (uv tool / pipx).
# Reuse any working ruff on the caller's PATH unchanged; never auto-upgrade.
# If absent, install via whichever of uv/pipx is available (uv preferred).
# No chained fallback on install failure, no remote shell installer / new
# package manager, no inferred ownership metadata. Removal clears only MEGAI
# state; the ruff CLI is retained so it stays independently usable.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

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

# 1. Detect a working ruff on the caller's original PATH first. ~/.local/bin
#    is only consulted as a fallback when the caller PATH has nothing — this
#    preserves any caller-selected executable (e.g., a custom PATH shim) and
#    never shadows it with a stale local install.
bin=""
if found="$(command -v ruff 2>/dev/null)"; then
  bin="$found"
elif [ -x "$HOME/.local/bin/ruff" ]; then
  bin="$HOME/.local/bin/ruff"
fi

# 2. Fresh install when nothing is on PATH (uv preferred, pipx as last resort).
#    Auto-upgrades and inferred ownership are intentionally NOT performed: any
#    existing working ruff must stay unchanged, including on `megai update`.
if [ -z "$bin" ]; then
  if command -v uv >/dev/null 2>&1; then
    if ! uv tool install ruff >/dev/null 2>&1; then
      warn "ruff install via uv failed; not recorded"
      exit 1
    fi
    hash -r
  elif command -v pipx >/dev/null 2>&1; then
    if ! pipx install ruff >/dev/null 2>&1; then
      warn "ruff install via pipx failed; not recorded"
      exit 1
    fi
    hash -r
  else
    die "ruff requires uv or pipx; neither is installed"
  fi
  if found="$(command -v ruff 2>/dev/null)"; then
    bin="$found"
  elif [ -x "$HOME/.local/bin/ruff" ]; then
    bin="$HOME/.local/bin/ruff"
  fi
fi

# 3. Verify the resolved binary actually reports a working version. Require a
#    successful exit AND a sensible non-empty `ruff <version>` output. The
#    failure status of `--version` is preserved (no `|| true` swallowing it,
#    no `set -e` short-circuiting the capture).
[ -n "$bin" ] && [ -x "$bin" ] || { warn "ruff binary unavailable after install; not recorded"; exit 1; }
_version_tmp="$(mktemp "$MEGAI_HOME/.ruff-version.XXXXXX")"
# Run `--version` inside an `if` so `set -e` does not short-circuit on the
# nonzero exit; the actual exit code is captured in `version_rc`.
if "$bin" --version >"$_version_tmp" 2>/dev/null; then
  version_rc=0
else
  version_rc=$?
fi
version_out="$(cat "$_version_tmp")"
rm -f "$_version_tmp"
if [ "$version_rc" -ne 0 ] || ! [[ "$version_out" =~ ^ruff[[:space:]]+[^[:space:]]+ ]]; then
  warn "ruff present but --version failed or returned invalid output; not recorded"
  exit 1
fi
version="$(printf '%s\n' "$version_out" | head -n1)"

# 4. Record only bin + version. No inferred manager / ownership metadata.
metadata="$(jq -cn --arg bin "$bin" --arg version "$version" \
  '{bin:$bin,version:$version}')"
state_set '.tools.ruff' "$metadata"
ok "Ruff ready -> $bin ($version)"

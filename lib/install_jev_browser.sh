#!/usr/bin/env bash
# Install the pinned Jev Ultrafast browser agent runner. No vendored copy, no upstream
# hooks, no service start and no credential requirement: keys stay the user's and are
# read only when the agent actually runs.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
export PATH="$PATH:$MEGAI_HOME/bin"
. "$MEGAI_HOME/lib/ui.sh"
. "$MEGAI_HOME/lib/state.sh"
state_init

command -v uv >/dev/null 2>&1 || die "uv is required for the Jev Ultrafast browser agent"

# The clean-profile installer copies only bin/megai, so provision this runner from its
# source checkout when it is not already installed.
if [ ! -x "$MEGAI_HOME/bin/jev-browser" ] && [ -n "${MEGAI_SOURCE:-}" ] && [ -f "$MEGAI_SOURCE/bin/jev-browser" ]; then
  mkdir -p "$MEGAI_HOME/bin"
  install -m 0755 "$MEGAI_SOURCE/bin/jev-browser" "$MEGAI_HOME/bin/jev-browser"
fi
command -v jev-browser >/dev/null 2>&1 || die "bin/jev-browser is missing from $MEGAI_HOME/bin"

# Readiness needs the user's credentials; a missing key is reported, never fatal.
readiness="credentials missing"
prewarm="unknown"
pin="unknown"
if out="$(jev-browser --self-check --prewarm 2>/dev/null)"; then
  readiness="ready"
fi
if printf '%s' "$out" | jq -e . >/dev/null 2>&1; then
  pin="$(printf '%s' "$out" | jq -r '.pin')"
  prewarm="$(printf '%s' "$out" | jq -r '.prewarm')"
fi
uv_version="$(uv --version)"

state_set '.tools["jev-browser"]' "$(jq -cn --arg pin "$pin" --arg uv "$uv_version" \
  --arg readiness "$readiness" --arg prewarm "$prewarm" \
  '{pin:$pin,uv:$uv,readiness:$readiness,prewarm:$prewarm}')"

if [ "$readiness" = ready ] && [ "$prewarm" = ok ]; then
  ok "jev-browser ready -> $MEGAI_HOME/bin/jev-browser (pinned cache warm, $uv_version)"
else
  warn "jev-browser installed -> $MEGAI_HOME/bin/jev-browser; $readiness, uv prewarm: $prewarm"
  warn 'store the TypeSafe key with: security add-generic-password -s typesafe.ai -a "$USER" -w'
fi

#!/usr/bin/env bash
# Compatibility cleanup only: no installation, CLI calls or project changes.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
PI_AGENT="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
SKILL_SOURCE="$MEGAI_HOME/skills/megai-openspec"
DEST="$PI_AGENT/skills/megai-openspec"
. "$MEGAI_HOME/lib/ui.sh"
. "$MEGAI_HOME/lib/state.sh"
[ "$#" -eq 0 ] || die "Usage: retire_openspec.sh"
command -v jq >/dev/null 2>&1 || die "jq required for MEGAI state"
destinations="$(jq -cn --arg dest "$DEST" '[$dest]')"
if [ -f "$STATE_FILE" ]; then
  destinations="$(jq -c --arg dest "$DEST" '[(.tools.openspec.destinations // [])[], $dest] | unique' "$STATE_FILE")"
fi
# Preserve the former installer's removal behavior, including dangling owned
# links and NUL-delimited custom destinations with spaces/newlines.
while IFS= read -r -d '' registered; do
  if [ -L "$registered" ] && [ "$(readlink "$registered")" = "$SKILL_SOURCE" ]; then
    rm "$registered"
  fi
done < <(printf '%s' "$destinations" | jq -j '.[] | ., "\u0000"')
if [ -f "$STATE_FILE" ]; then
  tmp="$(mktemp "$MEGAI_HOME/.openspec-state.XXXXXX")"
  if ! jq 'del(.tools.openspec)' "$STATE_FILE" >"$tmp"; then
    rm "$tmp"
    die "OpenSpec links removed but state update failed; reconcile before continuing"
  fi
  mv "$tmp" "$STATE_FILE"
fi
ok "OpenSpec managed Pi links removed; independent CLI, privacy settings and project specs retained"

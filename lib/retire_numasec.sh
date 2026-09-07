#!/usr/bin/env bash
# Legacy-link cleanup only; never installs or invokes Numasec.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
SKILL_SOURCE="${NUMASEC_SKILL_SOURCE:-$MEGAI_HOME/skills/numasec-security}"
. "$MEGAI_HOME/lib/ui.sh"
. "$MEGAI_HOME/lib/state.sh"
[ "$#" -eq 0 ] || die "Usage: retire_numasec.sh"
command -v jq >/dev/null 2>&1 || die "jq required for MEGAI state"
tmp=""
trap 'if [ -n "$tmp" ]; then rm -f "$tmp"; fi' EXIT
# Validate/prepare the state change before touching even owned links.
if [ -f "$STATE_FILE" ]; then
  tmp="$(mktemp "$MEGAI_HOME/.numasec-state.XXXXXX")"
  jq 'del(.tools.numasec)' "$STATE_FILE" > "$tmp"
fi
for root in "$HOME/.agents/skills" "$HOME/.claude/skills" "$HOME/.codex/skills" "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/skills"; do
  dest="$root/numasec-security"
  if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$SKILL_SOURCE" ]; then
    rm "$dest"
  fi
done
if [ -n "$tmp" ]; then mv "$tmp" "$STATE_FILE"; tmp=""; fi
ok "Numasec owned skill links/state removed; independent CLI and user data retained"

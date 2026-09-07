#!/usr/bin/env bash
# Legacy artifact cleanup only. Never invokes Argent or touches SDKs/reports.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
. "$MEGAI_HOME/lib/ui.sh"
. "$MEGAI_HOME/lib/state.sh"
[ "$#" -eq 0 ] || die "Usage: retire_argent.sh"
command -v jq >/dev/null 2>&1 || die "jq required for MEGAI state"
tmp=""
trap 'if [ -n "$tmp" ]; then rm -f "$tmp"; fi' EXIT
if [ -f "$STATE_FILE" ]; then
  tmp="$(mktemp "$MEGAI_HOME/.argent-state.XXXXXX")"
  jq 'del(.tools.argent)' "$STATE_FILE" > "$tmp"
fi
remove_managed_artifact() {
  local dest="$1"
  [ -f "$dest" ] || return 0
  if [ -L "$dest" ] || [ -L "$(dirname "$dest")" ]; then
    warn "Argent: preserving linked artifact: $dest"
  elif grep -q '^managed-by: megai$' "$dest"; then
    rm "$dest"
    rmdir "$(dirname "$dest")" 2>/dev/null || true
  else
    warn "Argent: preserving user-owned file: $dest"
  fi
}
for root in "$HOME/.agents/skills" "$HOME/.claude/skills" "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/skills" "$HOME/.omp/agent/skills"; do
  remove_managed_artifact "$root/argent/SKILL.md"
done
remove_managed_artifact "$HOME/.claude/commands/argent.md"
for agent in "$HOME/.omp/profiles/"*/agent; do
  [ -d "$agent" ] || continue
  remove_managed_artifact "$agent/skills/argent/SKILL.md"
done
if [ -n "$tmp" ]; then mv "$tmp" "$STATE_FILE"; tmp=""; fi
ok "Argent owned artifacts/state removed; independent CLI and user data retained"

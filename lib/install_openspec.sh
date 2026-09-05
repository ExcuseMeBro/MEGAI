#!/usr/bin/env bash
# Optional Pi-only spec bridge. Never initializes or scans project repositories.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
PI_AGENT="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
SKILL_SOURCE="$MEGAI_HOME/skills/megai-openspec"
DEST="$PI_AGENT/skills/megai-openspec"
VERSION="1.12.0"
. "$MEGAI_HOME/lib/ui.sh"
. "$MEGAI_HOME/lib/state.sh"

if [ "${1:-}" = "--remove" ]; then
  command -v jq >/dev/null 2>&1 || die "jq required for MEGAI state"
  destinations="$(jq -cn --arg dest "$DEST" '[$dest]')"
  if [ -f "$STATE_FILE" ]; then
    destinations="$(jq -c --arg dest "$DEST" '[(.tools.openspec.destinations // [])[], $dest] | unique' "$STATE_FILE")"
  fi
  # Include the current destination for older installs without a registry.
  # NUL delimiting preserves spaces/newlines in custom Pi paths.
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
  ok "OpenSpec managed Pi links removed; CLI, privacy setting and project specs retained"
  exit 0
fi
[ "$#" -eq 0 ] || die "Usage: install_openspec.sh [--remove]"
[ -f "$SKILL_SOURCE/SKILL.md" ] || die "Missing OpenSpec bridge: $SKILL_SOURCE"
if [ -e "$DEST" ] || [ -L "$DEST" ]; then
  [ -L "$DEST" ] && [ "$(readlink "$DEST")" = "$SKILL_SOURCE" ] || die "Keeping existing user skill: $DEST"
fi
command -v node >/dev/null 2>&1 || die "OpenSpec requires Node >=20.19.0"
node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>20 || (a===20 && b>=19) ? 0 : 1)' || die "OpenSpec requires Node >=20.19.0"
command -v jq >/dev/null 2>&1 || die "jq required for MEGAI state"

if ! command -v openspec >/dev/null 2>&1; then
  command -v npm >/dev/null 2>&1 || die "npm required to install OpenSpec"
  npm install --global --ignore-scripts --no-audit --no-fund "@fission-ai/openspec@$VERSION"
  hash -r
fi
actual="$(OPENSPEC_TELEMETRY=0 openspec --version)"
[ "$actual" = "$VERSION" ] || die "OpenSpec $actual retained; this integration requires tested version $VERSION. Review compatibility before changing versions."
# Targeted upstream config write preserves unrelated global settings.
OPENSPEC_TELEMETRY=0 openspec config set telemetry.enabled false
mkdir -p "$PI_AGENT/skills"
[ -L "$DEST" ] || ln -s "$SKILL_SOURCE" "$DEST"
state_init
destinations="$(jq -c --arg dest "$DEST" '[(.tools.openspec.destinations // [])[], $dest] | unique' "$STATE_FILE")"
metadata="$(jq -cn --arg bin "$(command -v openspec)" --arg version "$actual" --arg skill "$SKILL_SOURCE" --argjson destinations "$destinations" '{bin:$bin,version:$version,skill:$skill,destinations:$destinations,scope:"pi",optional:true}')"
state_set '.tools.openspec' "$metadata"
ok "OpenSpec $actual ready for Pi; repositories unchanged; use /skill:megai-openspec"

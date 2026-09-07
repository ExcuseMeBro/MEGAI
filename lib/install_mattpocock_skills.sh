#!/usr/bin/env bash
# Pinned upstream skill source, no third-party installer/config execution.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
. "$MEGAI_HOME/lib/ui.sh"
. "$MEGAI_HOME/lib/state.sh"
KIT="$MEGAI_HOME/pi-kits/mattpocock-skills"
REF=6654f6b60cd9d5be8b54c6fafe44346dabeb3b76
# Reuse the ownership-aware path guard even for standalone installer calls.
PYTHONDONTWRITEBYTECODE=1 python3 - "$MEGAI_HOME" "$KIT" "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/skills" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / 'lib'))
from slim_wiring import safe
for path in sys.argv[2:]:
    safe(Path(path) / '.preflight')
PY
if [ -L "$KIT" ] || { [ -e "$KIT" ] && [ ! -d "$KIT" ]; }; then die "unsafe Matt skill destination: $KIT"; fi
if [ -d "$KIT" ] && [ "$(state_get '.tools["mattpocock-skills"].path')" != "$KIT" ]; then die "unowned Matt source preserved: $KIT"; fi
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
if [ -n "${MATTPOCOCK_SKILLS_SOURCE:-}" ]; then
  cp -R "$MATTPOCOCK_SKILLS_SOURCE/." "$tmp/"
else
  curl -fsSL "https://codeload.github.com/mattpocock/skills/tar.gz/$REF" | tar -xz -C "$tmp" --strip-components=1
fi
[ -d "$tmp/skills" ] || die "upstream Matt skill tree missing"
find "$tmp/skills" -name SKILL.md -type f | grep -q . || die "no Matt skills downloaded"
if [ -d "$KIT" ]; then
  mkdir -p "$MEGAI_HOME/backups"
  recovery="$(mktemp -d "$MEGAI_HOME/backups/matt-source.XXXXXX")"
  mv "$KIT" "$recovery/source"
fi
mkdir -p "$(dirname "$KIT")"
mv "$tmp" "$KIT"
trap - EXIT
# Pi-only discovery; old shared source trees and registrations remain untouched.
roots=("${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/skills")
while IFS= read -r skill; do
  source="$(dirname "$skill")"
  name="$(basename "$source")"
  for root in "${roots[@]}"; do
    mkdir -p "$root"
    dest="$root/$name"
    legacy="$MEGAI_HOME/mattpocock-skills${source#"$KIT"}"
    if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$legacy" ]; then
      rm -f "$dest"  # migrate this exact Pi-local legacy link only
    fi
    if [ -e "$dest" ] || [ -L "$dest" ]; then
      [ -L "$dest" ] && [ "$(readlink "$dest")" = "$source" ] && continue
      warn "preserving existing skill: $dest (upstream available at $source)"
      continue
    fi
    ln -s "$source" "$dest"
  done
done < <(find "$KIT/skills" -name SKILL.md -type f | sort)
state_set '.tools["mattpocock-skills"]' "$(jq -cn --arg path "$KIT" --arg ref "$REF" '{path:$path,ref:$ref}')"
ok "Matt Pocock skills ready; bodies load on demand, user selections preserved"

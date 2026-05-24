#!/usr/bin/env bash
# Pi has no native MCP. Install megai skill + extensions instead.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

PI_AGENT="$HOME/.pi/agent"
MODE="${1:-install}"

if [ "$MODE" = "--remove" ]; then
  rm -f "$PI_AGENT/skills/megai.md"
  rm -f "$PI_AGENT/extensions/megai-memory.sh" "$PI_AGENT/extensions/megai-codedb.sh"
  ok "pi: megai skill + extensions removed"
  exit 0
fi

mkdir -p "$PI_AGENT/skills" "$PI_AGENT/extensions"

# Skill
cp "$MEGAI_HOME/pi-skill/SKILL.md" "$PI_AGENT/skills/megai.md"

# Extensions: symlink (so updates propagate)
ln -sf "$MEGAI_HOME/pi-skill/extensions/memory.sh" "$PI_AGENT/extensions/megai-memory.sh"
ln -sf "$MEGAI_HOME/pi-skill/extensions/codedb.sh" "$PI_AGENT/extensions/megai-codedb.sh"
chmod +x "$MEGAI_HOME/pi-skill/extensions/"*.sh 2>/dev/null || true

ok "pi: skill + extensions installed -> $PI_AGENT"
state_set '.agents["pi"]' "{\"config\":\"$PI_AGENT\",\"wired\":true}"

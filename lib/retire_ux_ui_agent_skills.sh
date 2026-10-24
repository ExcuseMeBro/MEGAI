#!/usr/bin/env bash
# Retire plugin87/ux-ui-agent-skills: detach its own skill links, keep the source.
# The curated design skills now ship in pi-defaults/skills (see UI-SKILLS.md).
set -euo pipefail

MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
KIT_HOME="$MEGAI_HOME/ux-ui-agent-skills"
WRAPPERS="$KIT_HOME/.megai-skills"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

skills=(
  a11y-audit apply-aesthetic brandkit design-code design-component design-qa
  design-review design-tokens figma-integration governance image-to-code
  migrate-design-system performance prototype redesign token-build ux-writing
)
profile="${OMP_PROFILE:-${PI_PROFILE:-}}"
case "$profile" in .|..|*/*|*\\*) die "invalid OMP profile" ;; esac
omp_agent="$HOME/.omp/agent"
[ -z "$profile" ] || omp_agent="$HOME/.omp/profiles/$profile/agent"
roots=(
  "$HOME/.agents/skills"
  "$HOME/.claude/skills"
  "$HOME/.codex/skills"
  "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/skills"
  "$omp_agent/skills"
)

exposed_name() {
  [ "$1" = "prototype" ] && printf '%s\n' ux-ui-prototype || printf '%s\n' "$1"
}

# Only links this kit created are removed; an operator's own skill named like one of
# them keeps its place because its target is not inside the kit wrapper directory.
detached=0
for root in "${roots[@]}"; do
  for skill in "${skills[@]}"; do
    dest="$root/$(exposed_name "$skill")"
    [ -L "$dest" ] || continue
    case "$(readlink "$dest")" in
    "$WRAPPERS"/*)
      rm -f "$dest"
      detached=$((detached + 1))
      ;;
    esac
  done
done

# Source, wrappers and any operator data in the kit stay; only the registration goes.
[ -f "$MEGAI_HOME/state.json" ] && state_set '.tools["ux-ui-agent-skills"]' null
ok "ux-ui-agent-skills retired ($detached links detached; kit source retained)"

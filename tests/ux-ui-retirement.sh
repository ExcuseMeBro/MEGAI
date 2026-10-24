#!/usr/bin/env bash
# The ux-ui kit install path is retired: its links are detached and the source is kept.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home"
export MEGAI_HOME="$TMP/megai"
export PI_CODING_AGENT_DIR="$HOME/.pi/agent"
export OMP_PROFILE=""
export PI_PROFILE=""
mkdir -p "$MEGAI_HOME" "$HOME/.agents/skills" "$HOME/.claude/skills"
cp "$ROOT/lib/ui.sh" "$ROOT/lib/state.sh" "$ROOT/lib/retire_ux_ui_agent_skills.sh" "$MEGAI_HOME/"
mkdir -p "$MEGAI_HOME/lib"
mv "$MEGAI_HOME"/*.sh "$MEGAI_HOME/lib/"
printf '%s\n' '{"tools":{"ux-ui-agent-skills":{"path":"'"$MEGAI_HOME"'/ux-ui-agent-skills","version":"2.4.0","skills":17}},"keep":{"value":42}}' >"$MEGAI_HOME/state.json"

kit="$MEGAI_HOME/ux-ui-agent-skills"
wrappers="$kit/.megai-skills"
skills=(
  a11y-audit apply-aesthetic brandkit design-code design-component design-qa
  design-review design-tokens figma-integration governance image-to-code
  migrate-design-system performance prototype redesign token-build ux-writing
)
exposed() { [ "$1" = "prototype" ] && printf '%s\n' ux-ui-prototype || printf '%s\n' "$1"; }
for skill in "${skills[@]}"; do
  mkdir -p "$wrappers/$(exposed "$skill")"
  printf '%s\n' '---' "name: $(exposed "$skill")" "description: fixture." '---' >"$wrappers/$(exposed "$skill")/SKILL.md"
done
printf '{"version":"2.4.0"}\n' >"$kit/package.json"
printf 'operator note\n' >"$kit/local-note"

# Kit links across all five roots, plus two lookalikes that must survive: a real
# file and a link this kit did not create.
roots=("$HOME/.agents/skills" "$HOME/.claude/skills" "$HOME/.codex/skills"
       "$PI_CODING_AGENT_DIR/skills" "$HOME/.omp/agent/skills")
for root in "${roots[@]}"; do
  mkdir -p "$root"
  ln -s "$wrappers/a11y-audit" "$root/a11y-audit"
  ln -s "$wrappers/ux-ui-prototype" "$root/ux-ui-prototype"
done
mkdir -p "$HOME/.agents/skills/prototype"
printf 'keep\n' >"$HOME/.agents/skills/prototype/SKILL.md"
mkdir -p "$TMP/elsewhere/brandkit"
ln -s "$TMP/elsewhere/brandkit" "$HOME/.agents/skills/brandkit"

bash "$MEGAI_HOME/lib/retire_ux_ui_agent_skills.sh"
for root in "${roots[@]}"; do
  [ ! -L "$root/a11y-audit" ] && [ ! -L "$root/ux-ui-prototype" ]
done
[ "$(cat "$HOME/.agents/skills/prototype/SKILL.md")" = keep ]
[ -L "$HOME/.agents/skills/brandkit" ] && [ "$(readlink "$HOME/.agents/skills/brandkit")" = "$TMP/elsewhere/brandkit" ]
[ -d "$kit" ] && [ "$(cat "$kit/local-note")" = 'operator note' ]
jq -e '.keep.value == 42' "$MEGAI_HOME/state.json" >/dev/null
jq -e '.tools["ux-ui-agent-skills"] == null' "$MEGAI_HOME/state.json" >/dev/null

# Idempotent: a second run has nothing to detach and must not fail.
bash "$MEGAI_HOME/lib/retire_ux_ui_agent_skills.sh"
[ ! -e "$HOME/.agents/skills/a11y-audit" ]
jq -e '.keep.value == 42' "$MEGAI_HOME/state.json" >/dev/null

# Selected OMP profiles and custom Pi roots follow the same ownership rules.
export OMP_PROFILE="fixture"
export PI_CODING_AGENT_DIR="$HOME/custom-pi"
for root in "$HOME/.omp/profiles/$OMP_PROFILE/agent/skills" "$PI_CODING_AGENT_DIR/skills"; do
  mkdir -p "$root"
  for skill in "${skills[@]}"; do
    ln -s "$wrappers/$(exposed "$skill")" "$root/$(exposed "$skill")"
  done
done
bash "$MEGAI_HOME/lib/retire_ux_ui_agent_skills.sh"
for root in "$HOME/.omp/profiles/$OMP_PROFILE/agent/skills" "$PI_CODING_AGENT_DIR/skills"; do
  for skill in "${skills[@]}"; do
    [ ! -L "$root/$(exposed "$skill")" ]
  done
done

# Invalid profiles fail before any detachment; missing state/source is safe.
if OMP_PROFILE='../escape' bash "$MEGAI_HOME/lib/retire_ux_ui_agent_skills.sh"; then
  echo 'invalid profile unexpectedly accepted' >&2
  exit 1
fi
export MEGAI_HOME="$TMP/fresh"
mkdir -p "$MEGAI_HOME/lib"
cp "$ROOT/lib/ui.sh" "$ROOT/lib/state.sh" "$ROOT/lib/retire_ux_ui_agent_skills.sh" "$MEGAI_HOME/lib/"
bash "$MEGAI_HOME/lib/retire_ux_ui_agent_skills.sh"
[ ! -e "$MEGAI_HOME/state.json" ]

# A fresh install no longer wires the kit at all.
! grep -q 'install_ux_ui_agent_skills' "$ROOT/lib/main.sh"
! grep -q 'ux-ui-agent-skills' "$ROOT/bin/megai"

echo "ux-ui-agent-skills retirement: ok"

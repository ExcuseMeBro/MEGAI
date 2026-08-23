#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home"
export MEGAI_HOME="$TMP/megai"
export UX_UI_AGENT_SKILLS_SOURCE="$TMP/source"
mkdir -p "$MEGAI_HOME/lib" "$UX_UI_AGENT_SKILLS_SOURCE/.claude/skills" "$UX_UI_AGENT_SKILLS_SOURCE/accessibility"
cp "$ROOT/lib/ui.sh" "$ROOT/lib/state.sh" "$MEGAI_HOME/lib/"
printf '%s\n' '{"tools":{},"ports":{},"agents":{},"projects":{}}' >"$MEGAI_HOME/state.json"
printf '%s\n' '{"version":"2.4.0"}' >"$UX_UI_AGENT_SKILLS_SOURCE/package.json"
printf '%s\n' '# WCAG fixture' >"$UX_UI_AGENT_SKILLS_SOURCE/accessibility/wcag-checklist.md"

skills=(
  a11y-audit apply-aesthetic brandkit design-code design-component design-qa
  design-review design-tokens figma-integration governance image-to-code
  migrate-design-system performance prototype redesign token-build ux-writing
)
for skill in "${skills[@]}"; do
  mkdir -p "$UX_UI_AGENT_SKILLS_SOURCE/.claude/skills/$skill"
  printf '%s\n' '---' "name: $skill" "description: Test $skill." '---' >"$UX_UI_AGENT_SKILLS_SOURCE/.claude/skills/$skill/SKILL.md"
done

mkdir -p "$HOME/.agents/skills/prototype"
printf '%s\n' keep >"$HOME/.agents/skills/prototype/SKILL.md"

bash "$ROOT/lib/install_ux_ui_agent_skills.sh" >/dev/null
bash "$ROOT/lib/install_ux_ui_agent_skills.sh" >/dev/null

for root in "$HOME/.agents/skills" "$HOME/.claude/skills" "$HOME/.codex/skills" "$HOME/.pi/agent/skills"; do
  [ -L "$root/a11y-audit" ]
  [ -L "$root/ux-ui-prototype" ]
done
[ "$(cat "$HOME/.agents/skills/prototype/SKILL.md")" = keep ]
grep -q '^name: ux-ui-prototype$' "$HOME/.agents/skills/ux-ui-prototype/SKILL.md"
grep -q '^# WCAG fixture$' "$HOME/.agents/skills/a11y-audit/accessibility/wcag-checklist.md"
jq -e '.tools["ux-ui-agent-skills"] == {path: (env.MEGAI_HOME + "/ux-ui-agent-skills"), version:"2.4.0", skills:17}' "$MEGAI_HOME/state.json" >/dev/null

# A malformed update must fail before replacing the working global kit.
rm "$UX_UI_AGENT_SKILLS_SOURCE/.claude/skills/brandkit/SKILL.md"
if bash "$ROOT/lib/install_ux_ui_agent_skills.sh" >/dev/null 2>&1; then
  echo "malformed ux-ui-agent-skills update unexpectedly succeeded" >&2
  exit 1
fi
[ -f "$HOME/.agents/skills/brandkit/SKILL.md" ]
grep -q '^name: brandkit$' "$HOME/.agents/skills/brandkit/SKILL.md"

bash "$ROOT/lib/install_ux_ui_agent_skills.sh" --remove >/dev/null
[ ! -e "$HOME/.agents/skills/a11y-audit" ]
[ ! -e "$HOME/.claude/skills/ux-ui-prototype" ]
[ -f "$HOME/.agents/skills/prototype/SKILL.md" ]

echo "ux-ui-agent-skills integration: ok"

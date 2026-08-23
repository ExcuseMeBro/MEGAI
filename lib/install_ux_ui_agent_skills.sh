#!/usr/bin/env bash
# plugin87/ux-ui-agent-skills — global UI/UX skills for Claude Code, Codex, and Pi.
set -euo pipefail

MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
KIT_HOME="$MEGAI_HOME/ux-ui-agent-skills"
WRAPPERS="$KIT_HOME/.megai-skills"
REPO="${UX_UI_AGENT_SKILLS_REPO:-plugin87/ux-ui-agent-skills}"
REF="${UX_UI_AGENT_SKILLS_REF:-main}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

skills=(
  a11y-audit apply-aesthetic brandkit design-code design-component design-qa
  design-review design-tokens figma-integration governance image-to-code
  migrate-design-system performance prototype redesign token-build ux-writing
)
resources=(
  CLAUDE.md CONTEXT.md accessibility components content design-systems examples
  frameworks scripts taste tokens workflows package.json
)
roots=(
  "$HOME/.agents/skills"
  "$HOME/.claude/skills"
  "$HOME/.codex/skills"
  "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/skills"
)

exposed_name() {
  [ "$1" = "prototype" ] && printf '%s\n' ux-ui-prototype || printf '%s\n' "$1"
}

remove_links() {
  local root skill name dest target
  for root in "${roots[@]}"; do
    for skill in "${skills[@]}"; do
      name="$(exposed_name "$skill")"
      dest="$root/$name"
      [ -L "$dest" ] || continue
      target="$(readlink "$dest")"
      case "$target" in
      "$WRAPPERS"/*) rm -f "$dest" ;;
      esac
    done
  done
}

if [ "${1:-}" = "--remove" ]; then
  remove_links
  rm -rf "$KIT_HOME"
  [ -f "$MEGAI_HOME/state.json" ] && state_set '.tools["ux-ui-agent-skills"]' null
  ok "ux-ui-agent-skills removed"
  exit 0
fi

source_dir="${UX_UI_AGENT_SKILLS_SOURCE:-}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
if [ -n "$source_dir" ]; then
  [ -d "$source_dir/.claude/skills" ] || die "Invalid ux-ui-agent-skills source: $source_dir"
  cp -R "$source_dir/." "$tmp/"
else
  curl -fsSL "https://codeload.github.com/${REPO}/tar.gz/refs/heads/${REF}" |
    tar -xz -C "$tmp" --strip-components=1
fi
for skill in "${skills[@]}"; do
  [ -f "$tmp/.claude/skills/$skill/SKILL.md" ] || die "Downloaded ux-ui-agent-skills archive is missing: $skill"
done
[ -f "$tmp/package.json" ] || die "Downloaded ux-ui-agent-skills archive is missing package.json"
rm -rf "$KIT_HOME"
mv "$tmp" "$KIT_HOME"
trap - EXIT

mkdir -p "$WRAPPERS"
for skill in "${skills[@]}"; do
  src="$KIT_HOME/.claude/skills/$skill/SKILL.md"
  [ -f "$src" ] || die "Missing upstream skill: $skill"
  name="$(exposed_name "$skill")"
  wrapper="$WRAPPERS/$name"
  mkdir -p "$wrapper"
  if [ "$skill" = "prototype" ]; then
    awk '{ if ($0 == "name: prototype") print "name: ux-ui-prototype"; else print }' "$src" >"$wrapper/SKILL.md"
  else
    cp "$src" "$wrapper/SKILL.md"
  fi
  for resource in "${resources[@]}"; do
    [ -e "$KIT_HOME/$resource" ] && ln -s "../../$resource" "$wrapper/$resource"
  done
done

linked=0
for root in "${roots[@]}"; do
  mkdir -p "$root"
  for skill in "${skills[@]}"; do
    name="$(exposed_name "$skill")"
    dest="$root/$name"
    if [ -L "$dest" ]; then
      target="$(readlink "$dest")"
      case "$target" in
      "$WRAPPERS"/*) rm -f "$dest" ;;
      *)
        warn "Keeping existing skill link: $dest"
        continue
        ;;
      esac
    elif [ -e "$dest" ]; then
      warn "Keeping existing skill: $dest"
      continue
    fi
    ln -s "$WRAPPERS/$name" "$dest"
    linked=$((linked + 1))
  done
done

version="$(jq -r '.version // "unknown"' "$KIT_HOME/package.json" 2>/dev/null || echo unknown)"
metadata="$(jq -n --arg path "$KIT_HOME" --arg version "$version" --argjson skills "${#skills[@]}" '{path:$path,version:$version,skills:$skills}')"
state_set '.tools["ux-ui-agent-skills"]' "$metadata"
ok "ux-ui-agent-skills v$version installed globally (${#skills[@]} skills; prototype exposed as ux-ui-prototype)"

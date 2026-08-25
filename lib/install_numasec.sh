#!/usr/bin/env bash
# Numasec — optional terminal security agent with global handoff guidance.
set -euo pipefail

MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
SKILL_SOURCE="${NUMASEC_SKILL_SOURCE:-$MEGAI_HOME/skills/numasec-security}"
PACKAGE="${NUMASEC_PACKAGE:-numasec@latest}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

roots=(
  "$HOME/.agents/skills"
  "$HOME/.claude/skills"
  "$HOME/.codex/skills"
  "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/skills"
)

remove_links() {
  local root dest target
  for root in "${roots[@]}"; do
    dest="$root/numasec-security"
    [ -L "$dest" ] || continue
    target="$(readlink "$dest")"
    [ "$target" = "$SKILL_SOURCE" ] && rm -f "$dest"
  done
}

if [ "${1:-}" = "--remove" ]; then
  remove_links
  [ -f "$MEGAI_HOME/state.json" ] && state_set '.tools.numasec' null
  ok "Numasec skill links removed; CLI retained"
  exit 0
fi

[ -f "$SKILL_SOURCE/SKILL.md" ] || die "Missing Numasec skill: $SKILL_SOURCE/SKILL.md"

if [ "${MEGAI_UPDATE:-0}" = "1" ]; then
  npm install -g "$PACKAGE" >/dev/null 2>&1 || warn "Numasec update failed — keeping current version"
elif command -v numasec >/dev/null 2>&1; then
  ok "Numasec already installed -> $(command -v numasec)"
else
  npm install -g "$PACKAGE" >/dev/null 2>&1 || {
    warn "Numasec npm install failed — skipping"
    exit 0
  }
fi
hash -r

bin="$(command -v numasec || true)"
[ -n "$bin" ] || {
  warn "Numasec binary unavailable after install"
  exit 0
}

linked=0
for root in "${roots[@]}"; do
  mkdir -p "$root"
  dest="$root/numasec-security"
  if [ -L "$dest" ]; then
    target="$(readlink "$dest")"
    if [ "$target" = "$SKILL_SOURCE" ]; then
      continue
    fi
    warn "Keeping existing skill link: $dest"
    continue
  elif [ -e "$dest" ]; then
    warn "Keeping existing skill: $dest"
    continue
  fi
  ln -s "$SKILL_SOURCE" "$dest"
  linked=$((linked + 1))
done

version="$(numasec --version 2>/dev/null | head -n1 || true)"
metadata="$(jq -cn --arg bin "$bin" --arg version "${version:-unknown}" --arg skill "$SKILL_SOURCE" '{bin:$bin,version:$version,skill:$skill}')"
state_set '.tools.numasec' "$metadata"
ok "Numasec ${version:-unknown} ready ($linked new skill links; authorized targets only)"

#!/usr/bin/env bash
# Argent — agent-driven mobile, TV, Electron, and browser testing via CLI + MCP.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

MODE="${1:-install}"
skill_source="$MEGAI_HOME/skills/argent/SKILL.md"
command_source="$MEGAI_HOME/task-flow/commands/argent.md"

remove_managed_artifact() {
  local dest="$1"
  [ -e "$dest" ] || return 0
  if grep -q '^managed-by: megai$' "$dest" 2>/dev/null; then
    rm -f "$dest"
    rmdir "$(dirname "$dest")" 2>/dev/null || true
  else
    warn "Argent: preserving user-owned file: $dest"
  fi
}

if [ "$MODE" = "--remove" ]; then
  for skill_root in \
    "$HOME/.agents/skills" \
    "$HOME/.claude/skills" \
    "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/skills" \
    "$HOME/.omp/agent/skills"; do
    remove_managed_artifact "$skill_root/argent/SKILL.md"
  done
  remove_managed_artifact "$HOME/.claude/commands/argent.md"
  if [ -d "$HOME/.omp/profiles" ]; then
    for profile_agent in "$HOME/.omp/profiles"/*/agent; do
      [ -d "$profile_agent" ] || continue
      remove_managed_artifact "$profile_agent/skills/argent/SKILL.md"
    done
  fi
  ok "Argent explicit-only skill removed"
  exit 0
fi

if [ "${MEGAI_UPDATE:-0}" = "1" ]; then
  npm install -g @swmansion/argent@latest >/dev/null 2>&1 || {
    warn "Argent update failed — keeping current version"
    exit 0
  }
  hash -r
  ok "Argent updated"
elif command -v argent >/dev/null 2>&1; then
  ok "Argent already installed -> $(command -v argent)"
else
  npm install -g @swmansion/argent@latest >/dev/null 2>&1 || {
    warn "Argent npm install failed — skipping"
    exit 0
  }
  hash -r
  ok "Argent installed"
fi

bin="$(command -v argent || echo "")"
ver="$(argent --version 2>/dev/null | head -n1 || echo "")"
state_set '.tools["argent"]' "{\"bin\":\"$bin\",\"version\":\"$ver\"}"



install_managed_artifact() {
  local source="$1" dest="$2"
  [ -f "$source" ] || return 0
  if [ -e "$dest" ] && ! grep -q '^managed-by: megai$' "$dest" 2>/dev/null; then
    warn "Argent: preserving user-owned file: $dest"
    return 0
  fi
  mkdir -p "$(dirname "$dest")"
  cp "$source" "$dest"
}

for skill_root in \
  "$HOME/.agents/skills" \
  "$HOME/.claude/skills" \
  "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/skills" \
  "$HOME/.omp/agent/skills"; do
  install_managed_artifact "$skill_source" "$skill_root/argent/SKILL.md"
done
install_managed_artifact "$command_source" "$HOME/.claude/commands/argent.md"

if [ -d "$HOME/.omp/profiles" ]; then
  for profile_agent in "$HOME/.omp/profiles"/*/agent; do
    [ -d "$profile_agent" ] || continue
    install_managed_artifact "$skill_source" "$profile_agent/skills/argent/SKILL.md"
  done
fi

ok "Argent explicit-only /argent skill installed"

#!/usr/bin/env bash
# Wire MEGAI skills and core MCP servers into OMP's native user config.
# Idempotent: preserves unrelated user configuration and manages only MEGAI-owned entries.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

PROFILE="${OMP_PROFILE:-${PI_PROFILE:-}}"
if [ -n "$PROFILE" ]; then
  case "$PROFILE" in
    .|..|*[!A-Za-z0-9._-]*)
      warn "OMP: invalid profile name: $PROFILE"
      exit 1
      ;;
  esac
  OMP_AGENT="$HOME/.omp/profiles/$PROFILE/agent"
else
  OMP_AGENT="${PI_CODING_AGENT_DIR:-$HOME/.omp/agent}"
fi
OMP_MCP_CONFIG="$OMP_AGENT/mcp.json"
OMP_SKILL="$MEGAI_HOME/omp-skill/SKILL.md"
TASK_FLOW_SKILL="$MEGAI_HOME/task-flow/skills/megai-task-flow/SKILL.md"
WORKTREE_SKILL="$MEGAI_HOME/skills/agent-worktree-lifecycle/SKILL.md"
ORCHESTRATOR_SKILL="$MEGAI_HOME/skills/smart-development-orchestrator/SKILL.md"
OMP_RULES="$OMP_AGENT/RULES.md"
OMP_RULES_SOURCE="$MEGAI_HOME/omp-skill/RULES.md"
OMP_AGENTS_SOURCE="$MEGAI_HOME/omp-agents"
RULES_BEGIN="<!-- megai:paseo-placement:begin -->"
RULES_END="<!-- megai:paseo-placement:end -->"
validate_placement_rules() {
  [ -f "$OMP_RULES" ] || return 0
  if ! awk -v begin="$RULES_BEGIN" -v end="$RULES_END" '
    $0 == begin {
      if (open) malformed=1
      open=1
      next
    }
    $0 == end {
      if (!open) malformed=1
      open=0
      next
    }
    END { if (open || malformed) exit 1 }
  ' "$OMP_RULES"; then
    warn "OMP: malformed Paseo placement markers — RULES.md unchanged: $OMP_RULES"
    return 1
  fi
}


remove_placement_rules() {
  [ -f "$OMP_RULES" ] || return 0
  validate_placement_rules
  local rules_tmp
  rules_tmp="$(mktemp "$OMP_AGENT/RULES.md.XXXXXX")"
  awk -v begin="$RULES_BEGIN" -v end="$RULES_END" '
    $0 == begin { skip=1; next }
    skip && $0 == end { skip=0; next }
    !skip { print }
  ' "$OMP_RULES" >"$rules_tmp"
  if grep -q '[^[:space:]]' "$rules_tmp"; then
    mv "$rules_tmp" "$OMP_RULES"
  else
    rm -f "$rules_tmp" "$OMP_RULES"
  fi
}

refresh_placement_rules() {
  [ -f "$OMP_RULES_SOURCE" ] || {
    warn "OMP: Paseo placement rules missing — skipped"
    return 0
  }
  validate_placement_rules
  local rules_tmp
  if [ -f "$OMP_RULES" ] && grep -Fxq "$RULES_BEGIN" "$OMP_RULES"; then
    rules_tmp="$(mktemp "$OMP_AGENT/RULES.md.XXXXXX")"
    awk -v begin="$RULES_BEGIN" -v end="$RULES_END" -v replacement="$OMP_RULES_SOURCE" '
      $0 == begin {
        if (!emitted) {
          while ((getline line < replacement) > 0) print line
          close(replacement)
          emitted=1
        }
        skip=1
        next
      }
      skip && $0 == end { skip=0; next }
      !skip { print }
    ' "$OMP_RULES" >"$rules_tmp"
    mv "$rules_tmp" "$OMP_RULES"
  elif [ -f "$OMP_RULES" ]; then
    rules_tmp="$(mktemp "$OMP_AGENT/RULES.md.XXXXXX")"
    { cat "$OMP_RULES"; printf '\n'; cat "$OMP_RULES_SOURCE"; } >"$rules_tmp"
    mv "$rules_tmp" "$OMP_RULES"
  else
    cp "$OMP_RULES_SOURCE" "$OMP_RULES"
  fi
}

is_managed_copy() {
  local source="$1" dest="$2" legacy
  [ -f "$dest" ] || return 1
  grep -Fxq 'managed-by: megai' "$dest" && return 0
  [ -f "$source" ] || return 1
  legacy="$(mktemp)"
  awk '$0 != "managed-by: megai"' "$source" >"$legacy"
  if cmp -s "$legacy" "$dest"; then
    rm -f "$legacy"
    return 0
  fi
  rm -f "$legacy"
  return 1
}

install_managed_copy() {
  local source="$1" dest="$2"
  if [ -e "$dest" ] && ! is_managed_copy "$source" "$dest"; then
    warn "OMP: preserving user-owned collision: $dest"
    return 0
  fi
  mkdir -p "$(dirname "$dest")"
  cp "$source" "$dest"
}

remove_managed_copy() {
  local source="$1" dest="$2"
  [ -e "$dest" ] || return 0
  if ! is_managed_copy "$source" "$dest"; then
    warn "OMP: preserving user-owned file: $dest"
    return 0
  fi
  rm -f "$dest"
  rmdir "$(dirname "$dest")" 2>/dev/null || true
}

remove_smart_agents() {
  remove_managed_copy "$OMP_AGENTS_SOURCE/smart-router.md" "$OMP_AGENT/agents/smart-router.md"
  remove_managed_copy "$OMP_AGENTS_SOURCE/luna-scout.md" "$OMP_AGENT/agents/luna-scout.md"
  remove_managed_copy "$OMP_AGENTS_SOURCE/terra-scout.md" "$OMP_AGENT/agents/terra-scout.md"
  remove_managed_copy "$OMP_AGENTS_SOURCE/minimax-worker.md" "$OMP_AGENT/agents/minimax-worker.md"
}

install_router_group() {
  local name source dest safe=1
  for name in smart-router luna-scout terra-scout; do
    source="$OMP_AGENTS_SOURCE/$name.md"
    dest="$OMP_AGENT/agents/$name.md"
    if [ ! -f "$source" ]; then
      warn "OMP: routing agent missing: $source"
      safe=0
    elif [ -e "$dest" ] && ! is_managed_copy "$source" "$dest"; then
      warn "OMP: preserving user-owned routing dependency collision: $dest"
      safe=0
    fi
  done
  if [ "$safe" != 1 ]; then
    for name in smart-router luna-scout terra-scout; do
      remove_managed_copy "$OMP_AGENTS_SOURCE/$name.md" "$OMP_AGENT/agents/$name.md"
    done
    warn "OMP: managed smart-router group skipped to avoid spawning user-owned dependencies"
    return 0
  fi
  for name in smart-router luna-scout terra-scout; do
    install_managed_copy "$OMP_AGENTS_SOURCE/$name.md" "$OMP_AGENT/agents/$name.md"
  done
}
MODE="${1:-install}"

if [ "$MODE" = "--remove" ]; then
  remove_placement_rules
  rm -rf "$OMP_AGENT/skills/megai" "$OMP_AGENT/skills/megai-task-flow"
  remove_managed_copy "$WORKTREE_SKILL" "$OMP_AGENT/skills/agent-worktree-lifecycle/SKILL.md"
  remove_managed_copy "$ORCHESTRATOR_SKILL" "$OMP_AGENT/skills/smart-development-orchestrator/SKILL.md"
  remove_smart_agents
  if [ ! -f "$OMP_MCP_CONFIG" ]; then
    ok "OMP: no native MEGAI wiring to remove"
    exit 0
  fi
  if ! command -v jq >/dev/null 2>&1; then
    warn "jq missing — OMP skills removed, MCP config unchanged"
    exit 0
  fi
  if ! jq -e 'type == "object" and ((.mcpServers // {}) | type == "object")' "$OMP_MCP_CONFIG" >/dev/null 2>&1; then
    warn "OMP: invalid MCP config — MCP cleanup skipped: $OMP_MCP_CONFIG"
    exit 0
  fi
  mkdir -p "$MEGAI_HOME/backups"
  backup="$(mktemp "$MEGAI_HOME/backups/omp.mcp.json.bak.XXXXXX")"
  cp "$OMP_MCP_CONFIG" "$backup"
  tmp="$(mktemp "$OMP_AGENT/mcp.json.XXXXXX")"
  jq 'del(.mcpServers.agentmemory, .mcpServers.codedb, .mcpServers["megai-dembrandt"], .mcpServers["megai-argent"], .mcpServers["megai-repowise"])' \
    "$OMP_MCP_CONFIG" >"$tmp"
  chmod 600 "$tmp"
  mv "$tmp" "$OMP_MCP_CONFIG"
  ok "OMP: MEGAI MCP servers, skills, and placement rules removed"
  exit 0
fi

if ! command -v jq >/dev/null 2>&1; then
  warn "jq missing — skipping OMP wire"
  exit 0
fi

mkdir -p "$OMP_AGENT/skills" "$OMP_AGENT/agents" "$MEGAI_HOME/backups"
refresh_placement_rules
if [ ! -f "$OMP_MCP_CONFIG" ]; then
  cat >"$OMP_MCP_CONFIG" <<'JSON'
{
  "$schema": "https://raw.githubusercontent.com/can1357/oh-my-pi/main/packages/coding-agent/src/config/mcp-schema.json",
  "mcpServers": {}
}
JSON
fi

if ! jq -e 'type == "object" and ((.mcpServers // {}) | type == "object")' "$OMP_MCP_CONFIG" >/dev/null 2>&1; then
  warn "OMP: invalid MCP config — wiring skipped: $OMP_MCP_CONFIG"
  exit 0
fi

backup="$(mktemp "$MEGAI_HOME/backups/omp.mcp.json.bak.XXXXXX")"
cp "$OMP_MCP_CONFIG" "$backup"
tmp="$(mktemp "$OMP_AGENT/mcp.json.XXXXXX")"

AGM_PORT="$(state_get '.ports["agent-memory"]')"
AGM_PORT="${AGM_PORT:-3111}"
AGM_BIN="$(state_get '.tools["agent-memory"].bin')"
AGM_BIN="${AGM_BIN:-agentmemory}"
CODEDB_BIN="$(state_get '.tools["codedb"].bin')"
CODEDB_BIN="${CODEDB_BIN:-codedb}"

mcp_block="$(jq -n \
  --arg agentmemory "$AGM_BIN" \
  --arg codedb "$CODEDB_BIN" \
  --arg url "http://127.0.0.1:$AGM_PORT" '
  {
    agentmemory: {
      command: $agentmemory,
      args: ["mcp"],
      env: {AGENTMEMORY_URL: $url}
    },
    codedb: {
      command: $codedb,
      args: ["mcp"]
    }
  }
')"

jq --argjson add "$mcp_block" '
  .mcpServers = (((.mcpServers // {})
    | del(.["megai-dembrandt"], .["megai-argent"], .["megai-repowise"])) + $add)
' "$OMP_MCP_CONFIG" >"$tmp"
chmod 600 "$tmp"
mv "$tmp" "$OMP_MCP_CONFIG"

mkdir -p "$OMP_AGENT/skills/megai"
cp "$OMP_SKILL" "$OMP_AGENT/skills/megai/SKILL.md"
if [ -f "$TASK_FLOW_SKILL" ]; then
  mkdir -p "$OMP_AGENT/skills/megai-task-flow"
  cp "$TASK_FLOW_SKILL" "$OMP_AGENT/skills/megai-task-flow/SKILL.md"
else
  warn "OMP: MEGAI task-flow skill missing — skipped"
fi
if [ -f "$WORKTREE_SKILL" ]; then
  install_managed_copy "$WORKTREE_SKILL" "$OMP_AGENT/skills/agent-worktree-lifecycle/SKILL.md"
else
  warn "OMP: worktree lifecycle skill missing — skipped"
fi
if [ -f "$ORCHESTRATOR_SKILL" ]; then
  install_managed_copy "$ORCHESTRATOR_SKILL" "$OMP_AGENT/skills/smart-development-orchestrator/SKILL.md"
else
  warn "OMP: smart development orchestrator skill missing — skipped"
fi
install_router_group
if [ -f "$OMP_AGENTS_SOURCE/minimax-worker.md" ]; then
  install_managed_copy "$OMP_AGENTS_SOURCE/minimax-worker.md" "$OMP_AGENT/agents/minimax-worker.md"
else
  warn "OMP: MiniMax worker agent missing — skipped"
fi

ok "OMP: native MCP servers, skills, smart routing agents, and placement rules wired -> $OMP_AGENT"
state_set '.agents["omp"]' "{\"config\":\"$OMP_AGENT\",\"wired\":true}"

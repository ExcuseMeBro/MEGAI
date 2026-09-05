#!/usr/bin/env bash
# Install MEGAI skills, shell CLI bridges and tools through Pi MCP Adapter.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

PI_AGENT="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
PI_MCP_CONFIG="$PI_AGENT/mcp.json"
TASK_FLOW_SKILL="$MEGAI_HOME/task-flow/skills/megai-task-flow/SKILL.md"
WORKTREE_SKILL="$MEGAI_HOME/skills/agent-worktree-lifecycle/SKILL.md"
MODE="${1:-install}"
ZG_BIN="$(state_get '.tools["zvec-grep"].bin' 2>/dev/null || true)"
if [ -z "$ZG_BIN" ] || [ ! -x "$ZG_BIN" ]; then
  ZG_BIN="$(command -v zg 2>/dev/null || true)"
fi

wire_megai_mcp() {
  command -v jq >/dev/null 2>&1 || {
    warn "pi: jq missing — MCP tools not wired"
    return 0
  }
  mkdir -p "$PI_AGENT" "$MEGAI_HOME/backups"
  [ -f "$PI_MCP_CONFIG" ] || echo '{"mcpServers":{}}' >"$PI_MCP_CONFIG"
  if ! jq -e 'type == "object"' "$PI_MCP_CONFIG" >/dev/null 2>&1; then
    warn "pi: invalid MCP config — MCP tools not wired: $PI_MCP_CONFIG"
    return 0
  fi

  local backup
  backup="$(mktemp "$MEGAI_HOME/backups/pi.mcp.json.bak.XXXXXX")"
  cp "$PI_MCP_CONFIG" "$backup"
  local tmp
  tmp="$(mktemp)"
  # Pi gets memory and structural code intelligence through lightweight shell
  # CLI bridges. zvec-grep is global MCP because semantic/hybrid retrieval is its
  # agent-native interface. Keep Asana lazy and remove legacy specialist MCPs.
  if [ "$MODE" = "--remove" ]; then
    jq '
      del(.mcpServers["megai-dembrandt"], .mcpServers["megai-argent"], .mcpServers["megai-repowise"], .mcpServers.zvec_grep)
      | if .mcpServers.asana? then .mcpServers.asana.lifecycle = "lazy" else . end
    ' "$PI_MCP_CONFIG" >"$tmp" && mv "$tmp" "$PI_MCP_CONFIG"
  elif [ -n "$ZG_BIN" ]; then
    jq --arg zg "$ZG_BIN" '
      del(.mcpServers["megai-dembrandt"], .mcpServers["megai-argent"], .mcpServers["megai-repowise"])
      | .mcpServers.zvec_grep = {command: $zg, args: ["server", "--stdio"]}
      | if .mcpServers.asana? then .mcpServers.asana.lifecycle = "lazy" else . end
    ' "$PI_MCP_CONFIG" >"$tmp" && mv "$tmp" "$PI_MCP_CONFIG"
  else
    jq '
      del(.mcpServers["megai-dembrandt"], .mcpServers["megai-argent"], .mcpServers["megai-repowise"], .mcpServers.zvec_grep)
      | if .mcpServers.asana? then .mcpServers.asana.lifecycle = "lazy" else . end
    ' "$PI_MCP_CONFIG" >"$tmp" && mv "$tmp" "$PI_MCP_CONFIG"
    warn "pi: zvec-grep missing — global MCP entry skipped"
  fi
}

configure_default_model() {
  command -v pi >/dev/null 2>&1 || return 0
  command -v jq >/dev/null 2>&1 || return 0

  local models first provider model settings current current_provider current_model tmp
  models="$(pi --list-models 2>/dev/null || true)"
  first="$(printf '%s\n' "$models" | awk 'NF >= 6 && $1 != "provider" && $1 !~ /^(Warning:|Error:)$/ { print $1 "\t" $2; exit }')"

  if [ -z "$first" ]; then
    warn "pi: no authenticated models yet"
    echo "    Run 'pi', enter /login, and choose a provider. Credentials will be stored globally in $PI_AGENT/auth.json"
    return 0
  fi

  provider="${first%%$'\t'*}"
  model="${first#*$'\t'}"
  settings="$PI_AGENT/settings.json"
  current=""
  if [ -f "$settings" ] && jq -e 'type == "object"' "$settings" >/dev/null 2>&1; then
    current="$(jq -r '[(.defaultProvider // ""), (.defaultModel // "")] | @tsv' "$settings")"
  fi

  # Keep a valid user preference. Replace only missing or stale defaults.
  if [ -n "$current" ] && printf '%s\n' "$models" | awk -v wanted="$current" 'NF >= 6 && $1 != "provider" && ($1 "\t" $2) == wanted { found=1 } END { exit !found }'; then
    current_provider="${current%%$'\t'*}"
    current_model="${current#*$'\t'}"
    ok "pi: global model ready -> $current_provider/$current_model"
    return 0
  fi

  mkdir -p "$PI_AGENT"
  tmp="$(mktemp "$PI_AGENT/settings.json.XXXXXX")"
  if [ -f "$settings" ] && jq -e 'type == "object"' "$settings" >/dev/null 2>&1; then
    jq --arg provider "$provider" --arg model "$model" \
      '.defaultProvider = $provider | .defaultModel = $model' "$settings" >"$tmp"
  else
    jq -n --arg provider "$provider" --arg model "$model" \
      '{defaultProvider: $provider, defaultModel: $model}' >"$tmp"
  fi
  chmod 600 "$tmp"
  mv "$tmp" "$settings"
  ok "pi: global default model -> $provider/$model"
}

# Pi loads JS/TS extensions, not shell scripts. Keep these bridges on PATH.
remove_owned_bridge() {
  local link="$1" target="$2"
  if [ -L "$link" ] && [ "$(readlink "$link")" = "$target" ]; then
    rm "$link"
  fi
}
wire_cli_bridges() {
  local name target link
  mkdir -p "$MEGAI_HOME/bin"
  for name in memory codedb; do
    target="$MEGAI_HOME/pi-skill/extensions/$name.sh"
    link="$MEGAI_HOME/bin/megai-$name"
    remove_owned_bridge "$PI_AGENT/extensions/megai-$name.sh" "$target"
    if [ "$MODE" = "--remove" ]; then
      remove_owned_bridge "$link" "$target"
    elif { [ -e "$link" ] || [ -L "$link" ]; } && [ "$(readlink "$link" 2>/dev/null || true)" != "$target" ]; then
      warn "pi: preserving user-owned bridge: $link"
    else
      chmod +x "$target"
      ln -sf "$target" "$link"
    fi
  done
}

configure_skill_profile() {
  local settings="$PI_AGENT/settings.json" tmp backup
  [ -f "$settings" ] || printf '{}\n' > "$settings"
  jq -e 'type == "object" and ((.skills // []) | type == "array" or type == "object")' "$settings" >/dev/null || {
    warn "pi: invalid settings — preserved without changes"
    return 1
  }
  mkdir -p "$MEGAI_HOME/backups"
  backup="$(mktemp "$MEGAI_HOME/backups/pi.skills.json.XXXXXX")"
  cp "$settings" "$backup"
  tmp="$(mktemp "$PI_AGENT/settings.json.XXXXXX")"
  # Match Pi SettingsManager's legacy skills-object migration. Preserve an
  # explicit top-level enableSkillCommands value over the legacy nested value.
  jq '
    (if (.skills | type) == "object" then
      .skills as $legacy
      | (if ($legacy | has("enableSkillCommands")) and (has("enableSkillCommands") | not)
         then .enableSkillCommands = $legacy.enableSkillCommands else . end)
      | .skills = (if ($legacy.customDirectories | type) == "array"
                   then $legacy.customDirectories else [] end)
     else . end)
    | ["!caveman*", "!cavecrew", "!smart-development-orchestrator"] as $filters
    | .skills = (reduce $filters[] as $filter ((.skills // []);
        if index($filter) == null then . + [$filter] else . end))
  ' "$settings" > "$tmp"
  chmod 600 "$tmp"
  mv "$tmp" "$settings"
}

if [ "$MODE" = "--remove" ]; then
  wire_megai_mcp
  wire_cli_bridges
  # Preserve user-scope skill selection on unwiring; use pi config or its backup
  # to re-enable resources, rather than deleting potentially user-owned filters.
  rm -f "$PI_AGENT/skills/megai.md"
  rm -rf "$PI_AGENT/skills/megai-task-flow" "$PI_AGENT/skills/agent-worktree-lifecycle"
  ok "pi: megai skills + owned CLI bridges + MCP tools removed"
  exit 0
fi

mkdir -p "$PI_AGENT/skills" "$PI_AGENT/extensions"
wire_megai_mcp

# Skills
cp "$MEGAI_HOME/pi-skill/SKILL.md" "$PI_AGENT/skills/megai.md"
if [ -f "$TASK_FLOW_SKILL" ]; then
  mkdir -p "$PI_AGENT/skills/megai-task-flow"
  cp "$TASK_FLOW_SKILL" "$PI_AGENT/skills/megai-task-flow/SKILL.md"
else
  warn "pi: MEGAI task-flow skill missing — skipped"
fi
if [ -f "$WORKTREE_SKILL" ]; then
  mkdir -p "$PI_AGENT/skills/agent-worktree-lifecycle"
  cp "$WORKTREE_SKILL" "$PI_AGENT/skills/agent-worktree-lifecycle/SKILL.md"
else
  warn "pi: worktree lifecycle skill missing — skipped"
fi

wire_cli_bridges
configure_skill_profile

ok "pi: skills + CLI bridges installed -> $PI_AGENT"
configure_default_model
state_set '.agents["pi"]' "{\"config\":\"$PI_AGENT\",\"wired\":true}"

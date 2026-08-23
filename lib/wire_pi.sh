#!/usr/bin/env bash
# Install MEGAI skill/extensions and MCP tools through Pi MCP Adapter.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

PI_AGENT="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
PI_MCP_CONFIG="$PI_AGENT/mcp.json"
TASK_FLOW_SKILL="$MEGAI_HOME/task-flow/skills/megai-task-flow/SKILL.md"
MODE="${1:-install}"

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
  if [ "$MODE" = "--remove" ]; then
    jq 'del(.mcpServers["megai-dembrandt"], .mcpServers["megai-argent"], .mcpServers["megai-repowise"])' "$PI_MCP_CONFIG" >"$tmp" && mv "$tmp" "$PI_MCP_CONFIG"
    return 0
  fi

  local dembrandt_bin argent_bin repowise_bin has_dembrandt=false has_argent=false has_repowise=false
  dembrandt_bin="$(state_get '.tools["dembrandt"].mcpBin')"
  argent_bin="$(state_get '.tools["argent"].bin')"
  repowise_bin="$(state_get '.tools["repowise"].bin')"
  if [ -n "$dembrandt_bin" ] && [ -x "$dembrandt_bin" ]; then
    has_dembrandt=true
  else warn "pi: Dembrandt MCP skipped — executable missing"; fi
  if [ -n "$argent_bin" ] && [ -x "$argent_bin" ]; then
    has_argent=true
  else warn "pi: Argent MCP skipped — executable missing"; fi
  if [ -n "$repowise_bin" ] && [ -x "$repowise_bin" ]; then
    has_repowise=true
  else warn "pi: RepoWise MCP skipped — executable missing"; fi
  jq --arg dembrandt "$dembrandt_bin" --arg argent "$argent_bin" --arg repowise "$repowise_bin" \
    --argjson hasDembrandt "$has_dembrandt" --argjson hasArgent "$has_argent" --argjson hasRepowise "$has_repowise" '
    .mcpServers = (.mcpServers // {})
    | if $hasDembrandt then .mcpServers["megai-dembrandt"] = {command: $dembrandt} else del(.mcpServers["megai-dembrandt"]) end
    | if $hasArgent then .mcpServers["megai-argent"] = {command: $argent, args: ["mcp"]} else del(.mcpServers["megai-argent"]) end
    | if $hasRepowise then .mcpServers["megai-repowise"] = {command: $repowise, args: ["mcp"]} else del(.mcpServers["megai-repowise"]) end
  ' "$PI_MCP_CONFIG" >"$tmp" && mv "$tmp" "$PI_MCP_CONFIG"
  ok "pi: available MCP tools wired -> $PI_MCP_CONFIG"
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

if [ "$MODE" = "--remove" ]; then
  wire_megai_mcp
  rm -f "$PI_AGENT/skills/megai.md"
  rm -rf "$PI_AGENT/skills/megai-task-flow"
  rm -f "$PI_AGENT/extensions/megai-memory.sh" "$PI_AGENT/extensions/megai-codedb.sh"
  ok "pi: megai skills + extensions + MCP tools removed"
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

# Extensions: symlink (so updates propagate)
ln -sf "$MEGAI_HOME/pi-skill/extensions/memory.sh" "$PI_AGENT/extensions/megai-memory.sh"
ln -sf "$MEGAI_HOME/pi-skill/extensions/codedb.sh" "$PI_AGENT/extensions/megai-codedb.sh"
chmod +x "$MEGAI_HOME/pi-skill/extensions/"*.sh 2>/dev/null || true

ok "pi: skills + extensions installed -> $PI_AGENT"
configure_default_model
state_set '.agents["pi"]' "{\"config\":\"$PI_AGENT\",\"wired\":true}"

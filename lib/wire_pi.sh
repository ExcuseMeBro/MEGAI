#!/usr/bin/env bash
# Pi has no native MCP. Install megai skill + extensions instead.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

PI_AGENT="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
MODE="${1:-install}"

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
      '.defaultProvider = $provider | .defaultModel = $model' "$settings" > "$tmp"
  else
    jq -n --arg provider "$provider" --arg model "$model" \
      '{defaultProvider: $provider, defaultModel: $model}' > "$tmp"
  fi
  chmod 600 "$tmp"
  mv "$tmp" "$settings"
  ok "pi: global default model -> $provider/$model"
}

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
configure_default_model
state_set '.agents["pi"]' "{\"config\":\"$PI_AGENT\",\"wired\":true}"

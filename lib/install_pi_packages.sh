#!/usr/bin/env bash
# Install the recommended Pi package stack globally (user scope).
set -euo pipefail

MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"

if ! command -v pi >/dev/null 2>&1; then
  warn "pi CLI not found — recommended Pi packages skipped"
  exit 0
fi

PI_AGENT="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
SETTINGS="$PI_AGENT/settings.json"
PACKAGES=(
  "npm:@vigolium/piolium"
  "npm:pi-mcp-adapter"
  "npm:pi-web-access"
  "npm:pi-subagents"
  "npm:bigpowers"
  "npm:@dietrichgebert/ponytail"
  "npm:pi-lens"
  "npm:@narumitw/pi-statusline"
)

package_configured() {
  local source="$1"
  [ -f "$SETTINGS" ] || return 1
  jq -e --arg source "$source" '
    (.packages // []) | any(
      if type == "string" then . == $source
      elif type == "object" then .source == $source
      else false
      end
    )
  ' "$SETTINGS" >/dev/null 2>&1
}

installed=0
failed=0
for package in "${PACKAGES[@]}"; do
  if package_configured "$package"; then
    skip "pi package already installed: $package"
    continue
  fi

  if pi install "$package"; then
    ok "pi package installed: $package"
    installed=$((installed + 1))
  else
    warn "pi package install failed: $package"
    failed=$((failed + 1))
  fi
done

if [ "$failed" -gt 0 ]; then
  warn "pi packages: $installed installed, $failed failed"
else
  ok "pi package stack ready (${#PACKAGES[@]} packages)"
fi

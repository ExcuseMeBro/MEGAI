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
if [ -L "$SETTINGS" ] || { [ -e "$SETTINGS" ] && [ ! -f "$SETTINGS" ]; }; then
  die "refusing symlinked or non-file Pi settings: $SETTINGS"
fi
if [ -f "$SETTINGS" ] && ! jq -e 'type == "object"' "$SETTINGS" >/dev/null 2>&1; then
  die "refusing malformed Pi settings: $SETTINGS"
fi
CORE_PACKAGES=(
  "npm:pi-mcp-adapter"
)
PACKAGES=("${CORE_PACKAGES[@]}")

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

  if [ -f "$SETTINGS" ]; then
    mkdir -p "$MEGAI_HOME/backups"
    backup="$(mktemp "$MEGAI_HOME/backups/pi-packages.XXXXXX")"
    cp "$SETTINGS" "$backup"
  fi
  if pi install "$package"; then
    ok "pi package installed: $package"
    installed=$((installed + 1))
  else
    warn "pi package install failed: $package"
    failed=$((failed + 1))
  fi
done

# Slim never removes package names from an existing settings file: a matching
# source can still be user-owned. The old full-profile flag has no effect here.
if [ "$failed" -gt 0 ]; then
  die "pi packages: $installed installed, $failed failed"
else
  ok "pi package stack ready (${#PACKAGES[@]} packages)"
fi

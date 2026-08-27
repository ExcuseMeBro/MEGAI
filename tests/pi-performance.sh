#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

export HOME="$TMP/home"
export MEGAI_HOME="$TMP/megai"
PI_AGENT="$HOME/.pi/agent"
mkdir -p "$PI_AGENT" "$MEGAI_HOME/lib" "$TMP/bin"
cp "$ROOT/lib/install_pi_packages.sh" "$ROOT/lib/ui.sh" "$MEGAI_HOME/lib/"

cat >"$PI_AGENT/settings.json" <<'JSON'
{
  "defaultThinkingLevel": "medium",
  "packages": [
    "npm:pi-mcp-adapter",
    "npm:pi-web-access",
    "npm:pi-subagents",
    "npm:@vigolium/piolium",
    "npm:bigpowers",
    "npm:@dietrichgebert/ponytail",
    "npm:pi-lens",
    "npm:@narumitw/pi-statusline",
    "npm:user-owned-extension",
    {"source": "npm:user-owned-object", "enabled": true}
  ]
}
JSON

cat >"$TMP/bin/pi" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
[ "${1:-}" = "install" ]
source="${2:?package source required}"
settings="$HOME/.pi/agent/settings.json"
tmp="$(mktemp "$HOME/.pi/agent/settings.json.XXXXXX")"
jq --arg source "$source" '
  if any((.packages // [])[]; type == "object" and .source == $source) then
    .packages = [(.packages // [])[] | if type == "object" and .source == $source then .enabled = true else . end]
  else
    .packages = ((.packages // []) + [$source])
  end
' "$settings" >"$tmp"
mv "$tmp" "$settings"
SH
chmod +x "$TMP/bin/pi"
export PATH="$TMP/bin:$PATH"

bash "$MEGAI_HOME/lib/install_pi_packages.sh" >/dev/null
jq -e '
  .packages == [
    "npm:pi-mcp-adapter",
    "npm:@narumitw/pi-statusline",
    "npm:user-owned-extension",
    {"source": "npm:user-owned-object", "enabled": true}
  ]
' "$PI_AGENT/settings.json" >/dev/null

# Full mode must enable or install the complete optional package stack.
cp "$PI_AGENT/settings.json" "$TMP/lean-settings.json"
jq '.packages += [
  {"source": "npm:pi-web-access", "enabled": false},
  "npm:pi-subagents"
]' "$PI_AGENT/settings.json" >"$TMP/full-settings.json"
mv "$TMP/full-settings.json" "$PI_AGENT/settings.json"
MEGAI_PI_FULL=1 bash "$MEGAI_HOME/lib/install_pi_packages.sh" >/dev/null
jq -e '
  def source: if type == "string" then . else .source end;
  ([
    "npm:@vigolium/piolium",
    "npm:pi-web-access",
    "npm:pi-subagents",
    "npm:bigpowers",
    "npm:@dietrichgebert/ponytail",
    "npm:pi-lens"
  ] - [.packages[] | source]) == []
  and any(.packages[]; type == "object" and .source == "npm:pi-web-access" and .enabled == true)
  and any(.packages[]; source == "npm:user-owned-extension")
  and any(.packages[]; source == "npm:user-owned-object")
' "$PI_AGENT/settings.json" >/dev/null

echo "Pi performance defaults: ok"

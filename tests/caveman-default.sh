#!/usr/bin/env bash
# Caveman core + slim wiring contract; no upstream installer or network calls.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home" MEGAI_HOME="$TMP/megai" CALLS="$TMP/calls" PKGROOT="$TMP/npm-root"
export PI_CODING_AGENT_DIR="$HOME/.pi/agent" MEGAI_SOURCE="$ROOT"
mkdir -p "$MEGAI_HOME/lib" "$TMP/bin" "$PKGROOT/caveman-installer/skills/caveman" "$PI_CODING_AGENT_DIR"
cp "$ROOT/lib/ui.sh" "$ROOT/lib/state.sh" "$ROOT/lib/slim_wiring.py" "$ROOT/lib/install_caveman.sh" "$MEGAI_HOME/lib/"
printf 'packaged core\n' > "$PKGROOT/caveman-installer/skills/caveman/SKILL.md"
printf '{"tools":{"keep":{"version":"1"}}}\n' > "$MEGAI_HOME/state.json"
cat > "$TMP/bin/caveman" <<'SH'
#!/bin/sh
echo FORBIDDEN >> "$CALLS"
exit 1
SH
cat > "$TMP/bin/npm" <<'SH'
#!/bin/sh
case "$1" in
  root) printf '%s\n' "$PKGROOT" ;;
  list) printf '{"dependencies":{"caveman-installer":{"version":"2.2.0"}}}\n' ;;
  *) echo FORBIDDEN >> "$CALLS"; exit 1 ;;
esac
SH
for command in codedb zg; do
  printf '#!/bin/sh\nexit 0\n' > "$TMP/bin/$command"
done
chmod +x "$TMP/bin/"*
export PATH="$TMP/bin:$PATH"
: > "$CALLS"

# Explicit opt-out does nothing and does not invoke npm or the Caveman CLI.
MEGAI_CAVEMAN=0 bash "$ROOT/lib/install_caveman.sh" >/dev/null
[ ! -e "$HOME/.agents/skills/caveman/SKILL.md" ] && [ ! -s "$CALLS" ]

# Default installation copies/reuses only the core skill and records state.
env -u MEGAI_CAVEMAN bash "$ROOT/lib/install_caveman.sh" >/dev/null
[ "$(< "$HOME/.agents/skills/caveman/SKILL.md")" = 'packaged core' ]
printf 'user core\n' > "$HOME/.agents/skills/caveman/SKILL.md"
env -u MEGAI_CAVEMAN bash "$ROOT/lib/install_caveman.sh" >/dev/null
[ "$(< "$HOME/.agents/skills/caveman/SKILL.md")" = 'user core' ]
[ ! -s "$CALLS" ] && [ ! -e "$HOME/.agents/skills/cavecrew" ]
jq -e '.tools.keep.version == "1" and .tools.caveman.version == "2.2.0"' "$MEGAI_HOME/state.json" >/dev/null
[ -f "$MEGAI_HOME/lib/install_caveman.sh" ]

# Slim Pi wiring enables exactly the core path, excludes companions, and keeps
# models, packages, auth, MCP and unrelated settings byte-for-byte unchanged.
printf '{"defaultProvider":"keep-provider","defaultModel":"keep-model","defaultThinkingLevel":"high","packages":["keep-package"],"skills":["!*","+keep"]}\n' > "$PI_CODING_AGENT_DIR/settings.json"
printf '{"private-test":"unchanged"}\n' > "$PI_CODING_AGENT_DIR/auth.json"
printf '{"mcpServers":{"user":{"command":"keep"}}}\n' > "$PI_CODING_AGENT_DIR/mcp.json"
cp "$PI_CODING_AGENT_DIR/settings.json" "$TMP/settings.before"
cp "$PI_CODING_AGENT_DIR/auth.json" "$TMP/auth.before"
cp "$PI_CODING_AGENT_DIR/mcp.json" "$TMP/mcp.before"
python3 "$ROOT/lib/slim_wiring.py" pi >/dev/null
core="+$HOME/.agents/skills/caveman/SKILL.md"
jq -e --arg core "$core" '
  .defaultProvider == "keep-provider" and .defaultModel == "keep-model"
  and .defaultThinkingLevel == "high" and .packages == ["keep-package"]
  and (.skills | index("!*")) != null
  and (.skills | index("!caveman*")) != null
  and (.skills | index("!cavecrew")) != null
  and (.skills | index($core)) != null
  and ([.skills[] | select(. == $core)] | length) == 1
' "$PI_CODING_AGENT_DIR/settings.json" >/dev/null
cmp "$PI_CODING_AGENT_DIR/auth.json" "$TMP/auth.before"
# User MCP/config data remains unchanged apart from the managed zvec entry.
jq -e '.mcpServers.user.command == "keep"' "$PI_CODING_AGENT_DIR/mcp.json" >/dev/null
python3 "$ROOT/lib/slim_wiring.py" pi >/dev/null
cmp "$PI_CODING_AGENT_DIR/auth.json" "$TMP/auth.before"
[ ! -e "$HOME/.claude/hooks" ] && [ ! -e "$HOME/.agents/skills/cavecrew" ]

# Opt-out removes only the managed core selection and keeps the exclusion.
MEGAI_CAVEMAN=0 python3 "$ROOT/lib/slim_wiring.py" pi >/dev/null
jq -e --arg core "$core" '(.skills | index($core)) == null and (.skills | index("!caveman*")) != null and .defaultModel == "keep-model"' "$PI_CODING_AGENT_DIR/settings.json" >/dev/null
cmp "$PI_CODING_AGENT_DIR/auth.json" "$TMP/auth.before"

# Concurrent/custom edits fail closed rather than overwriting unrelated settings.
jq '.defaultModel = "user-edited"' "$PI_CODING_AGENT_DIR/settings.json" > "$TMP/edited.json"
mv "$TMP/edited.json" "$PI_CODING_AGENT_DIR/settings.json"
cp "$PI_CODING_AGENT_DIR/settings.json" "$TMP/edited.before"
if MEGAI_CAVEMAN=1 python3 "$ROOT/lib/slim_wiring.py" pi >/dev/null 2>&1; then
  echo 'custom Pi settings unexpectedly overwritten' >&2
  exit 1
fi
cmp "$PI_CODING_AGENT_DIR/settings.json" "$TMP/edited.before"

echo 'Caveman default PASS: slim core-only selection, default-on/opt-out, no companions/hooks/force-wiring, settings/models/auth preserved'

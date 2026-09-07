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

# A genuinely fresh HOME passes the public install preflight before the core
# exists; normal check remains fail-closed until install_caveman creates it.
grep -Fq 'slim_wiring.py" all --check --install-preflight' "$ROOT/install.sh"
grep -Fq 'slim_wiring.py" all --check --install-preflight' "$ROOT/lib/main.sh"
env -u MEGAI_CAVEMAN python3 "$ROOT/lib/slim_wiring.py" all --check --install-preflight >/dev/null
[ ! -e "$HOME/.agents/skills/caveman/SKILL.md" ] && [ ! -e "$MEGAI_HOME/slim-wiring.json" ]
if env -u MEGAI_CAVEMAN python3 "$ROOT/lib/slim_wiring.py" all --check >/dev/null 2>&1; then
  echo 'normal preflight unexpectedly accepted missing enabled Caveman core' >&2
  exit 1
fi
if env -u MEGAI_CAVEMAN python3 "$ROOT/lib/slim_wiring.py" pi --verify >/dev/null 2>&1; then
  echo 'normal verify unexpectedly accepted missing enabled Caveman core' >&2
  exit 1
fi

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

# Legacy Pi skills dictionaries are validated before any write; unknown keys,
# malformed customDirectories and malformed values are never discarded.
for legacy_json in \
  '{"skills":{"customDirectories":[],"unexpected":true}}' \
  '{"skills":{"customDirectories":"not-an-array"}}' \
  '{"skills":{"customDirectories":[42]}}'; do
  LEGACY_HOME="$TMP/legacy-home-${RANDOM}"
  LEGACY_MEGAI="$TMP/legacy-megai-${RANDOM}"
  LEGACY_PI="$LEGACY_HOME/.pi/agent"
  mkdir -p "$LEGACY_PI" "$LEGACY_HOME/.agents/skills/caveman" "$LEGACY_MEGAI/lib"
  cp "$MEGAI_HOME/state.json" "$LEGACY_MEGAI/state.json"
  printf 'core\n' > "$LEGACY_HOME/.agents/skills/caveman/SKILL.md"
  printf '%s\n' "$legacy_json" > "$LEGACY_PI/settings.json"
  printf '{}\n' > "$LEGACY_PI/mcp.json"
  cp "$LEGACY_PI/settings.json" "$TMP/legacy.before"
  if HOME="$LEGACY_HOME" MEGAI_HOME="$LEGACY_MEGAI" PI_CODING_AGENT_DIR="$LEGACY_PI" MEGAI_SOURCE="$ROOT" python3 "$ROOT/lib/slim_wiring.py" pi >/dev/null 2>&1; then
    echo "legacy Pi settings unexpectedly accepted: $legacy_json" >&2
    exit 1
  fi
  cmp "$LEGACY_PI/settings.json" "$TMP/legacy.before"
  [ ! -e "$LEGACY_MEGAI/slim-wiring.json" ]
done

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

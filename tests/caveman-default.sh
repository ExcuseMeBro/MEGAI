#!/usr/bin/env bash
# Real core installer/profile function; no upstream installer or network calls.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home" MEGAI_HOME="$TMP/megai" CALLS="$TMP/calls" PKGROOT="$TMP/npm-root"
mkdir -p "$MEGAI_HOME/lib" "$TMP/bin" "$PKGROOT/caveman-installer/skills/caveman" "$HOME/.pi/agent"
cp "$ROOT/lib/"{ui,state}.sh "$MEGAI_HOME/lib/"
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
chmod +x "$TMP/bin/"*
export PATH="$TMP/bin:$PATH"
: > "$CALLS"
MEGAI_CAVEMAN=0 bash "$ROOT/lib/install_caveman.sh" >/dev/null
[ ! -e "$HOME/.agents/skills/caveman/SKILL.md" ] && [ ! -s "$CALLS" ]
env -u MEGAI_CAVEMAN bash "$ROOT/lib/install_caveman.sh" >/dev/null
[ "$(< "$HOME/.agents/skills/caveman/SKILL.md")" = 'packaged core' ]
printf 'user core\n' > "$HOME/.agents/skills/caveman/SKILL.md"
env -u MEGAI_CAVEMAN bash "$ROOT/lib/install_caveman.sh" >/dev/null
[ "$(< "$HOME/.agents/skills/caveman/SKILL.md")" = 'user core' ]
[ ! -s "$CALLS" ] && [ ! -e "$HOME/.agents/skills/cavecrew" ]
jq -e '.tools.keep.version == "1" and .tools.caveman.version == "2.2.0"' "$MEGAI_HOME/state.json" >/dev/null
. "$MEGAI_HOME/lib/ui.sh"
PI_AGENT="$HOME/.pi/agent"
eval "$(awk '/^configure_skill_profile\(\)/ {p=1} p {print} p && /^}/ {exit}' "$ROOT/lib/wire_pi.sh")"
printf '{"skills":["!*","+keep"],"defaultModel":"keep","packages":["keep"]}\n' > "$PI_AGENT/settings.json"
unset MEGAI_CAVEMAN
configure_skill_profile
configure_skill_profile
core="+$HOME/.agents/skills/caveman/SKILL.md"
jq -e --arg core "$core" '.skills[-1] == $core and ([.skills[] | select(. == $core)] | length) == 1 and .skills[0:2] == ["!*","+keep"] and (.skills | index("!cavecrew")) != null and .defaultModel == "keep" and .packages == ["keep"]' "$PI_AGENT/settings.json" >/dev/null
MEGAI_CAVEMAN=0 configure_skill_profile
jq -e --arg core "$core" '(.skills | index($core)) == null and (.skills | index("!caveman*")) != null and .defaultModel == "keep"' "$PI_AGENT/settings.json" >/dev/null
[ "$(< "$HOME/.agents/skills/caveman/SKILL.md")" = 'user core' ]
echo 'Caveman default PASS: core-only, opt-out, no force-wiring, user content/model/settings preserved'

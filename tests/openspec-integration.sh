#!/usr/bin/env bash
# Offline retirement: only registered owned links/state may be removed.
set -euo pipefail
ROOT="${MEGAI_TEST_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home" MEGAI_HOME="$TMP/megai" CALLS="$TMP/calls"
export PI_CODING_AGENT_DIR="$HOME/.pi/agent"
source_path="$MEGAI_HOME/skills/megai-openspec"
current="$PI_CODING_AGENT_DIR/skills/megai-openspec"
custom="$TMP/custom pi"$'\n'"profile/skills/megai-openspec"
foreign="$TMP/foreign/megai-openspec"
user="$TMP/user/megai-openspec"
mkdir -p "$MEGAI_HOME/lib" "$(dirname "$current")" "$(dirname "$custom")" "$(dirname "$foreign")" "$user" "$TMP/bin" "$TMP/project/openspec"
cp "$ROOT/lib/ui.sh" "$ROOT/lib/state.sh" "$ROOT/lib/slim_wiring.py" "$MEGAI_HOME/lib/"
ln -s "$source_path" "$current" # dangling owned link: source already retired
ln -s "$source_path" "$custom"
ln -s "$TMP/foreign-missing" "$foreign"
printf 'user skill\n' > "$user/SKILL.md"
printf 'preserve spec\n' > "$TMP/project/openspec/spec.md"
printf '#!/bin/sh\necho FORBIDDEN >> "$CALLS"\nexit 1\n' > "$TMP/bin/openspec"
chmod +x "$TMP/bin/openspec"
export PATH="$TMP/bin:$PATH"
jq -n --arg current "$current" --arg custom "$custom" --arg foreign "$foreign" --arg user "$user" '{tools:{keep:{version:"1"},openspec:{destinations:[$current,$custom,$foreign,$user]}},privacy:{enabled:false}}' > "$MEGAI_HOME/state.json"
: > "$CALLS"
cd "$TMP/project"
bash "$ROOT/lib/retire_openspec.sh" >/dev/null
bash "$ROOT/lib/retire_openspec.sh" >/dev/null
[ ! -L "$current" ] && [ ! -L "$custom" ]
[ "$(readlink "$foreign")" = "$TMP/foreign-missing" ]
[ "$(< "$user/SKILL.md")" = 'user skill' ]
[ "$(< "$TMP/project/openspec/spec.md")" = 'preserve spec' ]
[ -x "$TMP/bin/openspec" ] && [ ! -s "$CALLS" ]
jq -e '.tools == {keep:{version:"1"}} and .privacy == {enabled:false}' "$MEGAI_HOME/state.json" >/dev/null
# Invalid state must fail before unlinking even the current owned destination.
ln -s "$source_path" "$current"
for invalid in '' null '[]' '{} {}' '{broken'; do
  printf '%s' "$invalid" > "$MEGAI_HOME/state.json"
  if bash "$ROOT/lib/retire_openspec.sh" > "$TMP/invalid.log" 2>&1; then exit 1; fi
  [ -L "$current" ]
  [ "$(< "$MEGAI_HOME/state.json")" = "$invalid" ]
done
[ ! -f "$ROOT/lib/install_openspec.sh" ]
[ ! -e "$ROOT/skills/megai-openspec" ]
if grep -Fq 'install_openspec.sh' "$ROOT/bin/megai" "$ROOT/lib/main.sh"; then exit 1; fi
for file in "$ROOT/bin/megai" "$ROOT/lib/main.sh"; do grep -Fq 'bash "$LIB/retire_openspec.sh"' "$file"; done
echo 'OpenSpec retirement PASS: owned/custom/dangling links removed; foreign skills, specs, independent CLI and unrelated state preserved'

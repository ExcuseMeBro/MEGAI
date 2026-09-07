#!/usr/bin/env bash
# Offline retirement: preserve foreign skills, independent CLI and user reports.
set -euo pipefail
ROOT="${MEGAI_TEST_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home" MEGAI_HOME="$TMP/megai" CALLS="$TMP/calls"
export PI_CODING_AGENT_DIR="$TMP/custom pi"
export NUMASEC_SKILL_SOURCE="$MEGAI_HOME/skills/numasec-security"
mkdir -p "$MEGAI_HOME/lib" "$TMP/bin" "$HOME/.agents/skills/numasec-security" "$HOME/.claude/skills" "$HOME/.codex/skills" "$PI_CODING_AGENT_DIR/skills" "$TMP/project/reports"
cp "$ROOT/lib/"{ui,state,detect,banner}.sh "$MEGAI_HOME/lib/"
cp "$ROOT/lib/slim_wiring.py" "$MEGAI_HOME/lib/"
printf 'user skill\n' > "$HOME/.agents/skills/numasec-security/SKILL.md"
for root in "$HOME/.claude/skills" "$HOME/.codex/skills"; do ln -s "$NUMASEC_SKILL_SOURCE" "$root/numasec-security"; done
ln -s "$TMP/foreign-missing" "$PI_CODING_AGENT_DIR/skills/numasec-security"
printf 'user report\n' > "$TMP/project/reports/keep.md"
printf '#!/bin/sh\necho FORBIDDEN >> "$CALLS"\nexit 1\n' > "$TMP/bin/numasec"
printf '#!/bin/sh\nexit 0\n' > "$TMP/bin/agentmemory"
chmod +x "$TMP/bin/"*
export PATH="$TMP/bin:$PATH"
printf '{"tools":{"numasec":{"version":"old"},"keep":{"version":"1"}},"projects":{"keep":true}}\n' > "$MEGAI_HOME/state.json"
: > "$CALLS"
cd "$TMP/project"
bash "$ROOT/lib/retire_numasec.sh" >/dev/null
bash "$ROOT/lib/retire_numasec.sh" >/dev/null
[ ! -L "$HOME/.claude/skills/numasec-security" ]
[ ! -L "$HOME/.codex/skills/numasec-security" ]
[ "$(readlink "$PI_CODING_AGENT_DIR/skills/numasec-security")" = "$TMP/foreign-missing" ]
[ "$(< "$HOME/.agents/skills/numasec-security/SKILL.md")" = 'user skill' ]
[ "$(< "$TMP/project/reports/keep.md")" = 'user report' ]
jq -e '.tools == {keep:{version:"1"}} and .projects == {keep:true}' "$MEGAI_HOME/state.json" >/dev/null
if bash "$ROOT/bin/megai" security > "$TMP/security.out" 2>&1; then exit 1; fi
bash "$ROOT/bin/megai" status > "$TMP/status.out"
# Slim status is the supported retirement surface; doctor requires a complete
# nine-tool installation and is covered by the slim distribution contract.
if grep -qi numasec "$TMP/status.out"; then exit 1; fi
[ ! -s "$CALLS" ] && [ -x "$TMP/bin/numasec" ]
# Malformed state must stop before unlinking the current owned skill.
ln -s "$NUMASEC_SKILL_SOURCE" "$HOME/.claude/skills/numasec-security"
for invalid in '' null '[]' '{} {}' '{broken'; do
  printf '%s' "$invalid" > "$MEGAI_HOME/state.json"
  if bash "$ROOT/lib/retire_numasec.sh" > "$TMP/invalid.out" 2>&1; then exit 1; fi
  [ -L "$HOME/.claude/skills/numasec-security" ]
  [ "$(< "$MEGAI_HOME/state.json")" = "$invalid" ]
done
[ ! -f "$ROOT/lib/install_numasec.sh" ] && [ ! -e "$ROOT/skills/numasec-security" ]
if grep -vF 'bash "$LIB/retire_numasec.sh"' "$ROOT/bin/megai" | grep -qi numasec; then exit 1; fi
if grep -qi numasec "$ROOT/lib/main.sh"; then exit 1; fi
echo 'Numasec retirement PASS: no launcher/advertising; owned links cleaned; foreign skills, CLI, reports and unrelated state retained'

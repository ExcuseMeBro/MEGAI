#!/usr/bin/env bash
# Offline retirement of owned copies; never launches an app/device review.
set -euo pipefail
ROOT="${MEGAI_TEST_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home" MEGAI_HOME="$TMP/megai" CALLS="$TMP/calls"
export PI_CODING_AGENT_DIR="$TMP/custom pi"
mkdir -p "$MEGAI_HOME/lib" "$TMP/bin" "$TMP/project/reports"
cp "$ROOT/lib/"{ui,state,detect,banner}.sh "$MEGAI_HOME/lib/"
for root in "$HOME/.agents/skills" "$HOME/.claude/skills" "$PI_CODING_AGENT_DIR/skills" "$HOME/.omp/agent/skills" "$HOME/.omp/profiles/work/agent/skills"; do
  mkdir -p "$root/argent"
  printf 'managed-by: megai\nowned\n' > "$root/argent/SKILL.md"
done
mkdir -p "$HOME/.claude/commands"
printf 'managed-by: megai\nowned\n' > "$HOME/.claude/commands/argent.md"
printf 'user skill\n' > "$HOME/.agents/skills/argent/SKILL.md"
printf 'managed-by: megai\nforeign file\n' > "$TMP/foreign.md"
rm "$PI_CODING_AGENT_DIR/skills/argent/SKILL.md"
ln -s "$TMP/foreign.md" "$PI_CODING_AGENT_DIR/skills/argent/SKILL.md"
printf 'user report\n' > "$TMP/project/reports/keep.md"
printf '#!/bin/sh\necho FORBIDDEN >> "$CALLS"\nexit 1\n' > "$TMP/bin/argent"
printf '#!/bin/sh\nexit 0\n' > "$TMP/bin/agentmemory"
chmod +x "$TMP/bin/"*
export PATH="$TMP/bin:$PATH"
printf '{"tools":{"argent":{"version":"old"},"keep":{"version":"1"}},"projects":{"keep":true}}\n' > "$MEGAI_HOME/state.json"
: > "$CALLS"
cd "$TMP/project"
bash "$ROOT/lib/retire_argent.sh" >/dev/null
bash "$ROOT/lib/retire_argent.sh" >/dev/null
for p in "$HOME/.claude/skills/argent/SKILL.md" "$HOME/.omp/agent/skills/argent/SKILL.md" "$HOME/.omp/profiles/work/agent/skills/argent/SKILL.md" "$HOME/.claude/commands/argent.md"; do [ ! -e "$p" ]; done
[ "$(< "$HOME/.agents/skills/argent/SKILL.md")" = 'user skill' ]
[ "$(readlink "$PI_CODING_AGENT_DIR/skills/argent/SKILL.md")" = "$TMP/foreign.md" ]
[ "$(< "$TMP/foreign.md")" = $'managed-by: megai\nforeign file' ]
[ "$(< "$TMP/project/reports/keep.md")" = 'user report' ]
jq -e '.tools == {keep:{version:"1"}} and .projects == {keep:true}' "$MEGAI_HOME/state.json" >/dev/null
bash "$ROOT/bin/megai" status > "$TMP/status.out"
bash "$ROOT/bin/megai" doctor > "$TMP/doctor.out" 2>&1
if grep -qi argent "$TMP/status.out" "$TMP/doctor.out"; then exit 1; fi
[ ! -s "$CALLS" ] && [ -x "$TMP/bin/argent" ]
printf 'managed-by: megai\nowned\n' > "$HOME/.agents/skills/argent/SKILL.md"
printf '{broken' > "$MEGAI_HOME/state.json"
if bash "$ROOT/lib/retire_argent.sh" > "$TMP/invalid.out" 2>&1; then exit 1; fi
[ -f "$HOME/.agents/skills/argent/SKILL.md" ]
[ "$(< "$MEGAI_HOME/state.json")" = '{broken' ]
[ ! -f "$ROOT/lib/install_argent.sh" ] && [ ! -e "$ROOT/skills/argent" ]
[ ! -f "$ROOT/task-flow/commands/argent.md" ]
if grep -vF 'bash "$LIB/retire_argent.sh"' "$ROOT/bin/megai" | grep -qi argent; then exit 1; fi
if grep -qi argent "$ROOT/lib/main.sh"; then exit 1; fi
echo 'Argent retirement PASS: owned artifacts cleaned; foreign files/links, reports, independent CLI and unrelated state retained'

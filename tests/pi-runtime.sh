#!/usr/bin/env bash
# Real wiring/dispatch with fake backends: no model requests, services or indexes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home" MEGAI_HOME="$TMP/megai" PI_CODING_AGENT_DIR="$TMP/custom-pi"
export CALLS="$TMP/calls"
mkdir -p "$HOME" "$MEGAI_HOME" "$PI_CODING_AGENT_DIR" "$TMP/bin" "$TMP/project with spaces"
cp -R "$ROOT/lib" "$ROOT/pi-skill" "$ROOT/task-flow" "$ROOT/skills" "$MEGAI_HOME/"
printf '{"tools":{},"agents":{},"projects":{}}\n' > "$MEGAI_HOME/state.json"
printf '{"defaultProvider":"keep","defaultModel":"keep","defaultThinkingLevel":"high","packages":["user-package"],"skills":["user-skill"]}\n' > "$PI_CODING_AGENT_DIR/settings.json"
printf '#!/bin/sh\nexit 0\n' > "$TMP/bin/pi"
cat > "$TMP/bin/codedb" <<'SH'
#!/bin/sh
printf '%s\n' "$@" > "$CALLS"
case "$1" in find|outline|search) exit 0 ;; esac
[ "$#" = 2 ] && [ "$2" = tree ]
SH
cat > "$TMP/bin/curl" <<'SH'
#!/bin/sh
printf '%s\n' "$@" > "$CALLS"
printf '{"ok":true}\n'
SH
chmod +x "$TMP/bin/"*
export PATH="$TMP/bin:$MEGAI_HOME/bin:$PATH"
bash "$MEGAI_HOME/lib/wire_pi.sh" >/dev/null
command -v megai-memory >/dev/null
command -v megai-codedb >/dev/null
megai-memory stats | grep -q '"ok":true'
grep -Fxq -- '--max-time' "$CALLS"
megai-codedb symbol 'a name'
[ "$(< "$CALLS")" = $'find\na name' ]
megai-codedb tree "$TMP/project with spaces"
[ "$(< "$CALLS")" = "$TMP/project with spaces"$'\ntree' ]
megai-codedb index "$TMP/project with spaces"
[ "$(< "$CALLS")" = "$TMP/project with spaces"$'\ntree' ]
[ ! -L "$PI_CODING_AGENT_DIR/extensions/megai-memory.sh" ]
# Repeated wiring preserves user settings and does not duplicate exclusions.
bash "$MEGAI_HOME/lib/wire_pi.sh" >/dev/null
jq -e '.defaultProvider == "keep" and .defaultModel == "keep" and .defaultThinkingLevel == "high" and .packages == ["user-package"] and .skills[0] == "user-skill" and ([.skills[] | select(. == "!caveman*")] | length) == 1 and (.skills | index("!smart-development-orchestrator")) != null' "$PI_CODING_AGENT_DIR/settings.json" >/dev/null

# Exercise actual project warmup and caching against the installed CLI grammar.
source "$ROOT/bin/megai" --help >/dev/null
ensure_codedb_index "$TMP/project with spaces" >/dev/null
jq -e --arg p "$TMP/project with spaces" '.projects[$p].indexed_at != null' "$MEGAI_HOME/state.json" >/dev/null
printf 'cached\n' > "$CALLS"
ensure_codedb_index "$TMP/project with spaces" >/dev/null
[ "$(< "$CALLS")" = cached ]

# Exercise actual startup dispatch without spawning any background job.
printf '#!/bin/sh\nexit 0\n' > "$MEGAI_HOME/lib/ensure_dev.sh"
state_init() { :; }
is_project_initialized() { return 1; }
mark_project_active() { :; }
ensure_agent_memory() { echo memory >> "$CALLS"; }
ensure_codedb_index() { echo codedb >> "$CALLS"; }
ensure_zvec_index() { echo zvec >> "$CALLS"; }
ensure_graphify_bg() { echo graphify >> "$CALLS"; }
ensure_repowise_bg() { echo repowise >> "$CALLS"; }
check_caveman() { :; }
check_rtk() { :; }
: > "$CALLS"
MEGAI_SPECIALIST_INDEXES=0 prepare_stack >/dev/null
[ "$(< "$CALLS")" = $'memory\ncodedb\nzvec' ]
: > "$CALLS"
MEGAI_SPECIALIST_INDEXES=1 prepare_stack >/dev/null
grep -Fxq graphify "$CALLS"
grep -Fxq repowise "$CALLS"
is_project_initialized() { return 0; }
MEGAI_SPECIALIST_INDEXES=0 prepare_stack | grep -q 'core readiness checked; specialist indexes on demand'
MEGAI_SPECIALIST_INDEXES=1 prepare_stack | grep -q 'core readiness checked; specialist indexes requested'

# Default Caveman installation must not call either npm or the installer.
printf '#!/bin/sh\necho caveman >> "$CALLS"\n' > "$TMP/bin/caveman"
printf '#!/bin/sh\necho npm >> "$CALLS"\nprintf "{}\\n"\n' > "$TMP/bin/npm"
chmod +x "$TMP/bin/caveman" "$TMP/bin/npm"
: > "$CALLS"
MEGAI_CAVEMAN=0 bash "$MEGAI_HOME/lib/install_caveman.sh" >/dev/null
[ ! -s "$CALLS" ]
MEGAI_CAVEMAN=1 bash "$MEGAI_HOME/lib/install_caveman.sh" >/dev/null
grep -Fxq caveman "$CALLS"

# Only owned links are removed; foreign replacements survive reinstall/removal.
rm "$MEGAI_HOME/bin/megai-memory"
printf '#!/bin/sh\necho user-owned\n' > "$MEGAI_HOME/bin/megai-memory"
chmod +x "$MEGAI_HOME/bin/megai-memory"
bash "$MEGAI_HOME/lib/wire_pi.sh" >/dev/null
grep -q user-owned "$MEGAI_HOME/bin/megai-memory"
cp "$PI_CODING_AGENT_DIR/settings.json" "$TMP/settings-before-unwire"
bash "$MEGAI_HOME/lib/wire_pi.sh" --remove >/dev/null
grep -q user-owned "$MEGAI_HOME/bin/megai-memory"
[ ! -L "$MEGAI_HOME/bin/megai-codedb" ]
cmp "$PI_CODING_AGENT_DIR/settings.json" "$TMP/settings-before-unwire"
# Match Pi's supported legacy object migration without losing user options.
printf '{"skills":{"customDirectories":["legacy-skills"],"enableSkillCommands":false},"defaultModel":"keep"}\n' > "$PI_CODING_AGENT_DIR/settings.json"
bash "$MEGAI_HOME/lib/wire_pi.sh" >/dev/null
jq -e '.skills[0] == "legacy-skills" and .enableSkillCommands == false and .defaultModel == "keep"' "$PI_CODING_AGENT_DIR/settings.json" >/dev/null
printf '{"skills":{"customDirectories":[],"enableSkillCommands":false},"enableSkillCommands":true}\n' > "$PI_CODING_AGENT_DIR/settings.json"
bash "$MEGAI_HOME/lib/wire_pi.sh" >/dev/null
jq -e '.enableSkillCommands == true and .skills == ["!caveman*","!cavecrew","!smart-development-orchestrator"]' "$PI_CODING_AGENT_DIR/settings.json" >/dev/null

# Invalid settings fail without overwriting the original document.
printf '{invalid json\n' > "$PI_CODING_AGENT_DIR/settings.json"
cp "$PI_CODING_AGENT_DIR/settings.json" "$TMP/invalid-before"
if bash "$MEGAI_HOME/lib/wire_pi.sh" > /dev/null 2>&1; then
  echo 'invalid settings unexpectedly accepted' >&2; exit 1
fi
cmp "$PI_CODING_AGENT_DIR/settings.json" "$TMP/invalid-before"
echo 'Pi runtime: CLI wiring/grammar, bounded memory HTTP, startup opt-in, cache and preservation PASS'

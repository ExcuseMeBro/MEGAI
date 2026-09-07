#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

export HOME="$TMP/home"
export MEGAI_HOME="$TMP/megai"
export PI_CODING_AGENT_DIR="$HOME/.pi/agent"
mkdir -p "$MEGAI_HOME" "$PI_CODING_AGENT_DIR" "$TMP/bin"
cp -R "$ROOT/lib" "$ROOT/pi-skill" "$ROOT/task-flow" "$ROOT/skills" "$MEGAI_HOME/"
printf '%s\n' '{"tools":{},"agents":{},"projects":{}}' >"$MEGAI_HOME/state.json"
printf '%s\n' '{"mcpServers":{}}' >"$PI_CODING_AGENT_DIR/mcp.json"
printf '#!/usr/bin/env bash\nexit 0\n' >"$TMP/bin/pi"
chmod +x "$TMP/bin/pi"
export PATH="$TMP/bin:$PATH"

bash "$MEGAI_HOME/lib/wire_pi.sh" >/dev/null 2>&1
bash "$MEGAI_HOME/lib/wire_pi.sh" >/dev/null 2>&1
skill="$PI_CODING_AGENT_DIR/skills/megai-task-flow/SKILL.md"
[ -f "$skill" ]
grep -q '^name: megai-task-flow$' "$skill"
grep -q 'plane:project-uuid/workitem-uuid' "$skill"
grep -q 'Never create a second work item while a linked identity pair exists' "$skill"
grep -q 'Boundary-only Plane sync' "$skill"
grep -q 'Do not mirror individual ADLC stages to Plane' "$skill"
grep -q 'external_source=asana-migration-v1' "$skill"
grep -q 'Routine stage changes and milestone comments are forbidden' "$skill"
grep -q '| Active from spec through ship | `inprogress.md` | started: `In Progress` | start boundary only |' "$skill"
grep -Fq '| Verified; awaiting user review | `inprogress.md` (unchecked, 🔍 In Review) | started: `In Review` | handoff boundary |' "$skill"
grep -Fq '| User marks Done; reconcile | `done.md` | completed state | user only |' "$skill"
grep -Fq 'Do not invent or synchronize a completion boolean' "$skill"
grep -Fq 'A task already active in this session needs no repeated start mutation' "$skill"
grep -Fq 'Delegated children inherit' "$skill"
grep -Fq 'never create a project implicitly' "$skill"
! grep -Fq 'Bounded fast-path changes do not enter this protocol' "$skill"
grep -q 'Put it in started `In Progress` in one mutation' "$skill"
! grep -q 'when the API permits' "$skill"
! grep -q 'before final completion' "$skill"
grep -q 'megai finish --verified --target dev' "$skill"
[ -f "$PI_CODING_AGENT_DIR/skills/agent-worktree-lifecycle/SKILL.md" ]

# Reinstall must replace an older managed policy block instead of leaving stale rules.
mkdir -p "$HOME/.claude"
cat >"$HOME/.claude/CLAUDE.md" <<'MD'
before
<!-- megai:task-flow:begin -->
old synchronous policy one
<!-- megai:task-flow:end -->
middle
<!-- megai:task-flow:begin -->
old synchronous policy two
<!-- megai:task-flow:end -->
after
MD
printf '%s\n' '{}' >"$HOME/.claude/settings.json"
bash "$MEGAI_HOME/lib/install_taskflow.sh" >/dev/null 2>&1
bash "$MEGAI_HOME/lib/install_taskflow.sh" >/dev/null 2>&1
grep -q 'Risk-scaled Plane sync' "$HOME/.claude/CLAUDE.md"
grep -q 'Default fast path' "$HOME/.claude/CLAUDE.md"
grep -q 'implement → self-review → focused test → ship' "$HOME/.claude/CLAUDE.md"
grep -q 'There is no fallback or routine dual-sync to another tracker' "$HOME/.claude/CLAUDE.md"
grep -q 'Parallel implementation invariant' "$HOME/.claude/CLAUDE.md"
grep -q 'visible managed worktree workspace' "$HOME/.claude/CLAUDE.md"
grep -q 'launched with that `workspaceId`' "$HOME/.claude/CLAUDE.md"
grep -q 'megai promote --approved' "$HOME/.claude/CLAUDE.md"
grep -q 'Argent is explicit-only' "$HOME/.claude/CLAUDE.md"
! grep -q 'Every task runs full ADLC' "$HOME/.claude/CLAUDE.md"
! grep -q 'old synchronous policy' "$HOME/.claude/CLAUDE.md"
[ "$(grep -c 'megai:task-flow:begin' "$HOME/.claude/CLAUDE.md")" = "1" ]
grep -q 'Do not re-read unchanged board files between ADLC stages' "$HOME/.claude/skills/task-flow/SKILL.md"
grep -q 'ADLC labels are bookkeeping' "$HOME/.claude/skills/task-flow/SKILL.md"
grep -q 'Never invoke Argent unless the current user message explicitly contains `/argent`' "$HOME/.claude/hooks/taskflow-prompt.sh"
[ -f "$HOME/.claude/commands/argent.md" ]
grep -q '^managed-by: megai$' "$HOME/.claude/commands/argent.md"
grep -q 'explicitly invoked `/argent`' "$HOME/.claude/commands/argent.md"

bash "$MEGAI_HOME/lib/wire_pi.sh" --remove >/dev/null 2>&1
[ ! -e "$PI_CODING_AGENT_DIR/skills/megai-task-flow" ]
[ ! -e "$PI_CODING_AGENT_DIR/skills/agent-worktree-lifecycle" ]

# Pi policy replaces only its owned heading and preserves the next heading verbatim.
cat >"$PI_CODING_AGENT_DIR/AGENTS.md" <<'MD'
intro
## MEGAI task flow
legacy policy
## Paseo-visible delegation
user-owned delegation policy
MD
bash "$MEGAI_HOME/lib/wire_pi.sh" >/dev/null 2>&1
 grep -q 'Plane start boundary' "$PI_CODING_AGENT_DIR/AGENTS.md"
grep -Fxq '## Paseo-visible delegation' "$PI_CODING_AGENT_DIR/AGENTS.md"
grep -Fxq 'user-owned delegation policy' "$PI_CODING_AGENT_DIR/AGENTS.md"

# Codex policy replaces the exact legacy marker block and honors CODEX_HOME.
export CODEX_HOME="$TMP/custom-codex"
mkdir -p "$CODEX_HOME"
cat >"$CODEX_HOME/AGENTS.md" <<'MD'
user preface
<!-- asana-workflow:begin -->
legacy Asana instructions
<!-- asana-workflow:end -->
user suffix
MD
bash "$MEGAI_HOME/lib/wire_codex.sh" >/dev/null 2>&1
grep -q '<!-- plane-workflow:begin -->' "$CODEX_HOME/AGENTS.md"
! grep -q 'asana-workflow\|legacy Asana' "$CODEX_HOME/AGENTS.md"
grep -Fxq 'user preface' "$CODEX_HOME/AGENTS.md"
grep -Fxq 'user suffix' "$CODEX_HOME/AGENTS.md"

echo "Pi/Codex task-flow wiring: ok"

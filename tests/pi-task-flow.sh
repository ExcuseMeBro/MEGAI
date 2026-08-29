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
grep -q '<!-- asana:121234567890 -->' "$skill"
grep -q 'Never create a second task while a linked GID exists' "$skill"
grep -q 'Boundary-only Asana sync' "$skill"
grep -q 'Do not mirror individual ADLC stages to Asana' "$skill"
grep -q 'Routine stage changes and milestone comments are forbidden' "$skill"
grep -q '| Active from spec through ship | `inprogress.md` | `In Progress` | `false` |' "$skill"
grep -q '| Verified and finished | `done.md` | `Done` | `true` |' "$skill"
! grep -q '| Review or ship .* `In Review`' "$skill"
grep -q 'Put it in `In Progress` with `completed=false` in one mutation' "$skill"
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
grep -q 'Risk-scaled Asana sync' "$HOME/.claude/CLAUDE.md"
grep -q 'Default fast path' "$HOME/.claude/CLAUDE.md"
grep -q 'implement → self-review → focused test → ship' "$HOME/.claude/CLAUDE.md"
grep -q 'Never discover or sync Plane, Jira' "$HOME/.claude/CLAUDE.md"
grep -q 'Parallel implementation invariant' "$HOME/.claude/CLAUDE.md"
grep -q 'visible managed worktree workspace' "$HOME/.claude/CLAUDE.md"
grep -q 'launched with that `workspaceId`' "$HOME/.claude/CLAUDE.md"
! grep -q 'Every task runs full ADLC' "$HOME/.claude/CLAUDE.md"
! grep -q 'old synchronous policy' "$HOME/.claude/CLAUDE.md"
[ "$(grep -c 'megai:task-flow:begin' "$HOME/.claude/CLAUDE.md")" = "1" ]
grep -q 'Do not re-read unchanged board files between ADLC stages' "$HOME/.claude/skills/task-flow/SKILL.md"
grep -q 'ADLC labels are bookkeeping' "$HOME/.claude/skills/task-flow/SKILL.md"
grep -q "Execute only the user's current task" "$HOME/.claude/hooks/taskflow-prompt.sh"
grep -q 'Do not launch separate planner' "$HOME/.claude/hooks/taskflow-prompt.sh"

bash "$MEGAI_HOME/lib/wire_pi.sh" --remove >/dev/null 2>&1
[ ! -e "$PI_CODING_AGENT_DIR/skills/megai-task-flow" ]
[ ! -e "$PI_CODING_AGENT_DIR/skills/agent-worktree-lifecycle" ]

echo "Pi task-flow wiring: ok"

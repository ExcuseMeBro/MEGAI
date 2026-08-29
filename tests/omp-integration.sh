#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

export HOME="$TMP/home"
export MEGAI_HOME="$TMP/megai"
mkdir -p "$HOME/.omp/agent" "$MEGAI_HOME" "$TMP/bin" "$TMP/project/.repowise" "$TMP/project/graphify-out"
cp -R "$ROOT/bin" "$ROOT/lib" "$ROOT/pi-skill" "$ROOT/omp-skill" "$ROOT/omp-agents" "$ROOT/omp-config" "$ROOT/task-flow" "$ROOT/skills" "$MEGAI_HOME/"

cat >"$MEGAI_HOME/state.json" <<JSON
{
  "tools": {
    "agent-memory": {"bin": "$TMP/bin/agentmemory"},
    "codedb": {"bin": "$TMP/bin/codedb"}
  },
  "ports": {"agent-memory": 3111},
  "agents": {},
  "projects": {
    "$TMP/project": {
      "path": "$TMP/project",
      "initialized_at": "2026-08-25T00:00:00Z",
      "indexed_at": "2026-08-25T00:00:00Z"
    }
  }
}
JSON

cat >"$HOME/.omp/agent/mcp.json" <<'JSON'
{
  "$schema": "https://example.test/existing-schema.json",
  "mcpServers": {
    "keep": {"command": "keep"},
    "megai-dembrandt": {"command": "stale"},
    "megai-argent": {"command": "stale"},
    "megai-repowise": {"command": "stale"}
  },
  "disabledServers": ["disabled-by-user"]
}
JSON
cat >"$HOME/.omp/agent/RULES.md" <<'MD'
user-owned OMP rule mentioning <!-- megai:paseo-placement:begin --> inline
MD

for command in agentmemory codedb graphify repowise caveman; do
  printf '#!/usr/bin/env bash\nexit 0\n' >"$TMP/bin/$command"
  chmod +x "$TMP/bin/$command"
done
cat >"$TMP/bin/rtk" <<'SH'
#!/usr/bin/env bash
[ "${1:-}" = "--version" ] && echo "rtk test"
exit 0
SH
cat >"$TMP/bin/omp" <<SH
if [ "\${1:-}" = models ]; then
  case "\${2:-}" in
    minimax-code)
      if [ "\${MOCK_MINIMAX_AUTH:-0}" = 1 ]; then
        printf '%s\n' '{"models":[{"id":"MiniMax-M3"}]}'
      else
        printf '%s\n' '{"models":[]}'
      fi
      ;;
    openai-codex)
      if [ "\${MOCK_OPENAI_AUTH:-1}" = 1 ]; then
        printf '%s\n' '{"models":[{"id":"gpt-5.3-codex-spark"},{"id":"gpt-5.4-mini"},{"id":"gpt-5.4"},{"id":"gpt-5.5"},{"id":"gpt-5.6-luna"},{"id":"gpt-5.6-terra"},{"id":"gpt-5.6-sol"}]}'
      else
        printf '%s\n' '{"models":[]}'
      fi
      ;;
    *) printf '%s\n' '{"models":[]}' ;;
  esac
  exit 0
fi
printf '%s\n' "\$@" >"$TMP/omp.args"
SH
chmod +x "$TMP/bin/rtk" "$TMP/bin/omp" "$MEGAI_HOME/bin/megai"
export PATH="$TMP/bin:$PATH"
cat >"$TMP/expected-agents" <<'AGENTS'
smart-router|minimax-code/MiniMax-M2.1-lightning|low
luna-scout|openai-codex/gpt-5.6-luna|low
terra-scout|openai-codex/gpt-5.6-terra|medium
minimax-worker|minimax-code/MiniMax-M3|medium
minimax-fast-worker|minimax-code/MiniMax-M2.7-highspeed|medium
minimax-quality-worker|minimax-code/MiniMax-M2.7|high
minimax-test-worker|minimax-code/MiniMax-M2.5-highspeed|low
minimax-ops-worker|minimax-code/MiniMax-M2.5-lightning|low
minimax-migration-worker|minimax-code/MiniMax-M2.5|medium
minimax-stable-worker|minimax-code/MiniMax-M2.1|medium
minimax-legacy-worker|minimax-code/MiniMax-M2|low
minimax-commit-writer|minimax-code/MiniMax-M3|minimal
sol-gate|openai-codex/gpt-5.6-sol|high
gpt-debugger|openai-codex/gpt-5.5|high
gpt-long-context|openai-codex/gpt-5.4|high
gpt-fast-reviewer|openai-codex/gpt-5.4-mini|medium
gpt-trusted-fast|openai-codex/gpt-5.3-codex-spark|low
AGENTS

# Public wiring command must be idempotent and preserve unrelated OMP config.
bash "$MEGAI_HOME/bin/megai" wire omp >/dev/null
bash "$MEGAI_HOME/bin/megai" wire omp >/dev/null

jq -e '
  .["$schema"] == "https://example.test/existing-schema.json"
  and .mcpServers.keep.command == "keep"
  and .mcpServers.agentmemory.command == $agentmemory
  and .mcpServers.agentmemory.args == ["mcp"]
  and .mcpServers.agentmemory.env.AGENTMEMORY_URL == "http://127.0.0.1:3111"
  and .mcpServers.codedb.command == $codedb
  and .mcpServers.codedb.args == ["mcp"]
  and (.mcpServers["megai-dembrandt"] | not)
  and (.mcpServers["megai-argent"] | not)
  and (.mcpServers["megai-repowise"] | not)
  and .disabledServers == ["disabled-by-user"]
' --arg agentmemory "$TMP/bin/agentmemory" --arg codedb "$TMP/bin/codedb" "$HOME/.omp/agent/mcp.json" >/dev/null

[ -f "$HOME/.omp/agent/skills/megai/SKILL.md" ]
[ -f "$HOME/.omp/agent/skills/megai-task-flow/SKILL.md" ]
[ -f "$HOME/.omp/agent/skills/agent-worktree-lifecycle/SKILL.md" ]
[ -f "$HOME/.omp/agent/skills/smart-development-orchestrator/SKILL.md" ]
grep -q '^# Smart Development Orchestrator$' "$HOME/.omp/agent/skills/smart-development-orchestrator/SKILL.md"
grep -q 'archive_workspace' "$HOME/.omp/agent/skills/smart-development-orchestrator/SKILL.md"
grep -q '^# MEGAI for Oh My Pi$' "$HOME/.omp/agent/skills/megai/SKILL.md"
grep -q 'minimax-commit-writer' "$HOME/.omp/agent/RULES.md"
grep -q 'resolved-model badge' "$HOME/.omp/agent/RULES.md"
grep -q 'In an agent-scoped Paseo session, read-only discovery' "$HOME/.omp/agent/skills/megai/SKILL.md"
grep -q 'Every writing worker MUST receive a visible Paseo-managed worktree workspace' "$HOME/.omp/agent/skills/megai/SKILL.md"
grep -q 'OMP native `task` isolation is reserved for execution outside Paseo' "$HOME/.omp/agent/skills/megai/SKILL.md"
grep -q 'parent is the sole integration owner' "$HOME/.omp/agent/skills/megai/SKILL.md"
grep -q 'task.isolation.merge: branch' "$HOME/.omp/agent/skills/agent-worktree-lifecycle/SKILL.md"
while IFS='|' read -r name model effort; do
  file="$HOME/.omp/agent/agents/$name.md"
  [ -f "$file" ]
  grep -Fqx "model: $model" "$file"
  grep -Fqx "thinking: $effort" "$file"
  grep -q '^managed-by: megai$' "$file"
done <"$TMP/expected-agents"
grep -q '^spawns: luna-scout, terra-scout$' "$HOME/.omp/agent/agents/smart-router.md"
grep -q '^blocking: true$' "$HOME/.omp/agent/agents/smart-router.md"
grep -q 'MUST delegate non-trivial file location' "$HOME/.omp/agent/RULES.md"
jq -e '.agents.omp.wired == true and .agents.omp.config == $config' \
  --arg config "$HOME/.omp/agent" "$MEGAI_HOME/state.json" >/dev/null
grep -q 'user-owned OMP rule' "$HOME/.omp/agent/RULES.md"
grep -q 'orchestrator stays in the primary `dev` workspace' "$HOME/.omp/agent/RULES.md"
grep -q 'In an agent-scoped Paseo session, read-only discovery' "$HOME/.omp/agent/RULES.md"
grep -q 'In a top-level context, require exactly one workspace whose `cwd` equals the current `cwd`' "$HOME/.omp/agent/RULES.md"
grep -q 'Every worker with write authority MUST first use `create_workspace`' "$HOME/.omp/agent/RULES.md"
grep -q 'isolation: "worktree"' "$HOME/.omp/agent/RULES.md"
grep -q 'mode: "branch-off"' "$HOME/.omp/agent/RULES.md"
grep -q 'baseBranch: "dev"' "$HOME/.omp/agent/RULES.md"
grep -q 'unique `task/<slug>` branch' "$HOME/.omp/agent/RULES.md"
grep -q 'then use `create_agent` with the returned `workspaceId`' "$HOME/.omp/agent/RULES.md"
grep -q 'Never create concurrent writers in the parent workspace' "$HOME/.omp/agent/RULES.md"
grep -q 'visible writer workspaces take precedence' "$HOME/.omp/agent/RULES.md"
grep -q 'After verified merge, dev push, PR/MR creation, and worktree cleanup' "$HOME/.omp/agent/RULES.md"
[ "$(grep -Fxc '<!-- megai:paseo-placement:begin -->' "$HOME/.omp/agent/RULES.md")" = "1" ]

mkdir -p "$HOME/.omp/profiles/work/agent"
printf '%s\n' 'named-profile user rule' >"$HOME/.omp/profiles/work/agent/RULES.md"
# Public launcher must prepare the stack, preserve arguments, and exec OMP.
export MOCK_MINIMAX_AUTH=1
(
  cd "$TMP/project"
  bash "$MEGAI_HOME/bin/megai" omp --profile work >/dev/null
)
printf '%s\n' '--config' "$MEGAI_HOME/omp-config/high-speed.yml" '--config' "$MEGAI_HOME/omp-config/balanced-minimax.yml" '--profile' 'work' >"$TMP/expected.args"
cmp "$TMP/expected.args" "$TMP/omp.args"
(
  cd "$TMP/project"
  bash "$MEGAI_HOME/bin/megai" omp --config "$MEGAI_HOME/omp-config/high-speed.yml" --profile work >/dev/null
)
printf '%s\n' '--config' "$MEGAI_HOME/omp-config/balanced-minimax.yml" '--config' "$MEGAI_HOME/omp-config/high-speed.yml" '--profile' 'work' >"$TMP/expected.args"
cmp "$TMP/expected.args" "$TMP/omp.args"
printf 'task:\n  maxConcurrency: 3\n' >"$TMP/custom-omp.yml"
(
  cd "$TMP/project"
  bash "$MEGAI_HOME/bin/megai" omp --profile work --config "$TMP/custom-omp.yml" >/dev/null
)
printf '%s\n' '--config' "$MEGAI_HOME/omp-config/high-speed.yml" '--config' "$MEGAI_HOME/omp-config/balanced-minimax.yml" '--profile' 'work' '--config' "$TMP/custom-omp.yml" >"$TMP/expected.args"
cmp "$TMP/expected.args" "$TMP/omp.args"
(
  cd "$TMP/project"
  MOCK_MINIMAX_AUTH=0 bash "$MEGAI_HOME/bin/megai" omp --profile work >/dev/null
)
printf '%s\n' '--config' "$MEGAI_HOME/omp-config/high-speed.yml" '--profile' 'work' >"$TMP/expected.args"
cmp "$TMP/expected.args" "$TMP/omp.args"
(
  cd "$TMP/project"
  MOCK_MINIMAX_AUTH=1 MOCK_OPENAI_AUTH=0 bash "$MEGAI_HOME/bin/megai" omp --profile work >/dev/null
)
printf '%s\n' '--config' "$MEGAI_HOME/omp-config/high-speed.yml" '--profile' 'work' >"$TMP/expected.args"
cmp "$TMP/expected.args" "$TMP/omp.args"
[ -f "$HOME/.omp/profiles/work/agent/mcp.json" ]
[ -f "$HOME/.omp/profiles/work/agent/skills/megai/SKILL.md" ]
[ -f "$HOME/.omp/profiles/work/agent/skills/agent-worktree-lifecycle/SKILL.md" ]
grep -q 'In an agent-scoped Paseo session, read-only discovery' "$HOME/.omp/profiles/work/agent/skills/megai/SKILL.md"
grep -q 'Every writing worker MUST receive a visible Paseo-managed worktree workspace' "$HOME/.omp/profiles/work/agent/skills/megai/SKILL.md"
while IFS='|' read -r name model effort; do
  [ -f "$HOME/.omp/profiles/work/agent/agents/$name.md" ]
done <"$TMP/expected-agents"
grep -q '^spawns: luna-scout, terra-scout$' "$HOME/.omp/profiles/work/agent/agents/smart-router.md"
grep -q 'task.isolation.merge: branch' "$HOME/.omp/profiles/work/agent/skills/agent-worktree-lifecycle/SKILL.md"
grep -q 'named-profile user rule' "$HOME/.omp/profiles/work/agent/RULES.md"
grep -q 'create_agent` without `workspaceId`' "$HOME/.omp/profiles/work/agent/RULES.md"
grep -q 'Every worker with write authority MUST first use `create_workspace`' "$HOME/.omp/profiles/work/agent/RULES.md"
grep -q 'then use `create_agent` with the returned `workspaceId`' "$HOME/.omp/profiles/work/agent/RULES.md"
jq -e '.agents.omp.wired == true and .agents.omp.config == $config' \
  --arg config "$HOME/.omp/profiles/work/agent" "$MEGAI_HOME/state.json" >/dev/null

OMP_PROFILE=env-work bash "$MEGAI_HOME/bin/megai" wire omp >/dev/null
PI_PROFILE=pi-work bash "$MEGAI_HOME/bin/megai" wire omp >/dev/null
[ -f "$HOME/.omp/profiles/env-work/agent/mcp.json" ]
[ -f "$HOME/.omp/profiles/pi-work/agent/mcp.json" ]

# Removal must delete only MEGAI-owned OMP entries and skills.
bash "$MEGAI_HOME/lib/wire_omp.sh" --remove >/dev/null
jq -e '
  .mcpServers.keep.command == "keep"
  and (.mcpServers.agentmemory | not)
  and (.mcpServers.codedb | not)
  and .disabledServers == ["disabled-by-user"]
' "$HOME/.omp/agent/mcp.json" >/dev/null
[ ! -e "$HOME/.omp/agent/skills/megai" ]
[ ! -e "$HOME/.omp/agent/skills/megai-task-flow" ]
[ ! -e "$HOME/.omp/agent/skills/agent-worktree-lifecycle" ]
while IFS='|' read -r name model effort; do
  [ ! -e "$HOME/.omp/agent/agents/$name.md" ]
done <"$TMP/expected-agents"
grep -q 'user-owned OMP rule' "$HOME/.omp/agent/RULES.md"
! grep -Fxq '<!-- megai:paseo-placement:begin -->' "$HOME/.omp/agent/RULES.md"

OMP_PROFILE=work bash "$MEGAI_HOME/lib/wire_omp.sh" --remove >/dev/null
jq -e '(.mcpServers.agentmemory | not) and (.mcpServers.codedb | not)' \
  "$HOME/.omp/profiles/work/agent/mcp.json" >/dev/null
[ ! -e "$HOME/.omp/profiles/work/agent/skills/megai" ]
[ ! -e "$HOME/.omp/profiles/work/agent/skills/megai-task-flow" ]
[ ! -e "$HOME/.omp/profiles/work/agent/skills/agent-worktree-lifecycle" ]
while IFS='|' read -r name model effort; do
  [ ! -e "$HOME/.omp/profiles/work/agent/agents/$name.md" ]
done <"$TMP/expected-agents"
grep -q 'named-profile user rule' "$HOME/.omp/profiles/work/agent/RULES.md"
! grep -Fxq '<!-- megai:paseo-placement:begin -->' "$HOME/.omp/profiles/work/agent/RULES.md"

# User-owned agent collisions survive install and removal; independent managed
# agents still install and clean up.
COLLISION_HOME="$TMP/collision-home"
HOME="$COLLISION_HOME" bash "$MEGAI_HOME/lib/wire_omp.sh" >/dev/null
grep -q '^managed-by: megai$' "$COLLISION_HOME/.omp/agent/agents/luna-scout.md"
grep -q '^managed-by: megai$' "$COLLISION_HOME/.omp/agent/agents/terra-scout.md"
printf '%s\n' 'user-owned smart router' >"$COLLISION_HOME/.omp/agent/agents/smart-router.md"
HOME="$COLLISION_HOME" bash "$MEGAI_HOME/lib/wire_omp.sh" >/dev/null
while IFS='|' read -r name model effort; do
  case "$name" in
    smart-router) grep -q '^user-owned smart router$' "$COLLISION_HOME/.omp/agent/agents/$name.md" ;;
    luna-scout|terra-scout) [ ! -e "$COLLISION_HOME/.omp/agent/agents/$name.md" ] ;;
    *) grep -q '^managed-by: megai$' "$COLLISION_HOME/.omp/agent/agents/$name.md" ;;
  esac
done <"$TMP/expected-agents"
HOME="$COLLISION_HOME" bash "$MEGAI_HOME/lib/wire_omp.sh" --remove >/dev/null
while IFS='|' read -r name model effort; do
  if [ "$name" = smart-router ]; then
    grep -q '^user-owned smart router$' "$COLLISION_HOME/.omp/agent/agents/$name.md"
  else
    [ ! -e "$COLLISION_HOME/.omp/agent/agents/$name.md" ]
  fi
done <"$TMP/expected-agents"

# Global uninstall enumerates named OMP profiles before removing MEGAI_HOME.
UNINSTALL_HOME="$TMP/uninstall-home"
UNINSTALL_MEGAI="$TMP/uninstall-megai"
cp -R "$MEGAI_HOME" "$UNINSTALL_MEGAI"
HOME="$UNINSTALL_HOME" MEGAI_HOME="$UNINSTALL_MEGAI" bash "$UNINSTALL_MEGAI/lib/wire_omp.sh" >/dev/null
HOME="$UNINSTALL_HOME" MEGAI_HOME="$UNINSTALL_MEGAI" OMP_PROFILE=work bash "$UNINSTALL_MEGAI/lib/wire_omp.sh" >/dev/null
printf 'y\n' | HOME="$UNINSTALL_HOME" MEGAI_HOME="$UNINSTALL_MEGAI" bash "$UNINSTALL_MEGAI/bin/megai" uninstall >/dev/null
while IFS='|' read -r name model effort; do
  [ ! -e "$UNINSTALL_HOME/.omp/agent/agents/$name.md" ]
  [ ! -e "$UNINSTALL_HOME/.omp/profiles/work/agent/agents/$name.md" ]
done <"$TMP/expected-agents"
[ ! -e "$UNINSTALL_MEGAI" ]

# Malformed managed markers must fail closed without changing user rules.
MALFORMED_HOME="$TMP/malformed-home"
mkdir -p "$MALFORMED_HOME/.omp/agent"
cat >"$MALFORMED_HOME/.omp/agent/RULES.md" <<'MD'
before malformed block
<!-- megai:paseo-placement:begin -->
trailing user rule must survive
MD
cp "$MALFORMED_HOME/.omp/agent/RULES.md" "$TMP/malformed-rules.before"
if HOME="$MALFORMED_HOME" bash "$MEGAI_HOME/lib/wire_omp.sh" >/dev/null 2>&1; then
  echo "malformed OMP RULES.md was accepted" >&2
  exit 1
fi
cmp "$TMP/malformed-rules.before" "$MALFORMED_HOME/.omp/agent/RULES.md"

# Removal on a machine without OMP state must not create OMP artifacts.
EMPTY_HOME="$TMP/empty-home"
HOME="$EMPTY_HOME" bash "$MEGAI_HOME/lib/wire_omp.sh" --remove >/dev/null
[ ! -e "$EMPTY_HOME/.omp" ]

echo "OMP integration: ok"

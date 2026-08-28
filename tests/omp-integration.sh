#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

export HOME="$TMP/home"
export MEGAI_HOME="$TMP/megai"
mkdir -p "$HOME/.omp/agent" "$MEGAI_HOME" "$TMP/bin" "$TMP/project/.repowise" "$TMP/project/graphify-out"
cp -R "$ROOT/bin" "$ROOT/lib" "$ROOT/pi-skill" "$ROOT/omp-skill" "$ROOT/omp-agents" "$ROOT/task-flow" "$ROOT/skills" "$MEGAI_HOME/"

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
#!/usr/bin/env bash
printf '%s\n' "\$@" >"$TMP/omp.args"
SH
chmod +x "$TMP/bin/rtk" "$TMP/bin/omp" "$MEGAI_HOME/bin/megai"
export PATH="$TMP/bin:$PATH"

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
grep -q 'subagent, reviewer, parallel worker, or new tab' "$HOME/.omp/agent/skills/megai/SKILL.md"
grep -q 'do not create a workspace first' "$HOME/.omp/agent/skills/megai/SKILL.md"
grep -q 'one task batch with `isolated: true`' "$HOME/.omp/agent/skills/megai/SKILL.md"
grep -q 'parent is the sole integration owner' "$HOME/.omp/agent/skills/megai/SKILL.md"
grep -q 'task.isolation.merge: branch' "$HOME/.omp/agent/skills/agent-worktree-lifecycle/SKILL.md"
[ -f "$HOME/.omp/agent/agents/smart-router.md" ]
[ -f "$HOME/.omp/agent/agents/terra-scout.md" ]
grep -q '^model: "@luna"$' "$HOME/.omp/agent/agents/smart-router.md"
grep -q '^managed-by: megai$' "$HOME/.omp/agent/agents/smart-router.md"
grep -q '^managed-by: megai$' "$HOME/.omp/agent/agents/terra-scout.md"
grep -q '^spawns: terra-scout$' "$HOME/.omp/agent/agents/smart-router.md"
grep -q '^blocking: true$' "$HOME/.omp/agent/agents/smart-router.md"
grep -q '^model: "@terra"$' "$HOME/.omp/agent/agents/terra-scout.md"
grep -q 'Route non-trivial file location' "$HOME/.omp/agent/RULES.md"
jq -e '.agents.omp.wired == true and .agents.omp.config == $config' \
  --arg config "$HOME/.omp/agent" "$MEGAI_HOME/state.json" >/dev/null
grep -q 'user-owned OMP rule' "$HOME/.omp/agent/RULES.md"
grep -q 'New agent or tab means the current Paseo workspace' "$HOME/.omp/agent/RULES.md"
grep -q 'call `create_agent` without `workspaceId`' "$HOME/.omp/agent/RULES.md"
grep -q 'exactly one workspace whose `cwd` equals the current `cwd`' "$HOME/.omp/agent/RULES.md"
grep -q 'pass that `workspaceId` explicitly to `create_agent`' "$HOME/.omp/agent/RULES.md"
grep -q 'Never call `create_workspace` unless the user explicitly requests' "$HOME/.omp/agent/RULES.md"
grep -q 'For zero or multiple matches, ask once' "$HOME/.omp/agent/RULES.md"
[ "$(grep -Fxc '<!-- megai:paseo-placement:begin -->' "$HOME/.omp/agent/RULES.md")" = "1" ]

mkdir -p "$HOME/.omp/profiles/work/agent"
printf '%s\n' 'named-profile user rule' >"$HOME/.omp/profiles/work/agent/RULES.md"
# Public launcher must prepare the stack, preserve arguments, and exec OMP.
(
  cd "$TMP/project"
  bash "$MEGAI_HOME/bin/megai" omp --profile work >/dev/null
)
printf '%s\n' '--profile' 'work' >"$TMP/expected.args"
cmp "$TMP/expected.args" "$TMP/omp.args"
[ -f "$HOME/.omp/profiles/work/agent/mcp.json" ]
[ -f "$HOME/.omp/profiles/work/agent/skills/megai/SKILL.md" ]
[ -f "$HOME/.omp/profiles/work/agent/skills/agent-worktree-lifecycle/SKILL.md" ]
grep -q 'subagent, reviewer, parallel worker, or new tab' "$HOME/.omp/profiles/work/agent/skills/megai/SKILL.md"
grep -q 'do not create a workspace first' "$HOME/.omp/profiles/work/agent/skills/megai/SKILL.md"
grep -q 'one task batch with `isolated: true`' "$HOME/.omp/profiles/work/agent/skills/megai/SKILL.md"
grep -q 'task.isolation.merge: branch' "$HOME/.omp/profiles/work/agent/skills/agent-worktree-lifecycle/SKILL.md"
[ -f "$HOME/.omp/profiles/work/agent/skills/smart-development-orchestrator/SKILL.md" ]
[ -f "$HOME/.omp/profiles/work/agent/agents/smart-router.md" ]
[ -f "$HOME/.omp/profiles/work/agent/agents/terra-scout.md" ]
grep -q '^spawns: terra-scout$' "$HOME/.omp/profiles/work/agent/agents/smart-router.md"
grep -q 'named-profile user rule' "$HOME/.omp/profiles/work/agent/RULES.md"
grep -q 'call `create_agent` without `workspaceId`' "$HOME/.omp/profiles/work/agent/RULES.md"
grep -q 'pass that `workspaceId` explicitly to `create_agent`' "$HOME/.omp/profiles/work/agent/RULES.md"
grep -q 'Never call `create_workspace` unless the user explicitly requests' "$HOME/.omp/profiles/work/agent/RULES.md"
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
[ ! -e "$HOME/.omp/agent/agents/smart-router.md" ]
[ ! -e "$HOME/.omp/agent/skills/smart-development-orchestrator" ]
[ ! -e "$HOME/.omp/agent/agents/terra-scout.md" ]
grep -q 'user-owned OMP rule' "$HOME/.omp/agent/RULES.md"
! grep -Fxq '<!-- megai:paseo-placement:begin -->' "$HOME/.omp/agent/RULES.md"

OMP_PROFILE=work bash "$MEGAI_HOME/lib/wire_omp.sh" --remove >/dev/null
jq -e '(.mcpServers.agentmemory | not) and (.mcpServers.codedb | not)' \
  "$HOME/.omp/profiles/work/agent/mcp.json" >/dev/null
[ ! -e "$HOME/.omp/profiles/work/agent/skills/megai" ]
[ ! -e "$HOME/.omp/profiles/work/agent/skills/megai-task-flow" ]
[ ! -e "$HOME/.omp/profiles/work/agent/skills/agent-worktree-lifecycle" ]
[ ! -e "$HOME/.omp/profiles/work/agent/agents/smart-router.md" ]
[ ! -e "$HOME/.omp/profiles/work/agent/skills/smart-development-orchestrator" ]
[ ! -e "$HOME/.omp/profiles/work/agent/agents/terra-scout.md" ]
grep -q 'named-profile user rule' "$HOME/.omp/profiles/work/agent/RULES.md"
! grep -Fxq '<!-- megai:paseo-placement:begin -->' "$HOME/.omp/profiles/work/agent/RULES.md"

# User-owned agent collisions survive install and removal; independent managed
# agents still install and clean up.
COLLISION_HOME="$TMP/collision-home"
mkdir -p "$COLLISION_HOME/.omp/agent/agents"
printf '%s\n' 'user-owned smart router' >"$COLLISION_HOME/.omp/agent/agents/smart-router.md"
HOME="$COLLISION_HOME" bash "$MEGAI_HOME/lib/wire_omp.sh" >/dev/null
grep -q '^user-owned smart router$' "$COLLISION_HOME/.omp/agent/agents/smart-router.md"
grep -q '^managed-by: megai$' "$COLLISION_HOME/.omp/agent/agents/terra-scout.md"
HOME="$COLLISION_HOME" bash "$MEGAI_HOME/lib/wire_omp.sh" --remove >/dev/null
grep -q '^user-owned smart router$' "$COLLISION_HOME/.omp/agent/agents/smart-router.md"
[ ! -e "$COLLISION_HOME/.omp/agent/agents/terra-scout.md" ]

# Global uninstall enumerates named OMP profiles before removing MEGAI_HOME.
UNINSTALL_HOME="$TMP/uninstall-home"
UNINSTALL_MEGAI="$TMP/uninstall-megai"
cp -R "$MEGAI_HOME" "$UNINSTALL_MEGAI"
HOME="$UNINSTALL_HOME" MEGAI_HOME="$UNINSTALL_MEGAI" bash "$UNINSTALL_MEGAI/lib/wire_omp.sh" >/dev/null
HOME="$UNINSTALL_HOME" MEGAI_HOME="$UNINSTALL_MEGAI" OMP_PROFILE=work bash "$UNINSTALL_MEGAI/lib/wire_omp.sh" >/dev/null
printf 'y\n' | HOME="$UNINSTALL_HOME" MEGAI_HOME="$UNINSTALL_MEGAI" bash "$UNINSTALL_MEGAI/bin/megai" uninstall >/dev/null
[ ! -e "$UNINSTALL_HOME/.omp/agent/agents/terra-scout.md" ]
[ ! -e "$UNINSTALL_HOME/.omp/profiles/work/agent/agents/terra-scout.md" ]
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

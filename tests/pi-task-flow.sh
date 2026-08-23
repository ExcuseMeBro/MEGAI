#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

export HOME="$TMP/home"
export MEGAI_HOME="$TMP/megai"
export PI_CODING_AGENT_DIR="$HOME/.pi/agent"
mkdir -p "$MEGAI_HOME" "$PI_CODING_AGENT_DIR" "$TMP/bin"
cp -R "$ROOT/lib" "$ROOT/pi-skill" "$ROOT/task-flow" "$MEGAI_HOME/"
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
grep -q '| Queued or paused | `todo.md` | `Todo` | `false` |' "$skill"
grep -q '| Spec through verify | `inprogress.md` | `In Progress` | `false` |' "$skill"
grep -q '| Review or ship | `inprogress.md` | `In Review` | `false` |' "$skill"
grep -q '| Verified and finished | `done.md` | `Done` | `true` |' "$skill"

bash "$MEGAI_HOME/lib/wire_pi.sh" --remove >/dev/null 2>&1
[ ! -e "$PI_CODING_AGENT_DIR/skills/megai-task-flow" ]

echo "Pi task-flow wiring: ok"

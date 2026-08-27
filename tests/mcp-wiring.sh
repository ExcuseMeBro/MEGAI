#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

export HOME="$TMP/home"
export MEGAI_HOME="$TMP/megai"
export PI_CODING_AGENT_DIR="$HOME/.pi/agent"
mkdir -p "$HOME/.codex" "$PI_CODING_AGENT_DIR" "$MEGAI_HOME/backups" "$TMP/bin"
cp -R "$ROOT/lib" "$ROOT/pi-skill" "$MEGAI_HOME/"
cat >"$MEGAI_HOME/state.json" <<JSON
{"tools":{"agent-memory":{"bin":"/bin/agentmemory"},"codedb":{"bin":"/bin/codedb"},"dembrandt":{"mcpBin":"$TMP/bin/dembrandt-mcp"},"argent":{"bin":"$TMP/bin/argent"},"repowise":{"bin":"$TMP/bin/repowise"}},"ports":{"agent-memory":3111},"agents":{},"projects":{}}
JSON
printf '#!/usr/bin/env bash\nexit 0\n' >"$TMP/bin/dembrandt-mcp"
printf '#!/usr/bin/env bash\nexit 0\n' >"$TMP/bin/argent"
printf '#!/usr/bin/env bash\nexit 0\n' >"$TMP/bin/repowise"
chmod +x "$TMP/bin/dembrandt-mcp" "$TMP/bin/argent" "$TMP/bin/repowise"
cat >"$HOME/.claude.json" <<'JSON'
{"mcpServers":{"keep":{"command":"keep"},"dembrandt":{"command":"user-dembrandt"},"argent":{"command":"user-argent"},"repowise":{"command":"user-repowise"}}}
JSON
printf 'keep = true\n\n[mcp_servers.dembrandt]\ncommand = "user-dembrandt"\n\n[mcp_servers.argent]\ncommand = "user-argent"\n\n[mcp_servers.repowise]\ncommand = "user-repowise"\n' >"$HOME/.codex/config.toml"
cat >"$PI_CODING_AGENT_DIR/mcp.json" <<'JSON'
{"mcpServers":{"keep":{"command":"keep"},"asana":{"url":"https://mcp.asana.com/v2/mcp","lifecycle":"keep-alive"}}}
JSON
printf '#!/usr/bin/env bash\nexit 0\n' >"$TMP/bin/pi"
chmod +x "$TMP/bin/pi"
export PATH="$TMP/bin:$PATH"

bash "$MEGAI_HOME/lib/wire_cc.sh" >/dev/null
bash "$MEGAI_HOME/lib/wire_codex.sh" >/dev/null
bash "$MEGAI_HOME/lib/wire_pi.sh" >/dev/null 2>&1

# Codex may append app-managed MCP tables immediately before MEGAI's closing
# marker. Rewiring must preserve those unknown tables while replacing only the
# MCP servers owned by MEGAI.
python3 - "$HOME/.codex/config.toml" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
text = text.replace(
    "# <<< megai-managed <<<",
    """[mcp_servers.external-app]
command = \"external-app\"

[mcp_servers.external-app.env]
KEEP = \"true\"
# <<< megai-managed <<<""",
)
path.write_text(text)
PY

# Codex can normalize MEGAI tables outside the marker while leaving the old
# marker block in place. Rewiring must remove both the normalized owned tables
# (including nested env tables) and the marker copy before writing one block.
python3 - "$HOME/.codex/config.toml" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
normalized = """[mcp_servers.agentmemory]
command = \"old-agentmemory\"

[mcp_servers.agentmemory.env]
AGENTMEMORY_URL = \"http://127.0.0.1:3999\"

[mcp_servers.codedb]
command = \"old-codedb\"

"""
path.write_text(normalized + text)
PY

# Rewiring must stay idempotent.
bash "$MEGAI_HOME/lib/wire_cc.sh" >/dev/null
bash "$MEGAI_HOME/lib/wire_codex.sh" >/dev/null
bash "$MEGAI_HOME/lib/wire_pi.sh" >/dev/null 2>&1

jq -e '
  .mcpServers.dembrandt.command == "user-dembrandt"
  and .mcpServers.argent.command == "user-argent"
  and .mcpServers.repowise.command == "user-repowise"
  and .mcpServers.agentmemory.env.AGENTMEMORY_URL == "http://127.0.0.1:3111"
  and .mcpServers.codedb.args == ["mcp"]
  and (.mcpServers["megai-dembrandt"] | not)
  and (.mcpServers["megai-argent"] | not)
  and (.mcpServers["megai-repowise"] | not)
' "$HOME/.claude.json" >/dev/null
[ "$(grep -c '^\[mcp_servers.dembrandt\]$' "$HOME/.codex/config.toml")" = "1" ]
[ "$(grep -c '^\[mcp_servers.repowise\]$' "$HOME/.codex/config.toml")" = "1" ]
[ "$(grep -c '^\[mcp_servers.argent\]$' "$HOME/.codex/config.toml")" = "1" ]
! grep -q '^\[mcp_servers.megai-dembrandt\]$' "$HOME/.codex/config.toml"
! grep -q '^\[mcp_servers.megai-argent\]$' "$HOME/.codex/config.toml"
! grep -q '^\[mcp_servers.megai-repowise\]$' "$HOME/.codex/config.toml"
[ "$(grep -c '^\[mcp_servers.agentmemory\]$' "$HOME/.codex/config.toml")" = "1" ]
[ "$(grep -c '^\[mcp_servers.agentmemory.env\]$' "$HOME/.codex/config.toml")" = "0" ]
[ "$(grep -c '^\[mcp_servers.codedb\]$' "$HOME/.codex/config.toml")" = "1" ]
grep -q 'AGENTMEMORY_URL = "http://127.0.0.1:3111"' "$HOME/.codex/config.toml"
[ "$(grep -c '^\[mcp_servers.external-app\]$' "$HOME/.codex/config.toml")" = "1" ]
[ "$(grep -c '^\[mcp_servers.external-app.env\]$' "$HOME/.codex/config.toml")" = "1" ]
grep -q '^KEEP = "true"$' "$HOME/.codex/config.toml"
python3 -c 'import sys, tomllib; tomllib.load(open(sys.argv[1], "rb"))' "$HOME/.codex/config.toml"
jq -e '
  .mcpServers.keep
  and .mcpServers.asana.lifecycle == "lazy"
  and .mcpServers.asana.url == "https://mcp.asana.com/v2/mcp"
  and (.mcpServers["megai-dembrandt"] | not)
  and (.mcpServers["megai-argent"] | not)
  and (.mcpServers["megai-repowise"] | not)
' "$PI_CODING_AGENT_DIR/mcp.json" >/dev/null

bash "$MEGAI_HOME/lib/wire_cc.sh" --remove >/dev/null
bash "$MEGAI_HOME/lib/wire_codex.sh" --remove >/dev/null
bash "$MEGAI_HOME/lib/wire_pi.sh" --remove >/dev/null 2>&1

jq -e '.mcpServers.dembrandt.command == "user-dembrandt" and .mcpServers.argent.command == "user-argent" and .mcpServers.repowise.command == "user-repowise" and (.mcpServers["megai-dembrandt"] | not) and (.mcpServers["megai-argent"] | not) and (.mcpServers["megai-repowise"] | not)' "$HOME/.claude.json" >/dev/null
[ "$(grep -c '^\[mcp_servers.dembrandt\]$' "$HOME/.codex/config.toml")" = "1" ]
[ "$(grep -c '^\[mcp_servers.argent\]$' "$HOME/.codex/config.toml")" = "1" ]
[ "$(grep -c '^\[mcp_servers.repowise\]$' "$HOME/.codex/config.toml")" = "1" ]
! grep -q '^\[mcp_servers.megai-dembrandt\]$' "$HOME/.codex/config.toml"
! grep -q '^\[mcp_servers.megai-argent\]$' "$HOME/.codex/config.toml"
! grep -q '^\[mcp_servers.megai-repowise\]$' "$HOME/.codex/config.toml"
[ "$(grep -c '^\[mcp_servers.external-app\]$' "$HOME/.codex/config.toml")" = "1" ]
[ "$(grep -c '^\[mcp_servers.external-app.env\]$' "$HOME/.codex/config.toml")" = "1" ]
jq -e '.mcpServers.keep and .mcpServers.asana.lifecycle == "lazy" and .mcpServers.asana.url == "https://mcp.asana.com/v2/mcp" and (.mcpServers["megai-dembrandt"] | not) and (.mcpServers["megai-argent"] | not) and (.mcpServers["megai-repowise"] | not)' "$PI_CODING_AGENT_DIR/mcp.json" >/dev/null

# Missing optional executables must not leave broken MCP entries.
jq 'del(.tools.dembrandt, .tools.argent, .tools.repowise)' "$MEGAI_HOME/state.json" >"$MEGAI_HOME/state.tmp"
mv "$MEGAI_HOME/state.tmp" "$MEGAI_HOME/state.json"
jq '.mcpServers["megai-dembrandt"] = {command:"stale"} | .mcpServers["megai-argent"] = {command:"stale"} | .mcpServers["megai-repowise"] = {command:"stale"}' "$HOME/.claude.json" >"$HOME/.claude.tmp"
mv "$HOME/.claude.tmp" "$HOME/.claude.json"
jq '.mcpServers["megai-dembrandt"] = {command:"stale"} | .mcpServers["megai-argent"] = {command:"stale"} | .mcpServers["megai-repowise"] = {command:"stale"}' "$PI_CODING_AGENT_DIR/mcp.json" >"$PI_CODING_AGENT_DIR/mcp.tmp"
mv "$PI_CODING_AGENT_DIR/mcp.tmp" "$PI_CODING_AGENT_DIR/mcp.json"
bash "$MEGAI_HOME/lib/wire_cc.sh" >/dev/null 2>&1
bash "$MEGAI_HOME/lib/wire_codex.sh" >/dev/null 2>&1
bash "$MEGAI_HOME/lib/wire_pi.sh" >/dev/null 2>&1
jq -e '(.mcpServers["megai-dembrandt"] | not) and (.mcpServers["megai-argent"] | not) and (.mcpServers["megai-repowise"] | not)' "$HOME/.claude.json" >/dev/null
! grep -q '^\[mcp_servers.megai-dembrandt\]$' "$HOME/.codex/config.toml"
! grep -q '^\[mcp_servers.megai-argent\]$' "$HOME/.codex/config.toml"
! grep -q '^\[mcp_servers.megai-repowise\]$' "$HOME/.codex/config.toml"
jq -e '(.mcpServers["megai-dembrandt"] | not) and (.mcpServers["megai-argent"] | not) and (.mcpServers["megai-repowise"] | not)' "$PI_CODING_AGENT_DIR/mcp.json" >/dev/null

echo "MCP wiring: ok"

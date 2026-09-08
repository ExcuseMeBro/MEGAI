#!/usr/bin/env bash
# Retired Caveman compatibility guard: Headroom is the shared active default.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home" MEGAI_HOME="$TMP/megai" MEGAI_SOURCE="$ROOT"
export PI_CODING_AGENT_DIR="$HOME/.pi/agent" CODEX_HOME="$HOME/.codex"
export PATH="$TMP/bin:$PATH"
mkdir -p "$HOME" "$MEGAI_HOME" "$TMP/bin"
printf '{"tools":{},"agents":{},"ports":{"agent-memory":3111},"keep":true}\n' > "$MEGAI_HOME/state.json"
for command in codedb zg; do printf '#!/bin/sh\nexit 0\n' >"$TMP/bin/$command"; chmod +x "$TMP/bin/$command"; done
mkdir -p "$HOME/.claude" "$HOME/.codex" "$HOME/.pi/agent" "$HOME/.omp/agent"
printf '{}\n' >"$HOME/.claude/settings.json"
printf '{}\n' >"$HOME/.claude/mcp.json"
printf '# empty Codex config\n' >"$HOME/.codex/config.toml"
printf '{}\n' >"$HOME/.pi/agent/settings.json"
printf '{}\n' >"$HOME/.pi/agent/mcp.json"
printf '{}\n' >"$HOME/.omp/agent/settings.json"
printf '{}\n' >"$HOME/.omp/agent/mcp.json"
python3 "$ROOT/lib/slim_wiring.py" all >/dev/null
for path in "$HOME/.claude/CLAUDE.md" "$HOME/.codex/AGENTS.md" "$HOME/.pi/agent/AGENTS.md" "$HOME/.omp/agent/RULES.md"; do
  grep -q Headroom "$path"
  ! grep -qE 'GPT-only|Astra|MiniMax' "$path"
done
jq -e '.tools["agent-memory"] == null and .ports["agent-memory"] == null and .keep == true' "$MEGAI_HOME/state.json" >/dev/null
jq -e '.defaultProvider == null and (.skills | map(select(contains(".agents/skills/**"))) | length) == 1' "$PI_CODING_AGENT_DIR/settings.json" >/dev/null
[ -f "$PI_CODING_AGENT_DIR/extensions/megai-headroom/index.ts" ]
# User-owned retired registrations refuse migration without changing config.
printf '{"skills":["npm:agent-memory"]}\n' > "$PI_CODING_AGENT_DIR/settings.json"
cp "$PI_CODING_AGENT_DIR/settings.json" "$TMP/before"
if python3 "$ROOT/lib/slim_wiring.py" pi >/dev/null 2>&1; then exit 1; fi
cmp "$PI_CODING_AGENT_DIR/settings.json" "$TMP/before"
echo 'Headroom compatibility PASS: neutral four-harness policy, retirement state cleanup, Pi adapter and fail-closed legacy selection'

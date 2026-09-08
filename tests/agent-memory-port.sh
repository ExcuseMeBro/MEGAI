#!/usr/bin/env bash
# Legacy agent-memory migration guard: no daemon or port selection remains active.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home" MEGAI_HOME="$TMP/megai" MEGAI_SOURCE="$ROOT"
export PI_CODING_AGENT_DIR="$HOME/.pi/agent" CODEX_HOME="$HOME/.codex" PATH="$TMP/bin:$PATH"
mkdir -p "$MEGAI_HOME/bin" "$MEGAI_HOME/lib" "$HOME/.pi/agent" "$HOME/.codex" "$TMP/bin"
cp "$ROOT/bin/megai" "$MEGAI_HOME/bin/megai"
cp "$ROOT/lib/ui.sh" "$ROOT/lib/state.sh" "$ROOT/lib/slim_wiring.py" "$MEGAI_HOME/lib/"
printf '{"tools":{"agent-memory":{"version":"legacy"}},"ports":{"agent-memory":3112},"agents":{}}\n' > "$MEGAI_HOME/state.json"
printf '{}\n' > "$HOME/.pi/agent/settings.json"
printf '{}\n' > "$HOME/.pi/agent/mcp.json"
printf '# empty\n' > "$HOME/.codex/config.toml"
printf '#!/bin/sh\nexit 0\n' > "$TMP/bin/zg"; chmod +x "$TMP/bin/zg"
python3 "$ROOT/lib/slim_wiring.py" pi >/dev/null
jq -e '.tools["agent-memory"] == null and .ports["agent-memory"] == null' "$MEGAI_HOME/state.json" >/dev/null
[ ! -e "$MEGAI_HOME/bin/megai-memory" ]
if bash "$ROOT/bin/megai" start >/dev/null 2>&1; then exit 1; fi
if bash "$ROOT/bin/megai" stop >/dev/null 2>&1; then exit 1; fi
echo 'agent-memory retirement: port state cleared, daemon lifecycle refused, Headroom remains the active adapter'

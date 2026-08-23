#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home"
export MEGAI_HOME="$TMP/megai"
mkdir -p "$MEGAI_HOME/lib" "$TMP/bin"
cp "$ROOT/lib/ui.sh" "$ROOT/lib/state.sh" "$ROOT/lib/detect.sh" "$MEGAI_HOME/lib/"
printf '%s\n' '{"tools":{},"ports":{"agent-memory":3111},"agents":{},"projects":{}}' >"$MEGAI_HOME/state.json"

cat >"$TMP/bin/agentmemory" <<'SH'
#!/bin/sh
case "${1:-}" in
  --version) echo "agentmemory 1.0.0" ;;
  status) exit 1 ;;
esac
SH
cat >"$TMP/bin/lsof" <<'SH'
#!/bin/sh
case "$*" in
  *-iTCP:3111*) exit 0 ;;
  *) exit 1 ;;
esac
SH
chmod +x "$TMP/bin/agentmemory" "$TMP/bin/lsof"
jq_dir="$(dirname "$(command -v jq)")"
export PATH="$TMP/bin:$jq_dir:/usr/bin:/bin"

bash "$ROOT/lib/install_agent_memory.sh" >/dev/null
jq -e '.ports["agent-memory"] == 3112 and .tools["agent-memory"].port == 3112' "$MEGAI_HOME/state.json" >/dev/null

echo "agent-memory port recovery: ok"

#!/usr/bin/env bash
# megai-memory — HTTP bridge to agent-memory daemon
set -euo pipefail

MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
PORT="${AGENTMEMORY_PORT:-}"
if [ -z "$PORT" ] && [ -f "$MEGAI_HOME/state.json" ] && command -v jq >/dev/null 2>&1; then
  PORT="$(jq -r '.ports["agent-memory"] // 3111' "$MEGAI_HOME/state.json")"
fi
PORT="${PORT:-3111}"
BASE="http://127.0.0.1:$PORT/agentmemory"

usage() {
  cat <<EOF
megai-memory <sub> [args]

  save <text>       Save observation
  recall <query>    Smart search
  sessions          List sessions
  stats             Memory stats
EOF
}

http_get()  { curl -fsS "$BASE/$1" || { echo "{\"error\":\"agent-memory daemon not reachable on :$PORT — run 'megai start agent-memory'\"}" >&2; exit 1; }; }
http_post() { curl -fsS -X POST -H "Content-Type: application/json" -d "$2" "$BASE/$1" || { echo "error: POST $1 failed" >&2; exit 1; }; }

case "${1:-help}" in
  save)
    shift; text="$*"
    [ -n "$text" ] || { echo "usage: megai-memory save <text>"; exit 1; }
    http_post "save" "{\"content\":$(printf '%s' "$text" | jq -Rs .)}"
    ;;
  recall)
    shift; q="$*"
    [ -n "$q" ] || { echo "usage: megai-memory recall <query>"; exit 1; }
    http_post "smart-search" "{\"query\":$(printf '%s' "$q" | jq -Rs .)}"
    ;;
  sessions) http_get "sessions" ;;
  stats)    http_get "stats" ;;
  help|-h|--help|"") usage ;;
  *) usage; exit 1 ;;
esac

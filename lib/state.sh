#!/usr/bin/env bash
# state.json read/write (requires jq)
STATE_FILE="${MEGAI_HOME:-$HOME/.megai}/state.json"

state_init() {
  [ -f "$STATE_FILE" ] && return 0
  cat > "$STATE_FILE" <<'EOF'
{
  "version": "0.1.0",
  "tools": {},
  "ports": {},
  "agents": {},
  "projects": {}
}
EOF
}

state_set() {
  # state_set <jq-path> <json-value>
  local path="$1" val="$2" tmp
  tmp="$(mktemp)"
  jq "$path = $val" "$STATE_FILE" > "$tmp" && mv "$tmp" "$STATE_FILE"
}

state_get() {
  jq -r "$1 // empty" "$STATE_FILE"
}

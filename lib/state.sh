#!/usr/bin/env bash
# Paths are internal field selectors; JSON values are data, never jq source.
STATE_FILE="${MEGAI_HOME:-$HOME/.megai}/state.json"
state_init() {
  if [ -L "$STATE_FILE" ] || { [ -e "$STATE_FILE" ] && { [ ! -f "$STATE_FILE" ] || [ ! -O "$STATE_FILE" ]; }; }; then
    printf 'unsafe MEGAI state: %s\n' "$STATE_FILE" >&2; return 1
  fi
  if [ -f "$STATE_FILE" ]; then
    jq -e 'type == "object"' "$STATE_FILE" >/dev/null || { printf 'malformed MEGAI state\n' >&2; return 1; }
    return
  fi
  mkdir -p "$(dirname "$STATE_FILE")"
  local tmp
  tmp="$(mktemp "${STATE_FILE}.XXXXXX")"
  printf '%s\n' '{"version":"0.1.0","tools":{},"ports":{},"agents":{},"projects":{}}' >"$tmp"
  mv "$tmp" "$STATE_FILE"
}
state_set() {
  local path="$1" val="$2" tmp
  printf '%s\n' "$path" | grep -Eq '^(\.[[:alnum:]_-]+|\["[[:alnum:]_-]+"\])+$' || { printf 'invalid state selector\n' >&2; return 1; }
  state_init || return 1
  tmp="$(mktemp "${STATE_FILE}.XXXXXX")"
  if jq --argjson value "$val" "$path = \$value" "$STATE_FILE" >"$tmp"; then
    mv "$tmp" "$STATE_FILE"
  else
    rm -f "$tmp"; return 1
  fi
}
state_get() {
  [ -f "$STATE_FILE" ] || return 0
  [ ! -L "$STATE_FILE" ] && [ -O "$STATE_FILE" ] || return 1
  jq -r "$1 // empty" "$STATE_FILE"
}

#!/usr/bin/env bash
set -euo pipefail

command -v omp >/dev/null 2>&1 || {
  echo "OMP native MiniMax catalog: omp is required" >&2
  exit 1
}

without="$(env -u MINIMAX_API_KEY omp models --json)"
printf '%s\n' "$without" |
  jq -e '
    (if type == "array" then . else .models end)
    | map(select(.provider == "minimax"))
    | length == 0
  ' >/dev/null

with_key="$(MINIMAX_API_KEY=test-only omp models --json)"
printf '%s\n' "$with_key" |
  jq -e '
    (if type == "array" then . else .models end)
    | map(select(.provider == "minimax"))
    | map(.id)
    | (index("MiniMax-M2.7") != null and index("MiniMax-M2.7-highspeed") != null)
  ' >/dev/null

echo "OMP native MiniMax catalog: ok"

#!/usr/bin/env bash
set -euo pipefail

command -v omp >/dev/null 2>&1 || {
  echo "OMP native MiniMax catalog: omp is required" >&2
  exit 1
}
# Metadata-only catalog check. Credential-backed MiniMax inference is exercised
# by omp-agent-discovery-live.sh when OMP_LIVE_AGENT_TEST=1.

catalog="$(MINIMAX_CODE_API_KEY=catalog-only omp models --json)"
printf '%s\n' "$catalog" |
  jq -e '
    (if type == "array" then . else .models end)
    | map(select(.provider == "minimax-code"))
    | map(.id)
    | (index("MiniMax-M3") != null and index("MiniMax-M2.7") != null)
  ' >/dev/null

echo "OMP native MiniMax catalog metadata: ok"

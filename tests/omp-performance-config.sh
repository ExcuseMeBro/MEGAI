#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
config="$ROOT/omp-config/high-speed.yml"
[ -f "$config" ]
! grep -q '^[[:space:]]*default:' "$config"
grep -q 'codeMode: auto' "$config"
grep -q 'maxConcurrency: 6' "$config"
grep -q 'minimax: 4' "$config"

command -v omp >/dev/null 2>&1 || {
  echo "OMP high-speed config: omp is required" >&2
  exit 1
}
PI_CONFIG_FILES="$config" omp config list --json |
  jq -e '
    .["providers.openai-codex.codeMode"].value == "auto"
    and .["providers.maxInFlightRequests"].value["openai-codex"] == 2
    and .["providers.maxInFlightRequests"].value.minimax == 4
    and .["task.maxConcurrency"].value == 6
    and .["task.batch"].value == true
    and .["task.isolation.mode"].value == "auto"
    and .["task.isolation.merge"].value == "branch"
    and .["task.isolation.apply"].value == true
    and .["async.enabled"].value == true
  ' >/dev/null

echo "OMP high-speed config: ok"

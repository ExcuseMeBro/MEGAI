#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
performance="$ROOT/omp-config/high-speed.yml"
balanced="$ROOT/omp-config/balanced-minimax.yml"
[ -f "$performance" ]
[ -f "$balanced" ]
grep -q 'default: minimax-code/MiniMax-M3:medium' "$balanced"
grep -q 'tiny: minimax-code/MiniMax-M3:minimal' "$balanced"
grep -q 'commit: minimax-code/MiniMax-M3:minimal' "$balanced"
! grep -q 'subagents:' "$balanced"
grep -q 'codeMode: auto' "$performance"
grep -q 'maxConcurrency: 6' "$performance"
grep -q 'minimax-code: 4' "$performance"

command -v omp >/dev/null 2>&1 || {
  echo "OMP high-speed config: omp is required" >&2
  exit 1
}
PI_CONFIG_FILES="$performance:$balanced" MINIMAX_CODE_API_KEY=test-only omp config list --json |
  jq -e '
    .modelRoles.value.default == "minimax-code/MiniMax-M3:medium"
    and .modelRoles.value.task == "minimax-code/MiniMax-M3:medium"
    and .modelRoles.value.smol == "minimax-code/MiniMax-M3:low"
    and .modelRoles.value.tiny == "minimax-code/MiniMax-M3:minimal"
    and .modelRoles.value.commit == "minimax-code/MiniMax-M3:minimal"
    and .modelRoles.value.plan == "openai-codex/gpt-5.6-sol:high"
    and .modelRoles.value.slow == "openai-codex/gpt-5.6-sol:high"
    and .modelRoles.value.advisor == "openai-codex/gpt-5.6-sol:high"
    and .modelRoles.value.vision == "openai-codex/gpt-5.6-sol:medium"
    and .defaultThinkingLevel.value == "medium"
    and .["advisor.enabled"].value == false
    and .["providers.openai-codex.codeMode"].value == "auto"
    and .["providers.maxInFlightRequests"].value["openai-codex"] == 2
    and .["providers.maxInFlightRequests"].value["minimax-code"] == 4
    and .["task.maxConcurrency"].value == 6
    and .["task.batch"].value == true
    and .["task.agentAdvisor"].value == {}
    and .["task.isolation.mode"].value == "auto"
    and .["task.isolation.merge"].value == "branch"
    and .["task.isolation.apply"].value == true
    and .["async.enabled"].value == true
    and .["retry.fallbackChains"].value["openai-codex/gpt-5.6-sol"] == null
    and .["retry.fallbackChains"].value["minimax-code/MiniMax-M3"][0] == "openai-codex/gpt-5.6-terra:medium"
  ' >/dev/null

echo "OMP high-speed config: ok"

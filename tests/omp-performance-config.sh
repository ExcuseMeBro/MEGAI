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
grep -q 'showResolvedModelBadge: true' "$performance"
for model in \
  minimax-code/MiniMax-M2 \
  minimax-code/MiniMax-M2.1 \
  minimax-code/MiniMax-M2.1-lightning \
  minimax-code/MiniMax-M2.5 \
  minimax-code/MiniMax-M2.5-highspeed \
  minimax-code/MiniMax-M2.5-lightning \
  minimax-code/MiniMax-M2.7 \
  minimax-code/MiniMax-M2.7-highspeed \
  minimax-code/MiniMax-M3 \
  openai-codex/gpt-5.3-codex-spark \
  openai-codex/gpt-5.4-mini \
  openai-codex/gpt-5.4 \
  openai-codex/gpt-5.5 \
  openai-codex/gpt-5.6-luna \
  openai-codex/gpt-5.6-terra \
  openai-codex/gpt-5.6-sol; do
  grep -Fq "$model:" "$balanced"
done
for model in \
  minimax-code/MiniMax-M2 \
  minimax-code/MiniMax-M2.1 \
  minimax-code/MiniMax-M2.1-lightning \
  minimax-code/MiniMax-M2.5 \
  minimax-code/MiniMax-M2.5-highspeed \
  minimax-code/MiniMax-M2.5-lightning \
  minimax-code/MiniMax-M2.7 \
  minimax-code/MiniMax-M2.7-highspeed \
  minimax-code/MiniMax-M3 \
  openai-codex/gpt-5.3-codex-spark \
  openai-codex/gpt-5.4-mini \
  openai-codex/gpt-5.4 \
  openai-codex/gpt-5.5 \
  openai-codex/gpt-5.6-luna \
  openai-codex/gpt-5.6-terra; do
  grep -Fq "    \"$model\":" "$balanced"
done

command -v omp >/dev/null 2>&1 || {
  echo "OMP high-speed config: omp is required" >&2
  exit 1
}
PI_CONFIG_FILES="$performance:$balanced" MINIMAX_CODE_API_KEY=test-only omp config list --json |
  jq -e '
    def strip_effort: sub(":(minimal|low|medium|high|xhigh|max)$"; "");
    def has_cycle($graph; $node; $seen):
      if ($seen | index($node)) != null then true
      else any(($graph[$node] // [])[]; has_cycle($graph; .; ($seen + [$node])))
      end;
    .modelRoles.value.default == "minimax-code/MiniMax-M3:medium"
    and .modelRoles.value.task == "minimax-code/MiniMax-M3:medium"
    and .modelRoles.value.smol == "minimax-code/MiniMax-M3:low"
    and .modelRoles.value.tiny == "minimax-code/MiniMax-M3:minimal"
    and .modelRoles.value.commit == "minimax-code/MiniMax-M3:minimal"
    and .modelRoles.value.plan == "openai-codex/gpt-5.6-sol:high"
    and .modelRoles.value.slow == "openai-codex/gpt-5.6-sol:high"
    and .modelRoles.value.advisor == "openai-codex/gpt-5.6-sol:high"
    and .modelRoles.value.vision == "openai-codex/gpt-5.6-sol:medium"
    and .modelRoles.value.final == "openai-codex/gpt-5.6-sol:high"
    and .modelRoles.value.architecture == "openai-codex/gpt-5.6-terra:high"
    and .modelRoles.value.terra == "openai-codex/gpt-5.6-terra:medium"
    and .modelRoles.value.review == "openai-codex/gpt-5.6-terra:high"
    and .modelRoles.value.luna == "openai-codex/gpt-5.6-luna:low"
    and .modelRoles.value.scout == "openai-codex/gpt-5.6-luna:low"
    and .modelRoles.value.repo == "minimax-code/MiniMax-M2.1-lightning:low"
    and .modelRoles.value["worker-fast"] == "minimax-code/MiniMax-M2.7-highspeed:medium"
    and .modelRoles.value["worker-quality"] == "minimax-code/MiniMax-M2.7:high"
    and .modelRoles.value.tests == "minimax-code/MiniMax-M2.5-highspeed:low"
    and .modelRoles.value.docker == "minimax-code/MiniMax-M2.5-lightning:low"
    and .modelRoles.value.migration == "minimax-code/MiniMax-M2.5:medium"
    and .modelRoles.value["worker-stable"] == "minimax-code/MiniMax-M2.1:medium"
    and .modelRoles.value["worker-legacy"] == "minimax-code/MiniMax-M2:low"
    and .modelRoles.value.debug == "openai-codex/gpt-5.5:high"
    and .modelRoles.value["long-context"] == "openai-codex/gpt-5.4:high"
    and .modelRoles.value["review-fast"] == "openai-codex/gpt-5.4-mini:medium"
    and .modelRoles.value["trusted-fast"] == "openai-codex/gpt-5.3-codex-spark:low"
    and .defaultThinkingLevel.value == "medium"
    and .["advisor.enabled"].value == false
    and .["providers.openai-codex.codeMode"].value == "auto"
    and .["providers.maxInFlightRequests"].value["openai-codex"] == 2
    and .["providers.maxInFlightRequests"].value["minimax-code"] == 4
    and .["task.maxConcurrency"].value == 6
    and .["task.batch"].value == true
    and .["task.showResolvedModelBadge"].value == true
    and .["task.agentModelOverrides"].value.task == "minimax-code/MiniMax-M3:medium"
    and .["task.agentModelOverrides"].value.scout == "minimax-code/MiniMax-M2.1-lightning:low"
    and .["task.agentModelOverrides"].value["cavecrew-investigator"] == "minimax-code/MiniMax-M2.1-lightning:low"
    and .["task.agentModelOverrides"].value["cavecrew-builder"] == "minimax-code/MiniMax-M2.7-highspeed:medium"
    and .["task.agentModelOverrides"].value["minimax-commit-writer"] == "minimax-code/MiniMax-M3:minimal"
    and .["task.agentModelOverrides"].value.reviewer == "openai-codex/gpt-5.6-terra:high"
    and .["task.agentModelOverrides"].value["security-reviewer"] == "openai-codex/gpt-5.6-sol:high"
    and .["task.agentAdvisor"].value == {}
    and .["task.isolation.mode"].value == "auto"
    and .["task.isolation.merge"].value == "branch"
    and .["task.isolation.apply"].value == true
    and .["async.enabled"].value == true
    and .["retry.maxDelayMs"].value == 300000
    and ([
      .["retry.fallbackChains"].value
      | to_entries[]
      | select(.key | startswith("openai-codex/"))
      | .value[]
      | select(startswith("minimax-code/"))
    ] | length == 0)
    and ([
      .["retry.fallbackChains"].value
      | to_entries[]
      | select(.key | startswith("minimax-code/"))
      | .value[]
      | select(startswith("minimax-code/"))
    ] | length == 0)
    and (
      (.["retry.fallbackChains"].value | with_entries(.value |= map(strip_effort))) as $graph
      | all($graph | keys[]; (has_cycle($graph; .; []) | not))
    )
    and .["retry.fallbackChains"].value["openai-codex/gpt-5.6-sol"] == null
    and .["retry.fallbackChains"].value["minimax-code/MiniMax-M3"][0] == "openai-codex/gpt-5.6-terra:medium"
  ' >/dev/null

echo "OMP high-speed config: ok"

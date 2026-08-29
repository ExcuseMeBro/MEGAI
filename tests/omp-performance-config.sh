#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
performance="$ROOT/omp-config/high-speed.yml"
balanced="$ROOT/omp-config/balanced-minimax.yml"
[ -f "$performance" ]
[ -f "$balanced" ]
grep -q 'default: openai-codex/gpt-5.6-terra:medium' "$balanced"
grep -q 'task: openai-codex/gpt-5.6-terra:medium' "$balanced"
grep -q 'repo: minimax-code/MiniMax-M2.1-lightning:low' "$balanced"
! grep -q 'subagents:' "$balanced"
grep -q 'codeMode: auto' "$performance"
grep -q 'maxConcurrency: 4' "$performance"
grep -q 'minimax-code: 2' "$performance"
grep -q 'showResolvedModelBadge: true' "$performance"
grep -q 'maxJobs: 4' "$performance"
grep -q 'maxEffort: high' "$performance"
grep -q 'softRequestBudget: 16' "$performance"
grep -q 'maxRuntimeMs: 300000' "$performance"
grep -q 'enabled: false' "$performance"
grep -q 'threshold: 2' "$performance"
! grep -Eq 'MiniMax-(M3|M2\.7|M2\.5|M2\.1:|M2:)' "$balanced"
grep -q 'gpt-core-worker: openai-codex/gpt-5.6-terra:medium' "$balanced"
grep -q 'gpt-fast-worker: openai-codex/gpt-5.4-mini:medium' "$balanced"

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
    .modelRoles.value.default == "openai-codex/gpt-5.6-terra:medium"
    and .modelRoles.value.task == "openai-codex/gpt-5.6-terra:medium"
    and .modelRoles.value.smol == "openai-codex/gpt-5.4-mini:medium"
    and .modelRoles.value.tiny == "openai-codex/gpt-5.3-codex-spark:low"
    and .modelRoles.value.commit == "openai-codex/gpt-5.3-codex-spark:low"
    and .modelRoles.value.repo == "minimax-code/MiniMax-M2.1-lightning:low"
    and .modelRoles.value.scout == "minimax-code/MiniMax-M2.1-lightning:low"
    and .modelRoles.value["worker-fast"] == "openai-codex/gpt-5.4-mini:medium"
    and .modelRoles.value["worker-quality"] == "openai-codex/gpt-5.6-terra:high"
    and .modelRoles.value.tests == "openai-codex/gpt-5.4-mini:medium"
    and .modelRoles.value.docker == "openai-codex/gpt-5.3-codex-spark:low"
    and .modelRoles.value.migration == "openai-codex/gpt-5.5:high"
    and .modelRoles.value["worker-stable"] == "openai-codex/gpt-5.4:high"
    and .modelRoles.value["worker-legacy"] == "openai-codex/gpt-5.3-codex-spark:low"
    and .modelRoles.value.plan == "openai-codex/gpt-5.6-sol:high"
    and .modelRoles.value.architecture == "openai-codex/gpt-5.6-terra:high"
    and .modelRoles.value.review == "openai-codex/gpt-5.6-terra:high"
    and .modelRoles.value.debug == "openai-codex/gpt-5.5:high"
    and .modelRoles.value["long-context"] == "openai-codex/gpt-5.4:high"
    and .modelRoles.value["review-fast"] == "openai-codex/gpt-5.4-mini:medium"
    and .modelRoles.value["trusted-fast"] == "openai-codex/gpt-5.3-codex-spark:low"
    and .defaultThinkingLevel.value == "medium"
    and .["advisor.enabled"].value == false
    and .["providers.openai-codex.codeMode"].value == "auto"
    and .["providers.maxInFlightRequests"].value["openai-codex"] == 2
    and .["providers.maxInFlightRequests"].value["minimax-code"] == 2
    and .["task.maxConcurrency"].value == 4
    and .["task.batch"].value == true
    and .["task.showResolvedModelBadge"].value == true
    and .["async.maxJobs"].value == 4
    and .["task.maxEffort"].value == "high"
    and .["task.softRequestBudget"].value == 16
    and .["task.maxRuntimeMs"].value == 300000
    and .["goal.enabled"].value == false
    and .["model.toolCallLoopGuard.threshold"].value == 2
    and .["task.agentModelOverrides"].value.task == "openai-codex/gpt-5.6-terra:medium"
    and .["task.agentModelOverrides"].value.scout == "minimax-code/MiniMax-M2.1-lightning:low"
    and .["task.agentModelOverrides"].value["cavecrew-investigator"] == "minimax-code/MiniMax-M2.1-lightning:low"
    and .["task.agentModelOverrides"].value["cavecrew-builder"] == "openai-codex/gpt-5.4-mini:medium"
    and .["task.agentModelOverrides"].value["gpt-core-worker"] == "openai-codex/gpt-5.6-terra:medium"
    and .["task.agentModelOverrides"].value["gpt-fast-worker"] == "openai-codex/gpt-5.4-mini:medium"
    and .["task.agentModelOverrides"].value["minimax-worker"] == "openai-codex/gpt-5.6-terra:medium"
    and .["task.agentModelOverrides"].value["minimax-test-worker"] == "openai-codex/gpt-5.4-mini:medium"
    and .["task.agentModelOverrides"].value.reviewer == "openai-codex/gpt-5.6-terra:high"
    and .["task.agentModelOverrides"].value["security-reviewer"] == "openai-codex/gpt-5.6-sol:high"
    and .["task.agentAdvisor"].value == {}
    and .["task.isolation.mode"].value == "auto"
    and .["task.isolation.merge"].value == "branch"
    and .["task.isolation.apply"].value == true
    and .["async.enabled"].value == true
    and .["retry.maxDelayMs"].value == 30000
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
    and ([.["retry.fallbackChains"].value | to_entries[] | select((.key | startswith("minimax-code/")) and (.value | length > 0))] | length == 1)
    and (
      (.["retry.fallbackChains"].value | with_entries(.value |= map(strip_effort))) as $graph
      | all($graph | keys[]; (has_cycle($graph; .; []) | not))
    )
    and .["retry.fallbackChains"].value["openai-codex/gpt-5.6-sol"] == []
    and .["retry.fallbackChains"].value["openai-codex/gpt-5.6-terra"] == []
    and .["retry.fallbackChains"].value["openai-codex/gpt-5.6-luna"] == []
    and .["retry.fallbackChains"].value["openai-codex/gpt-5.3-codex-spark"] == []
    and .["retry.fallbackChains"].value["minimax-code/MiniMax-M2.1-lightning"][0] == "openai-codex/gpt-5.6-luna:low"
  ' >/dev/null

echo "OMP high-speed config: ok"

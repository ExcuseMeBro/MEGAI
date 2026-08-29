#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

command -v omp >/dev/null 2>&1 || {
  echo "OMP native MiniMax catalog: omp is required" >&2
  exit 1
}
# Metadata-only catalog check. Credential-backed MiniMax inference is exercised
# by omp-agent-discovery-live.sh when OMP_LIVE_AGENT_TEST=1.

catalog="$(MINIMAX_CODE_API_KEY=catalog-only omp models minimax-code --json)"
printf '%s\n' "$catalog" |
  jq -e '
    [.models[].id] as $ids
    | ([
        "MiniMax-M2",
        "MiniMax-M2.1",
        "MiniMax-M2.1-lightning",
        "MiniMax-M2.5",
        "MiniMax-M2.5-highspeed",
        "MiniMax-M2.5-lightning",
        "MiniMax-M2.7",
        "MiniMax-M2.7-highspeed",
        "MiniMax-M3"
      ] - $ids | length == 0)
    and (.models[] | select(.id == "MiniMax-M3") | .thinking | index("minimal") != null)
  ' >/dev/null

gpt_catalog="$(omp models openai-codex --json)"
printf '%s\n' "$gpt_catalog" |
  jq -e '
    [.models[].id] as $ids
    | ([
        "gpt-5.3-codex-spark",
        "gpt-5.4-mini",
        "gpt-5.4",
        "gpt-5.5",
        "gpt-5.6-luna",
        "gpt-5.6-terra",
        "gpt-5.6-sol"
      ] - $ids | length == 0)
  ' >/dev/null

roles="$(
  PI_CONFIG_FILES="$ROOT/omp-config/balanced-minimax.yml" MINIMAX_CODE_API_KEY=catalog-only \
    omp config list --json | jq '.modelRoles.value'
)"
jq -en \
  --argjson roles "$roles" \
  --argjson minimax "$catalog" \
  --argjson gpt "$gpt_catalog" '
    ($minimax.models + $gpt.models) as $models
    | all(
        $roles | to_entries[];
        (.value | capture("^(?<selector>.+):(?<effort>[^:]+)$")) as $route
        | any(
            $models[];
            .selector == $route.selector and (.thinking | index($route.effort) != null)
          )
      )
  ' >/dev/null

echo "OMP native model portfolio metadata: ok"

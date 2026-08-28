#!/usr/bin/env bash
set -euo pipefail

if [ "${OMP_LIVE_AGENT_TEST:-0}" != 1 ]; then
  echo "OMP live agent discovery: skipped (set OMP_LIVE_AGENT_TEST=1)"
  exit 0
fi

command -v omp >/dev/null 2>&1 || { echo "OMP live agent discovery: omp missing" >&2; exit 1; }

cwd="${OMP_LIVE_CWD:-$(cd "$(dirname "$0")/.." && pwd)}"
output="$(
  cd "$cwd"
  omp -p --no-session --no-title --thinking low --max-time 3m \
    "Delegate two read-only tasks in one batch. Use smart-router to locate where wire_omp.sh installs smart-router.md. Use terra-scout to locate the global worktree policy that enforces dev-to-main delivery. Return compact path:line evidence from both agents. Do not edit or run tests."
)"

printf '%s\n' "$output" | grep -q 'lib/wire_omp.sh'
printf '%s\n' "$output" | grep -Eq 'install_worktree_lifecycle.sh|agent-worktree-lifecycle|CLAUDE.md'
printf '%s\n' "$output" | grep -q 'smart-router'

echo "OMP live agent discovery: ok"

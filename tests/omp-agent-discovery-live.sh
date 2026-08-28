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
    "Delegate two read-only tasks in one batch to smart-router. Task A: treat the first MiniMax lookup as unresolved, escalate exactly once to luna-scout, locate where wire_omp.sh installs luna-scout.md, and include route=luna-scout. Task B: treat this as cross-module lifecycle reasoning, escalate exactly once to terra-scout, locate the global dev-to-main worktree policy, and include route=terra-scout. Return compact path:line evidence. Do not edit or run tests."
)"

printf '%s\n' "$output" | grep -q 'lib/wire_omp.sh'
printf '%s\n' "$output" | grep -Eq 'install_worktree_lifecycle.sh|agent-worktree-lifecycle|CLAUDE.md'
printf '%s\n' "$output" | grep -q 'route=luna-scout'
printf '%s\n' "$output" | grep -q 'route=terra-scout'

echo "OMP live agent discovery: ok"

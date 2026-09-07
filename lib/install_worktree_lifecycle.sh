#!/usr/bin/env bash
# Worktree policy shares the same preservation-safe installer as Plane policy.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
. "$MEGAI_HOME/lib/state.sh"
python3 "$MEGAI_HOME/lib/slim_wiring.py" pi "$@"
[ "${1:-}" = "--remove" ] || state_set '.tools["worktree-lifecycle"]' '{"wired":true,"profile":"slim"}'

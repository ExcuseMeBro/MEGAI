#!/usr/bin/env bash
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
. "$MEGAI_HOME/lib/state.sh"
python3 "$MEGAI_HOME/lib/slim_wiring.py" omp "$@"
[ "${1:-}" = "--remove" ] || state_set '.agents.omp' '{"wired":true,"profile":"slim"}'

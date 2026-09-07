#!/usr/bin/env bash
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
. "$MEGAI_HOME/lib/state.sh"
python3 "$MEGAI_HOME/lib/slim_wiring.py" cc "$@"
[ "${1:-}" = "--remove" ] || state_set '.agents.cc' '{"wired":true,"profile":"slim"}'

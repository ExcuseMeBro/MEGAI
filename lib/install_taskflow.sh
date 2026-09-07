#!/usr/bin/env bash
# Plane-only policy and shared slim skill wiring; no local board hooks.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
. "$MEGAI_HOME/lib/state.sh"
python3 "$MEGAI_HOME/lib/slim_wiring.py" pi "$@"
[ "${1:-}" = "--remove" ] || state_set '.tools["task-flow"]' '{"wired":true,"mode":"plane-only"}'

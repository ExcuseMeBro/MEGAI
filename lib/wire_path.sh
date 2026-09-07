#!/usr/bin/env bash
# PATH uses the same preflight, ownership checks and rollback as slim policies.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
exec python3 "$MEGAI_HOME/lib/slim_wiring.py" path "$@"

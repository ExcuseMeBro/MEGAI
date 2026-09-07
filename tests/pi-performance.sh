#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/tests/slim_distribution.py" Slim.test_pi_adapter_preserves_explicit_selection_and_ignores_full_flag Slim.test_startup_all_harnesses_and_profile_do_not_prewarm

#!/usr/bin/env bash
# Slim retains native OMP profile dispatch, not retired routing overlays.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/tests/slim_distribution.py" Slim.test_startup_all_harnesses_and_profile_do_not_prewarm Slim.test_user_config_and_policy_text_survive

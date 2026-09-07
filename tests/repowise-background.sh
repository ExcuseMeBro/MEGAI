#!/usr/bin/env bash
# Retired background indexing cannot return through slim startup.
set -euo pipefail
ROOT="${MEGAI_TEST_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
exec python3 "$ROOT/tests/slim_distribution.py" Slim.test_startup_all_harnesses_and_profile_do_not_prewarm

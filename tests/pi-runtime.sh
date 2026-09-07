#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/tests/slim_distribution.py" Slim.test_startup_all_harnesses_and_profile_do_not_prewarm Slim.test_explicit_zvec_reindex_does_not_rebuild_codedb Slim.test_policy_guards_and_public_branch

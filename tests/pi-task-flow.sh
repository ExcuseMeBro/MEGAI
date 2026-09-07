#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/tests/slim_distribution.py" Slim.test_legacy_hooks_and_skills_require_manual_migration Slim.test_policy_guards_and_public_branch Slim.test_fresh_idempotent_and_ownership_removal

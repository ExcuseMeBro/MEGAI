#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/tests/slim_distribution.py" Slim.test_fresh_idempotent_and_ownership_removal Slim.test_user_config_and_policy_text_survive Slim.test_malformed_late_config_fails_before_any_write Slim.test_symlink_ancestor_and_custom_assets_preserved Slim.test_missing_search_and_unowned_proxy_fail

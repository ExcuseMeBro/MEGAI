#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/tests/slim_distribution.py" Slim.test_search_installer_pin_reuse_and_data_preservation Slim.test_explicit_zvec_reindex_does_not_rebuild_codedb Slim.test_missing_search_and_unowned_proxy_fail

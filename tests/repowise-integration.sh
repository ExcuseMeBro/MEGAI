#!/usr/bin/env bash
# RepoWise install/update/removal is retired; exercise actual dispatch offline.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
bash "$ROOT/tests/ui-craft-retirement.sh"

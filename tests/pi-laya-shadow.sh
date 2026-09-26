#!/usr/bin/env bash
set -euo pipefail
PI_PACKAGE_ROOT="$(dirname "$(dirname "$(dirname "$(realpath "$(command -v pi)")")")")"
export PI_PACKAGE_ROOT PI_OFFLINE=1
node tests/pi-laya-shadow.mjs

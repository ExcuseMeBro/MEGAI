#!/usr/bin/env bash
# Verification loads installed user extensions: never forward provider credentials.
set -euo pipefail
root="${MEGAI_HOME:-$HOME/.megai}"
exec env -i HOME="$HOME" PATH="${PATH:-/usr/bin:/bin}" MEGAI_HOME="$root" \
  PI_CODING_AGENT_DIR="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}" \
  PI_PACKAGE_ROOT="${PI_PACKAGE_ROOT:-}" PI_OFFLINE=1 \
  node "$root/lib/verify_headroom_activation.mjs" "$(command -v pi)"

#!/usr/bin/env bash
# Focused offline acceptance for the local Laya decision integration.
#
# Nothing here reaches a hosted service: the extension drives the real stdio bridge,
# the bridge imports a deterministic fake `laya` module, and the installer runs against
# a disposable HOME. The one real-checkpoint run lives in tests/pi-laya-live.sh.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# The suites must pass with no legacy credential or runtime variable set: that is the
# point of the migration. Drop any inherited ones so a stray shell export cannot make
# a test look green.
for name in $(env | sed -n 's/^\(LAYA_[A-Z_]*\)=.*/\1/p'); do
  unset "$name"
done

if [ -z "${PI_PACKAGE_ROOT:-}" ]; then
  for candidate in \
    "$HOME/.pi/agent/npm/node_modules/@earendil-works/pi-coding-agent" \
    "$HOME/.bun/install/global/node_modules/@earendil-works/pi-coding-agent" \
    "$(npm root -g 2>/dev/null || true)/@earendil-works/pi-coding-agent"; do
    if [ -n "$candidate" ] && [ -f "$candidate/dist/index.js" ]; then
      PI_PACKAGE_ROOT="$candidate"
      break
    fi
  done
fi
if [ -z "${PI_PACKAGE_ROOT:-}" ] || [ ! -f "$PI_PACKAGE_ROOT/dist/index.js" ]; then
  printf 'blocked: set PI_PACKAGE_ROOT to the installed @earendil-works/pi-coding-agent\n' >&2
  exit 2
fi
export PI_PACKAGE_ROOT

python3 -B tests/laya_bridge.py
python3 -B tests/laya_shadow.py
python3 -B tests/pi_laya_policy.py
python3 -B tests/pi_laya_runtime.py
node tests/pi-laya.mjs
node tests/pi-laya-sift.mjs
node tests/pi-laya-compaction.mjs
python3 -B tests/laya_active_scope.py

printf 'PASS: offline Laya integration suite (bridge protocol, ledger, installer wiring, '
printf 'owned runtime preparation, tool/gate/router/repair, sift, compaction, active scope)\n'

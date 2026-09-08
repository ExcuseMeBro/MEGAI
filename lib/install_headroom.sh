#!/usr/bin/env bash
# Pinned, hash-checked wheels in a Pi-private Python 3.14 runtime. No wrap/proxy.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
export MEGAI_HOME
MEGAI_SOURCE="${MEGAI_SOURCE:-$MEGAI_HOME}"
. "$MEGAI_SOURCE/lib/ui.sh"
. "$MEGAI_SOURCE/lib/state.sh"
clean_run() { env -i HOME="$HOME" MEGAI_HOME="$MEGAI_HOME" PATH="${PATH:-/usr/bin:/bin}" "$@"; }
command -v uv >/dev/null 2>&1 || die "uv required for isolated Headroom; install uv from https://docs.astral.sh/uv/ then retry"
clean_run python3 -I -B - "$MEGAI_HOME" <<'PY'
from pathlib import Path
import os
import sys
root=Path(sys.argv[1])
for destination in (root/'venv/headroom', root/'headroom-assets', root/'headroom-data'):
    for path in (destination, *destination.parents):
        if path.is_symlink() and path not in (Path('/tmp'), Path('/var')):
            raise SystemExit(f'unsafe Headroom destination: {path}')
    if destination.exists() and (not destination.is_dir() or destination.stat().st_uid != os.getuid()):
        raise SystemExit(f'unowned Headroom destination: {destination}')
PY
runtime="$MEGAI_HOME/venv/headroom"
lock="$MEGAI_SOURCE/pi-skill/headroom/requirements.txt"
if [ -e "$runtime" ]; then
  [ -f "$runtime/.megai-owned" ] && [ ! -L "$runtime/.megai-owned" ] && [ -O "$runtime/.megai-owned" ] && [ "$(<"$runtime/.megai-owned")" = megai-headroom-v1 ] || die "unowned Headroom runtime preserved: $runtime"
else
  umask 077
  clean_run uv venv --managed-python --python 3.14 "$runtime"
  printf 'megai-headroom-v1\n' >"$runtime/.megai-owned"
fi
clean_run "$runtime/bin/python" -I -B -c 'import sys; assert sys.version_info[:2] == (3,14)' || die "Headroom requires its managed Python 3.14 runtime; preserve/archive this runtime and reinstall"
# No source builds or lifecycle scripts. Repeated install verifies the exact lock.
clean_run uv pip sync --python "$runtime/bin/python" --require-hashes --only-binary=:all: "$lock"
clean_run "$runtime/bin/python" -I -B "$MEGAI_SOURCE/lib/prepare_headroom.py"
clean_run "$runtime/bin/python" -I -B "$MEGAI_SOURCE/pi-skill/headroom/bridge.py" doctor
if [ "${MEGAI_HEADROOM_PREPARE_ONLY:-0}" != 1 ]; then
  state_set '.tools.headroom' '{"installed":true,"version":"0.37.0","mode":"local-library"}'
fi
ok "Headroom 0.37.0 ready: offline compression/semantic memory, no proxy or effort routing"

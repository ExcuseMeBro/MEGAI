#!/usr/bin/env bash
# Offline token-profile acceptance: disposable HOME installer, real Pi loader, real RTK fixture.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
: "${PI_PACKAGE_ROOT:?set PI_PACKAGE_ROOT to the installed @earendil-works/pi-coding-agent package}"
: "${RTK_BIN:?set RTK_BIN to the existing rtk executable}"
export PI_PACKAGE_ROOT RTK_BIN RTK_TELEMETRY_DISABLED=1
[ -x "$RTK_BIN" ] || { echo "RTK_BIN is not executable: $RTK_BIN" >&2; exit 1; }

python3 -B "$ROOT/tests/pi_token_profile.py"
node "$ROOT/tests/token-profile-extension.mjs"
# Raw native tests, errors, reads, diffs and mutations stay uncompressed.
node "$ROOT/tests/headroom-extension.mjs"

# Same-directory listing comparison: isolated HOME/config/data, no real RTK state.
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/fixture" "$TMP/home" "$TMP/xdg-config" "$TMP/xdg-data"
entries=()
for index in $(seq 1 20); do
  name="entry-$index.txt"
  printf 'fixture content for %s\n' "$name" > "$TMP/fixture/$name"
  entries+=("$name")
done
python3 - "$RTK_BIN" "$TMP" "${entries[@]}" <<'PY'
import os
import subprocess
import sys
import time

rtk, tmp = sys.argv[1], sys.argv[2]
entries = sys.argv[3:]
directory = os.path.join(tmp, "fixture")
env = {**os.environ, "HOME": os.path.join(tmp, "home"),
       "XDG_CONFIG_HOME": os.path.join(tmp, "xdg-config"),
       "XDG_DATA_HOME": os.path.join(tmp, "xdg-data"),
       "RTK_TELEMETRY_DISABLED": "1"}
version = subprocess.run([rtk, "--version"], capture_output=True, text=True, env=env)
assert version.returncode == 0, version.stderr


def measure(command):
    started = time.perf_counter()
    result = subprocess.run(command, cwd=directory, capture_output=True, env=env)
    return result, time.perf_counter() - started


native, native_elapsed = measure(["ls", "-la"])
compact, compact_elapsed = measure([rtk, "ls"])
assert native.returncode == 0, native.stderr.decode()
assert compact.returncode == 0, compact.stderr.decode()
native_text, compact_text = native.stdout.decode(), compact.stdout.decode()
for entry in entries:
    assert entry in native_text, f"native ls -la missing {entry}"
    assert entry in compact_text, f"rtk ls missing {entry}"
print("sample-only same-directory listing fixture (20 files, not a token/bill/speed estimate): "
      f"{version.stdout.strip()}; native ls -la bytes={len(native.stdout)} elapsed={native_elapsed:.3f}s; "
      f"rtk ls bytes={len(compact.stdout)} elapsed={compact_elapsed:.3f}s; "
      f"all {len(entries)} entries present in both outputs")
PY

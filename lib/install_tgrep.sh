#!/usr/bin/env bash
# Pinned native CLI only: no hooks, indexing, server startup or user-tool replacement.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
export PATH="$PATH:$MEGAI_HOME/bin"
. "$MEGAI_HOME/lib/ui.sh"
. "$MEGAI_HOME/lib/state.sh"

# Reject malformed/unsafe state before downloading or publishing any executable.
python3 - "$MEGAI_HOME/lib" "$STATE_FILE" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from slim_wiring import safe
safe(Path(sys.argv[2]))
PY
state_init
jq -e '.tools == null or (.tools | type == "object")' "$STATE_FILE" >/dev/null || die "malformed MEGAI tools state"

if ! command -v tgrep >/dev/null 2>&1; then
  case "$(uname -s)/$(uname -m)" in
    Darwin/arm64) platform=aarch64-apple-darwin; expected=9ef13569d6725bb50497671506c914aaf6602fb0631810c8d100214498497ec8 ;;
    Darwin/x86_64) platform=x86_64-apple-darwin; expected=10c73c378d92c93f81d12706bc02c413c7626c4ed8f178ac0d23abd461bbd643 ;;
    Linux/aarch64|Linux/arm64) platform=aarch64-unknown-linux-musl; expected=8df6ab6ab6d859c38df3c6ee39c39bab66165761371a46a325021dd3c25607fb ;;
    Linux/x86_64) platform=x86_64-unknown-linux-musl; expected=81fd408f619fc1a316ed0618b2d2062b463631bdfd71123050580293817074fb ;;
    *) die "No pinned tgrep for this platform; provision trusted tgrep 1.0.4 or use rg" ;;
  esac
  target="$MEGAI_HOME/bin/tgrep"
  python3 - "$MEGAI_HOME/lib" "$target" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from slim_wiring import safe
safe(Path(sys.argv[2]))
PY
  [ ! -e "$target" ] && [ ! -L "$target" ] || die "Existing tgrep destination preserved; reconcile manually"
  mkdir -p "$MEGAI_HOME/bin"
  tmp="$(mktemp -d "$MEGAI_HOME/bin/.tgrep.XXXXXX")"
  trap 'rm -rf "$tmp"' EXIT
  curl --proto '=https' --proto-redir '=https' -fsSL --connect-timeout 10 --max-time 180 \
    "https://github.com/microsoft/tgrep/releases/download/v1.0.4/tgrep-v1.0.4-$platform.tar.gz" -o "$tmp/archive.tar.gz"
  python3 - "$MEGAI_HOME/lib" "$tmp" "$expected" "$target" <<'PY'
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tarfile

sys.path.insert(0, sys.argv[1])
from slim_wiring import safe

root, expected, target = Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
archive = root / "archive.tar.gz"
if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
    raise SystemExit("tgrep checksum mismatch; binary not installed")
with tarfile.open(archive, "r:gz") as bundle:
    matches = [member for member in bundle.getmembers() if Path(member.name).name == "tgrep"]
    if len(matches) != 1 or not matches[0].isfile() or not 0 < matches[0].size <= 100 * 1024 * 1024:
        raise SystemExit("invalid tgrep archive; expected one regular binary")
    # Read only that member into a fixed private path; never extract archive paths/links.
    binary = root / "tgrep"
    binary.write_bytes(bundle.extractfile(matches[0]).read())
    binary.chmod(0o700)
version = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=10)
if version.returncode or version.stdout.strip() != "tgrep 1.0.4":
    raise SystemExit("downloaded tgrep failed identity verification")
safe(target)
os.link(binary, target)  # Atomic publication, never overwrite a concurrent/user destination.
PY
  hash -r
fi
bin="$(command -v tgrep)"
version="$(tgrep --version)" || die "tgrep identity check failed; existing executable preserved"
[ "$version" = "tgrep 1.0.4" ] || die "Expected tgrep 1.0.4; existing executable preserved, use rg until reconciled"
state_set '.tools.tgrep' "$(jq -cn --arg bin "$bin" --arg version "$version" '{bin:$bin,version:$version}')"
ok "tgrep ready -> $bin; indexing and servers remain on demand, rg remains the correctness fallback"

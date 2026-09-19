#!/usr/bin/env bash
# jevcache: the pinned decision-cache CLI (hyperspaceai/jevcache v0.1.0). An optional
# tool, deliberately not in the Jev gate path (docs/jevcache.md). Fail-soft: every
# failure warns and exits 0, so a network problem never breaks a profile install.
set -uo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
export PATH="$PATH:$MEGAI_HOME/bin"
. "$MEGAI_HOME/lib/ui.sh"
. "$MEGAI_HOME/lib/state.sh"

skip() { warn "jevcache: $*"; exit 0; }

if command -v jevcache >/dev/null 2>&1; then
  ok "jevcache already installed -> $(command -v jevcache); left untouched"
  exit 0
fi

# Reject malformed or unsafe state before downloading or publishing any executable.
python3 - "$MEGAI_HOME/lib" "$STATE_FILE" <<'PY' || skip "unsafe or malformed MEGAI state"
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from slim_wiring import safe
safe(Path(sys.argv[2]))
PY
state_init || skip "cannot initialize MEGAI state"
jq -e '.tools == null or (.tools | type == "object")' "$STATE_FILE" >/dev/null || skip "malformed MEGAI tools state"

case "$(uname -s)/$(uname -m)" in
  Darwin/arm64)   asset=jevcache-darwin-arm64; expected=68fcb95b908cf3ee73dbeb3df52b265f6b908a6a9cfd661c5c6429d32f7535d5 ;;
  Darwin/x86_64)  asset=jevcache-darwin-x64;   expected=5612766cd839e0020fd260f4eec6c991d8a0b3b8e1b1d226e1783098ed71d338 ;;
  Linux/aarch64|Linux/arm64) asset=jevcache-linux-arm64; expected=11c344b7b0f9084c1cd94db861663871cba39efe3ace2ce80850f267841f06c9 ;;
  Linux/x86_64)   asset=jevcache-linux-x64;    expected=0e20e605f17219ce64979ae5b67cc33609aba5e1425426d01c9011c652263aa7 ;;
  *) skip "no pinned binary for $(uname -s)/$(uname -m)" ;;
esac

target="$MEGAI_HOME/bin/jevcache"
{ [ ! -e "$target" ] && [ ! -L "$target" ]; } || skip "existing $target preserved; remove it by hand to reinstall"
mkdir -p "$MEGAI_HOME/bin" || skip "cannot create $MEGAI_HOME/bin"
tmp="$(mktemp -d "$MEGAI_HOME/bin/.jevcache.XXXXXX")" || skip "cannot create a temporary directory"
trap 'rm -rf "$tmp"' EXIT

curl --proto '=https' --proto-redir '=https' -fsSL --connect-timeout 10 --max-time 180 \
  "https://github.com/hyperspaceai/jevcache/releases/download/v0.1.0/$asset" -o "$tmp/jevcache" \
  || skip "download failed; nothing installed"

# The pinned digest is the identity. It was copied from the release's own .sha256
# assets when v0.1.0 was adopted and is now a literal here — nothing is fetched at
# install time — so a swapped or truncated download never reaches PATH.
python3 - "$MEGAI_HOME/lib" "$tmp/jevcache" "$expected" "$target" <<'PY' || skip "checksum or destination check failed; nothing installed"
import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from slim_wiring import safe

binary, expected, target = Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
if not binary.is_file() or hashlib.sha256(binary.read_bytes()).hexdigest() != expected:
    raise SystemExit("jevcache checksum mismatch; binary not installed")
binary.chmod(0o700)
safe(target)
os.link(binary, target)  # Atomic publication, never overwrite a concurrent/user destination.
PY

version="v0.1.0"
state_set '.tools.jevcache' "$(jq -cn --arg bin "$target" --arg version "$version" '{bin:$bin,version:$version}')"
ok "jevcache $version ready -> $target (checksum verified); not wired into the Jev gate, see docs/jevcache.md"

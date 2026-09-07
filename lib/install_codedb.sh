#!/usr/bin/env bash
# Install only the pinned CLI binary: no upstream hooks, MCP registration or indexing.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
export PATH="$PATH:$MEGAI_HOME/bin"
. "$MEGAI_HOME/lib/ui.sh"
. "$MEGAI_HOME/lib/state.sh"
state_init

if ! command -v codedb >/dev/null 2>&1; then
  case "$(uname -s)/$(uname -m)" in
    Darwin/arm64) asset=codedb-darwin-arm64; expected=f916d0aa16eafaa850ca8c94af6771a1b2d85877cdffed7b23937466cd706522 ;;
    Linux/x86_64) asset=codedb-linux-x86_64; expected=b76caa6972a19ece1a9e107df01ff45c1a285524f3c9fc2adf19da2aa5bf381b ;;
    *) die "No pinned codedb binary for this platform; provision a trusted codedb CLI before retrying" ;;
  esac
  target="$MEGAI_HOME/bin/codedb"
  python3 - "$MEGAI_HOME/lib" "$target" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from slim_wiring import safe
safe(Path(sys.argv[2]))
PY
  [ ! -e "$target" ] && [ ! -L "$target" ] || die "Existing codedb destination preserved; reconcile manually"
  mkdir -p "$MEGAI_HOME/bin"
  tmp="$(mktemp "$MEGAI_HOME/bin/.codedb.XXXXXX")"
  trap 'rm -f "$tmp"' EXIT
  curl --proto '=https' --proto-redir '=https' -fsSL --connect-timeout 10 --max-time 180 \
    "https://github.com/justrach/codedb/releases/download/v0.2.56/$asset" -o "$tmp"
  python3 - "$tmp" "$expected" <<'PY'
import hashlib, sys
from pathlib import Path
if hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest() != sys.argv[2]:
    raise SystemExit('codedb checksum mismatch; binary not installed')
PY
  chmod 700 "$tmp"
  ln "$tmp" "$target" # atomic, no overwrite of concurrent/user assets
  rm -f "$tmp"
  trap - EXIT
  hash -r
fi
bin="$(command -v codedb)"
ver="$(codedb --version)" || die "codedb version check failed"
[[ "$ver" == codedb\ * ]] || die "codedb returned invalid version output"
state_set '.tools["codedb"]' "$(jq -cn --arg bin "$bin" --arg version "$ver" '{bin:$bin,version:$version}')"
ok "codedb ready -> $bin; indexes remain on demand"

#!/usr/bin/env bash
# Reuse a working rtk-ai CLI; fresh installs use a checked upstream installer.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
. "$MEGAI_HOME/lib/ui.sh"
. "$MEGAI_HOME/lib/state.sh"
if ! command -v rtk >/dev/null 2>&1; then
  target="$MEGAI_HOME/bin/rtk"
  [ ! -e "$target" ] && [ ! -L "$target" ] || die "rtk destination exists off PATH; reconcile $target"
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/5a7880d404db8364d602f2ecdc41dd790f64013f/install.sh -o "$tmp/install.sh"
  python3 - "$tmp/install.sh" <<'PY'
import hashlib,sys
from pathlib import Path
assert hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest() == 'd6eb73a772903e13ff34ee1be8a8b24e896ba9a978f20d2279a08b4083ea6f77', 'rtk installer checksum mismatch'
PY
  RTK_VERSION=v0.43.0 RTK_SKIP_CHECKSUM=0 RTK_INSTALL_DIR="$tmp/bin" sh "$tmp/install.sh"
  "$tmp/bin/rtk" gain >/dev/null || die "downloaded rtk failed identity verification"
  mkdir -p "$MEGAI_HOME/bin"
  mv "$tmp/bin/rtk" "$target"
  export PATH="$MEGAI_HOME/bin:$PATH"
fi
rtk gain >/dev/null 2>&1 || die "rtk identity ambiguous; existing executable preserved"
bin="$(command -v rtk)"
version="$(rtk --version)"
state_set '.tools.rtk' "$(jq -cn --arg bin "$bin" --arg version "$version" '{bin:$bin,version:$version}')"
ok "rtk ready; no automatic global hooks installed"

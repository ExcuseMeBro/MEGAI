#!/bin/bash
# safe-anything guard: the only way agents run the scanner on this Mac. Installed as ~/.local/bin/safe-anything.
# 1. Verifies the pinned release binary's SHA-256 before every run (refuses a stale or replaced binary).
# 2. Forces --offline (no package names to OSV.dev) unless SAFE_ANYTHING_ONLINE=1 is set for that one command,
#    which an agent may do only after the user agreed in the conversation.
# Binary: erkamyaman/safe-anything v1.0.2, aarch64-apple-darwin release tarball (SHA256SUMS-verified at install), MIT.
set -u
VERSION="1.0.2"
BIN="${SAFE_ANYTHING_BIN:-$HOME/.local/lib/safe-anything/$VERSION/safe-anything}"
PINNED="bf128f1496863b9d67da224822f11a72ddd6ca5e2c8257d12c24399e965c2e46"

[ -f "$BIN" ] && [ ! -L "$BIN" ] || { echo "safe-anything guard: scanner binary missing at $BIN (scan: unavailable)" >&2; exit 3; }
actual="$(shasum -a 256 "$BIN" | awk '{print $1}')"
[ "$actual" = "$PINNED" ] || { echo "safe-anything guard: binary digest mismatch, refusing to run (scan: unavailable)" >&2; exit 3; }

case " $* " in
  *" mcp "*) echo "safe-anything guard: MCP mode is not enabled on this Mac; use the CLI." >&2; exit 3 ;;
esac
if [ "${SAFE_ANYTHING_ONLINE:-}" = "1" ]; then exec "$BIN" "$@"; fi
case " $* " in
  *" --offline "*|*" --version "*|*" -V "*|*" --help "*|*" -h "*|*" --list-rules "*) exec "$BIN" "$@" ;;
  *) exec "$BIN" "$@" --offline ;;
esac

#!/bin/bash
# safe-anything guard: the only way agents run the scanner on this Mac. Installed as ~/.local/bin/safe-anything.
# - Copies the pinned release binary into a private temp folder, verifies the copy's SHA-256 with /usr/bin/shasum and
#   runs exactly those verified bytes (no PATH lookups, no swap between check and launch).
# - Every scan gets --offline (no package names to OSV.dev) unless the first argument is --online, which an agent may
#   pass only after the user agreed in the current conversation. `--online` is consumed by the guard.
# - MCP mode is refused.
# Binary: erkamyaman/safe-anything v1.0.2, aarch64-apple-darwin release tarball (SHA256SUMS-verified at install), MIT.
set -u
export PATH=/usr/bin:/bin
VERSION="1.0.2"
PINNED="bf128f1496863b9d67da224822f11a72ddd6ca5e2c8257d12c24399e965c2e46"
BIN="${SAFE_ANYTHING_BIN:-$HOME/.local/lib/safe-anything/$VERSION/safe-anything}"
fail() { echo "safe-anything guard: $1 (scan: unavailable)" >&2; exit 3; }

case "$BIN" in /*) ;; *) fail "SAFE_ANYTHING_BIN must be an absolute path" ;; esac
[ -f "$BIN" ] && [ ! -L "$BIN" ] || fail "scanner binary missing at $BIN"

online=0
if [ "${1:-}" = "--online" ]; then online=1; shift; fi
[ "${1:-}" = "mcp" ] && fail "MCP mode is not enabled on this Mac; use the CLI"

# Metadata-only calls are the exact single flags below; everything else is a scan and gets --offline.
meta=0
if [ $# -eq 1 ]; then case "$1" in --version|-V|--help|-h|--list-rules) meta=1 ;; esac; fi
has_offline=0
for a in "$@"; do [ "$a" = "--offline" ] && has_offline=1; done

stage="$(/usr/bin/mktemp -d "${TMPDIR:-/tmp}/safe-anything.XXXXXX")" || fail "cannot create a private temp folder"
trap '/bin/rm -rf "$stage"' EXIT
/bin/cp "$BIN" "$stage/safe-anything" || fail "cannot stage the binary"
/bin/chmod 500 "$stage/safe-anything"
actual="$(/usr/bin/shasum -a 256 "$stage/safe-anything" 2>/dev/null)" || fail "cannot hash the binary"
[ "${actual%% *}" = "$PINNED" ] || fail "binary digest mismatch, refusing to run"

if [ "$meta" = 1 ] || [ "$online" = 1 ] || [ "$has_offline" = 1 ]; then "$stage/safe-anything" "$@"; else "$stage/safe-anything" "$@" --offline; fi

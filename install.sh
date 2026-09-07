#!/usr/bin/env bash
# MEGAI installer — zero-config AI agent stack bundle
# Usage:  curl -fsSL https://raw.githubusercontent.com/ExcuseMeBro/MEGAI/slim/install.sh | bash
set -euo pipefail

MEGAI_REPO="${MEGAI_REPO:-ExcuseMeBro/MEGAI}"
# The public installer is intentionally pinned to the slim distribution. Set
# MEGAI_REF explicitly when adopting another branch by choice.
MEGAI_REF="${MEGAI_REF:-slim}"
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
MEGAI_TARBALL="https://codeload.github.com/${MEGAI_REPO}/tar.gz/refs/heads/${MEGAI_REF}"

c_blue=$'\033[34m'; c_grn=$'\033[32m'; c_red=$'\033[31m'; c_dim=$'\033[2m'; c_off=$'\033[0m'
say()  { printf "%s[megai]%s %s\n"   "$c_blue" "$c_off" "$*"; }
ok()   { printf "%s  ✓%s %s\n"        "$c_grn"  "$c_off" "$*"; }
warn() { printf "%s  !%s %s\n"        "$c_red"  "$c_off" "$*" >&2; }
die()  { warn "$*"; exit 1; }

[ -t 1 ] || { c_blue=""; c_grn=""; c_red=""; c_dim=""; c_off=""; }

# inline mini-banner (full banner lives in lib/banner.sh, but install.sh runs before lib is on disk)
if [ -t 1 ]; then printf '\033[97m'; fi
cat <<'BNR'

███╗   ███╗███████╗ ██████╗  █████╗ ██╗
████╗ ████║██╔════╝██╔════╝ ██╔══██╗██║
██╔████╔██║█████╗  ██║  ███╗███████║██║
██║╚██╔╝██║██╔══╝  ██║   ██║██╔══██║██║
██║ ╚═╝ ██║███████╗╚██████╔╝██║  ██║██║
╚═╝     ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝
BNR
if [ -t 1 ]; then printf '\033[0m\033[2;37m'; fi
printf '   THE ZERO-CONFIG AI AGENT STACK\n\n'
if [ -t 1 ]; then printf '\033[0m'; fi

say "MEGAI installer starting"
say "target: $MEGAI_HOME"

# 1. download repo tarball
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
say "fetching $MEGAI_TARBALL"
curl -fsSL "$MEGAI_TARBALL" | tar -xz -C "$tmp" --strip-components=1
ok "source extracted -> $tmp"

# 2. Fail migration conflicts before replacing even the distribution source.
export MEGAI_HOME PYTHONDONTWRITEBYTECODE=1
python3 -c 'import tomllib' || die "Python 3.11+ required"
MEGAI_SOURCE="$tmp" python3 "$tmp/lib/slim_wiring.py" pi --check
python3 "$tmp/lib/install_slim_source.py" "$tmp"
ok "source installed with private recovery manifest"

# 3. run main pipeline; retaining the shell ensures the temporary source is cleaned.
bash "$MEGAI_HOME/lib/main.sh"

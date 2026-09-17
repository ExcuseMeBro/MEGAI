#!/usr/bin/env bash
# MEGAI installer — zero-config AI agent stack bundle
# Usage:  curl -fsSL https://raw.githubusercontent.com/ExcuseMeBro/MEGAI/main/install.sh | bash
set -euo pipefail

MEGAI_REPO="${MEGAI_REPO:-ExcuseMeBro/MEGAI}"
# This installer belongs to the persistent pi branch.
MEGAI_REF="${MEGAI_REF:-pi}"
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

# 2. The pi branch installs the clean profile without legacy recovery/wiring.
# Reset is explicit because it destroys Pi authentication and session history.
export PYTHONDONTWRITEBYTECODE=1
args=()
[ "${MEGAI_PI_RESET:-0}" != 1 ] || args+=(--reset)
[ "${MEGAI_REMOVE_OMP:-0}" != 1 ] || args+=(--remove-omp)
python3 "$tmp/pi-defaults/install.py" "${args[@]}"
ok "Pi defaults installed (no backups)"

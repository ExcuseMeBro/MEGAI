#!/usr/bin/env bash
# colored output + progress helpers
# shellcheck disable=SC2034

if [ -t 1 ]; then
  C_BLUE=$'\033[34m'; C_GRN=$'\033[32m'; C_RED=$'\033[31m'
  C_YEL=$'\033[33m'; C_DIM=$'\033[2m';  C_OFF=$'\033[0m'
else
  C_BLUE=""; C_GRN=""; C_RED=""; C_YEL=""; C_DIM=""; C_OFF=""
fi

say()  { printf "%s[megai]%s %s\n" "$C_BLUE" "$C_OFF" "$*"; }
ok()   { printf "%s  ✓%s %s\n"      "$C_GRN"  "$C_OFF" "$*"; }
skip() { printf "%s  -%s %s\n"      "$C_DIM"  "$C_OFF" "$*"; }
warn() { printf "%s  !%s %s\n"      "$C_YEL"  "$C_OFF" "$*" >&2; }
err()  { printf "%s  ✗%s %s\n"      "$C_RED"  "$C_OFF" "$*" >&2; }
die()  { err "$*"; exit 1; }

step() {
  local n="$1" tot="$2" msg="$3"
  printf "%s[%d/%d]%s %s\n" "$C_BLUE" "$n" "$tot" "$C_OFF" "$msg"
}

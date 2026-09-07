#!/usr/bin/env bash
# Retired background indexing cannot return through either startup mode.
set -euo pipefail
ROOT="${MEGAI_TEST_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home" MEGAI_HOME="$TMP/megai" CALLS="$TMP/calls"
mkdir -p "$HOME" "$MEGAI_HOME/lib"
cp -R "$ROOT/lib/." "$MEGAI_HOME/lib/"
printf '#!/bin/sh\nexit 0\n' > "$MEGAI_HOME/lib/ensure_dev.sh"
source "$ROOT/bin/megai" --help >/dev/null
state_init() { :; }
is_project_initialized() { return 1; }
mark_project_active() { :; }
ensure_agent_memory() { echo memory >> "$CALLS"; }
ensure_codedb_index() { echo codedb >> "$CALLS"; }
ensure_zvec_index() { echo zvec >> "$CALLS"; }
ensure_graphify_bg() { echo graphify >> "$CALLS"; }
ensure_repowise_bg() { echo repowise >> "$CALLS"; }
check_caveman() { :; }
check_rtk() { :; }
: > "$CALLS"
MEGAI_SPECIALIST_INDEXES=0 prepare_stack > "$TMP/default.out"
[ "$(< "$CALLS")" = $'memory\ncodedb\nzvec' ]
: > "$CALLS"
MEGAI_SPECIALIST_INDEXES=1 prepare_stack > "$TMP/full.out"
[ "$(< "$CALLS")" = $'memory\ncodedb\nzvec\ngraphify' ]
if grep -qi repowise "$TMP/default.out" "$TMP/full.out"; then exit 1; fi
echo 'RepoWise background retirement PASS; core indexing and opt-in graphify preserved'

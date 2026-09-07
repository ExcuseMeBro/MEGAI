#!/usr/bin/env bash
# Reuse installed search; never upgrade or initialize indexes implicitly.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
. "$MEGAI_HOME/lib/ui.sh"
. "$MEGAI_HOME/lib/state.sh"
command -v node >/dev/null 2>&1 && node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 22 ? 0 : 1)' || die "zvec-grep requires Node.js 22+"
if ! command -v zg >/dev/null 2>&1; then
  npm install -g --ignore-scripts @zvec/zvec-grep@0.2.1 || die "zvec-grep install failed"
fi
bin="$(command -v zg)" || die "zg missing after install"
version="$("$bin" version)" || die "zg version check failed"
[ -n "$version" ] || die "zg returned no version"
state_set '.tools["zvec-grep"]' "$(jq -cn --arg bin "$bin" --arg version "$version" '{bin:$bin,version:$version}')"
ok "zvec-grep ready; existing indexes and unrelated installations preserved"

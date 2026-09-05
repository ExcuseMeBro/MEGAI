#!/usr/bin/env bash
# caveman — token-compression skill that self-installs into Claude Code / Codex / Pi / Cursor.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

# Compression is optional; the core engineering policy already requires concise,
# scoped work. Do not force-install another always-triggered skill/hook layer.
if [ "${MEGAI_CAVEMAN:-0}" != "1" ]; then
  skip "caveman is optional (MEGAI_CAVEMAN=1 to install); existing files preserved"
  exit 0
fi

if ! command -v caveman >/dev/null 2>&1; then
  npm install -g 'github:JuliusBrussee/caveman#v2.2.0' \
    || { warn "caveman installer package failed (non-fatal)"; exit 0; }
fi

# Install from HOME so the skills CLI selects the global ~/.agents/skills
# target instead of whichever repository happened to launch MEGAI.
(cd "$HOME" && caveman --force --non-interactive) \
  || { warn "caveman agent wiring failed (non-fatal)"; exit 0; }
ok "caveman installed -> $(command -v caveman)"

bin="$(command -v caveman || echo "")"
ver="$(npm list -g caveman-installer --depth=0 --json 2>/dev/null | jq -r '.dependencies["caveman-installer"].version // empty')"
state_set '.tools["caveman"]' "{\"bin\":\"$bin\",\"version\":\"$ver\"}"

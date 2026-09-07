#!/usr/bin/env bash
# Default core Caveman skill only; no force-wiring, hooks or workflow bundles.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
. "$MEGAI_HOME/lib/ui.sh"
. "$MEGAI_HOME/lib/state.sh"
if [ "${MEGAI_CAVEMAN:-1}" != "1" ]; then
  skip "caveman disabled (MEGAI_CAVEMAN=0); existing files preserved"
  exit 0
fi
if ! command -v caveman >/dev/null 2>&1; then
  npm install -g --ignore-scripts --no-audit --no-fund 'github:JuliusBrussee/caveman#v2.2.0' \
    || { warn "caveman package install failed — skipped"; exit 0; }
  hash -r
fi
skill="$HOME/.agents/skills/caveman/SKILL.md"
if [ ! -f "$skill" ]; then
  if [ -e "$skill" ] || [ -L "$skill" ] || [ -L "$(dirname "$skill")" ]; then
    warn "caveman: preserving existing non-file/linked destination"
    exit 0
  fi
  packaged="$(npm root -g)/caveman-installer/skills/caveman/SKILL.md"
  [ -f "$packaged" ] || { warn "caveman core skill missing from package — skipped"; exit 0; }
  mkdir -p "$(dirname "$skill")"
  cp "$packaged" "$skill"
fi
# Reuse existing skill content. Never invoke the all-agent upstream installer.
bin="$(command -v caveman || true)"
ver=""
if command -v npm >/dev/null 2>&1; then
  ver="$(npm list -g caveman-installer --depth=0 --json 2>/dev/null | jq -r '.dependencies["caveman-installer"].version // empty' || true)"
fi
metadata="$(jq -cn --arg bin "$bin" --arg version "$ver" --arg skill "$skill" '{bin:$bin,version:$version,skill:$skill}')"
state_set '.tools.caveman' "$metadata"
ok "caveman core ready; MEGAI_CAVEMAN=0 opts out; existing skill preserved"

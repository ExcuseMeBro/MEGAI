#!/usr/bin/env bash
# zvec-grep — local-first hybrid workspace search for humans and agents.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

if ! command -v node >/dev/null 2>&1 || ! node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 22 ? 0 : 1)' 2>/dev/null; then
  warn "zvec-grep requires Node.js 22+ — skipped"
  exit 0
fi
if ! command -v npm >/dev/null 2>&1; then
  warn "npm missing — zvec-grep skipped"
  exit 0
fi

if [ "${MEGAI_UPDATE:-0}" = "1" ]; then
  npm install -g @zvec/zvec-grep@latest >/dev/null 2>&1 \
    || { warn "zvec-grep update failed — keeping current version"; }
elif ! command -v zg >/dev/null 2>&1; then
  npm install -g @zvec/zvec-grep@latest >/dev/null 2>&1 \
    || { warn "zvec-grep install failed — skipping"; exit 0; }
else
  ok "zvec-grep already installed -> $(command -v zg)"
fi

hash -r
bin="$(command -v zg || true)"
[ -n "$bin" ] && [ -x "$bin" ] || { warn "zvec-grep installed but zg was not found"; exit 0; }
target="$MEGAI_HOME/bin/zg"
mkdir -p "$MEGAI_HOME/bin"
if [ "$bin" != "$target" ]; then
  ln -sf "$bin" "$target"
fi
ver="$("$target" version 2>/dev/null | head -n1 || true)"
state_set '.tools["zvec-grep"]' "{\"bin\":\"$target\",\"version\":\"${ver:-unknown}\"}"

# CocoIndex is no longer MEGAI-managed. Remove only MEGAI-owned artifacts;
# preserve any independently installed pipx or system package.
rm -f "$MEGAI_HOME/bin/cocoindex" "$MEGAI_HOME/lib/install_cocoindex.sh"
rm -rf "$MEGAI_HOME/venv/cocoindex"
if [ -f "$STATE_FILE" ]; then
  tmp="$(mktemp)"
  jq 'del(.tools.cocoindex)' "$STATE_FILE" >"$tmp" && mv "$tmp" "$STATE_FILE"
fi
ok "zvec-grep ready -> $bin"

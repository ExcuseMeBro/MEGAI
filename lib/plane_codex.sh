#!/usr/bin/env bash
# Secure Codex Plane MCP lifecycle. Called by plane_mcp.sh; never handles tokens in argv.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
. "$MEGAI_HOME/lib/ui.sh"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
CONFIG="$CODEX_HOME/config.toml"
HELPER="$MEGAI_HOME/lib/plane_mcp_remote.py"
BEGIN="# >>> megai-plane-managed (do not edit) >>>"
END="# <<< megai-plane-managed <<<"

validate_config() {
  [ ! -L "$CONFIG" ] || die "refusing symlinked Codex config: $CONFIG"
  [ ! -e "$CONFIG" ] || [ -f "$CONFIG" ] || die "Codex config is not a regular file: $CONFIG"
  [ ! -e "$CONFIG" ] && return 0
  python3 - "$CONFIG" <<'PY'
import sys
from pathlib import Path
try:
    import tomllib
    tomllib.loads(Path(sys.argv[1]).read_text())
except (OSError, UnicodeDecodeError, ValueError):
    raise SystemExit(1)
PY
  [ "$?" -eq 0 ] || die "invalid Codex TOML config; no changes made: $CONFIG"
}

has_section() { grep -Eq '^\[mcp_servers\.(plane|"plane")\]$' "$CONFIG"; }

strip_plane() {
  awk -v b="$BEGIN" -v e="$END" '
    $0 == b { skip=1; next }
    skip && $0 == e { skip=0; next }
    !skip { print }
  ' "$CONFIG"
}
strip_asana() {
  awk '
    /^[[]mcp_servers[.](asana|"asana")(\.|])/ { drop=1; next }
    /^\[[^]]+\][[:space:]]*$/ { drop=0 }
    !drop { print }
  '
}
render_entry() {
  local token_file="$1" workspace="$2"
  python3 - "$HELPER" "$token_file" "$workspace" <<'PY'
import json
import sys
helper, token_file, workspace = sys.argv[1:]
print("[mcp_servers.plane]")
print(f"command = {json.dumps(helper)}")
print(f"args = [{json.dumps('--token-file')}, {json.dumps(token_file)}, {json.dumps('--workspace')}, {json.dumps(workspace)}]")
PY
}
backup() {
  local target="$1" out
  mkdir -p "$MEGAI_HOME/backups"
  chmod 700 "$MEGAI_HOME/backups"
  out="$(mktemp "$MEGAI_HOME/backups/codex-plane-mcp.toml.bak.XXXXXX")"
  cp -- "$target" "$out"
  chmod 600 "$out"
}
private() {
  local mode
  mode="$(stat -c '%a' "$1" 2>/dev/null || stat -f '%Lp' "$1")"
  [ $((0$mode & 077)) -eq 0 ]
}
setup() {
  local workspace="$1" token_file="$2" replace="$3" candidate
  validate_config
  mkdir -p "$CODEX_HOME"
  if has_section && ! grep -Fq "$BEGIN" "$CONFIG"; then
    die "existing Codex MCP server 'plane' is user-owned; refusing to replace it"
  fi
  python3 "$HELPER" --check --token-file "$token_file" --workspace "$workspace" >/dev/null 2>&1 \
    || die "Plane token file is missing, empty, or unsafe"
  candidate="$(mktemp "$CODEX_HOME/config.toml.XXXXXX")"
  if [ -f "$CONFIG" ]; then
    strip_plane "$CONFIG" | {
      if [ "$replace" = 1 ]; then strip_asana; else cat; fi
      printf '%s\n' "$BEGIN"
      render_entry "$token_file" "$workspace"
      printf '%s\n' "$END"
    } >"$candidate"
  else
    {
      printf '%s\n' "$BEGIN"
      render_entry "$token_file" "$workspace"
      printf '%s\n' "$END"
    } >"$candidate"
  fi
  if [ ! -f "$CONFIG" ] || ! cmp -s "$CONFIG" "$candidate"; then
    [ -f "$CONFIG" ] && backup "$CONFIG"
    chmod 600 "$candidate"
    mv "$candidate" "$CONFIG"
    ok "Plane Codex MCP configured (workspace=$workspace)"
  else
    rm -f "$candidate"
    private "$CONFIG" || { backup "$CONFIG"; chmod 600 "$CONFIG"; }
    ok "Plane Codex MCP already configured (workspace=$workspace)"
  fi
}

status() {
  validate_config
  if ! has_section; then echo 'Plane Codex MCP: not configured'; return 0; fi
  grep -Fq "$BEGIN" "$CONFIG" || { echo 'Plane Codex MCP: unmanaged entry preserved' >&2; return 1; }
  echo 'Plane Codex MCP: configured (credential checked at launch)'
}

remove() {
  validate_config
  [ -f "$CONFIG" ] || { echo 'Plane Codex MCP: not configured'; return 0; }
  has_section || { echo 'Plane Codex MCP: not configured'; return 0; }
  grep -Fq "$BEGIN" "$CONFIG" || die "existing Codex MCP server 'plane' is user-owned; refusing to remove it"
  backup "$CONFIG"
  strip_plane >"$CODEX_HOME/config.toml.tmp"
  chmod 600 "$CODEX_HOME/config.toml.tmp"
  mv "$CODEX_HOME/config.toml.tmp" "$CONFIG"
  ok 'Plane Codex MCP removed'
}

restore() {
  local source
  source="$(ls -t "$MEGAI_HOME"/backups/codex-plane-mcp.toml.bak.* 2>/dev/null | head -n1 || true)"
  [ -n "$source" ] || die 'Plane Codex restore: no private backup found'
  [ ! -L "$CONFIG" ] || die "refusing symlinked restore target: $CONFIG"
  mkdir -p "$CODEX_HOME"
  cp -- "$source" "$CODEX_HOME/config.toml.tmp"
  chmod 600 "$CODEX_HOME/config.toml.tmp"
  mv "$CODEX_HOME/config.toml.tmp" "$CONFIG"
  ok 'Plane Codex restored from private backup'
}

case "${1:-}" in
  setup) [ "$#" -eq 4 ] || die 'usage: plane_codex setup WORKSPACE TOKEN_FILE REPLACE'; setup "$2" "$3" "$4" ;;
  status) status ;;
  remove) remove ;;
  restore) restore ;;
  *) die 'invalid Plane Codex action' ;;
esac

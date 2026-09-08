#!/usr/bin/env bash
# Secure Codex Plane MCP lifecycle. Tokens are read from private files, never argv/logs.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
. "$MEGAI_HOME/lib/ui.sh"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
CONFIG="$CODEX_HOME/config.toml"
HELPER="$MEGAI_HOME/lib/plane_mcp_remote.py"
CONFIG_TOOL="$MEGAI_HOME/lib/plane_codex_config.py"
BACKUP_TOOL="$MEGAI_HOME/lib/plane_backup.py"
BEGIN="# >>> megai-plane-managed (do not edit) >>>"
END="# <<< megai-plane-managed <<<"

validate_config() {
  [ ! -L "$CONFIG" ] || die "refusing symlinked Codex config: $CONFIG"
  [ ! -e "$CONFIG" ] || [ -f "$CONFIG" ] || die "Codex config is not a regular file: $CONFIG"
  [ ! -e "$CONFIG" ] && return 0
  python3 "$CONFIG_TOOL" validate --file "$CONFIG" >/dev/null \
    || die "invalid Codex TOML config; no changes made: $CONFIG"
}

config_kind() {
  [ -f "$CONFIG" ] || { echo missing; return; }
  python3 "$CONFIG_TOOL" inspect --file "$CONFIG" --begin "$BEGIN" --end "$END" --helper "$HELPER"
}

private() {
  local mode
  mode="$(stat -c '%a' "$1" 2>/dev/null || stat -f '%Lp' "$1")"
  [ $((0$mode & 077)) -eq 0 ]
}

render_candidate() {
  local workspace="$1" token_file="$2" replace="$3" candidate="$4" kind base stripped
  kind="$(config_kind)"
  [ "$kind" != unmanaged ] || die "existing Codex MCP server 'plane' is user-owned or has invalid markers; refusing to replace it"
  base="$(mktemp "${candidate}.base.XXXXXX")"
  stripped="$(mktemp "${candidate}.strip.XXXXXX")"
  trap 'rm -f -- "$base" "$stripped"' RETURN
  if [ "$kind" = owned ]; then
    python3 "$CONFIG_TOOL" strip-managed --file "$CONFIG" --begin "$BEGIN" --end "$END" >"$base"
  elif [ -f "$CONFIG" ]; then
    cp -- "$CONFIG" "$base"
  else
    : >"$base"
  fi
  if [ "$replace" = 1 ] && [ -s "$base" ]; then
    python3 "$CONFIG_TOOL" strip-servers --file "$base" --server asana >"$stripped"
    cp -- "$stripped" "$base"
  fi
  {
    cat -- "$base"
    if [ -s "$base" ] && [ "$(tail -c 1 "$base" | od -An -t x1 | tr -d '[:space:]')" != 0a ]; then printf '\n'; fi
    printf '%s\n' "$BEGIN"
    python3 - "$HELPER" "$token_file" "$workspace" <<'PY'
import json
import sys
helper, token_file, workspace = sys.argv[1:]
print("[mcp_servers.plane]")
print(f"command = {json.dumps(helper)}")
print(f"args = [{json.dumps('--token-file')}, {json.dumps(token_file)}, {json.dumps('--workspace')}, {json.dumps(workspace)}]")
PY
    printf '%s\n' "$END"
  } >"$candidate"
  chmod 600 "$candidate"
  python3 "$CONFIG_TOOL" validate --file "$candidate" >/dev/null \
    || die "generated Codex TOML failed validation"
  [ "$(python3 "$CONFIG_TOOL" inspect --file "$candidate" --begin "$BEGIN" --end "$END" --helper "$HELPER")" = owned ] \
    || die "generated Codex TOML failed ownership validation"
  rm -f -- "$base" "$stripped"
  trap - RETURN
}

stage_setup() {
  local workspace="$1" token_file="$2" replace="$3" candidate="$4"
  validate_config
  mkdir -p "$CODEX_HOME"
  python3 "$HELPER" --check --token-file "$token_file" --workspace "$workspace" >/dev/null 2>&1 \
    || die "Plane token or verified bridge is unavailable; run 'megai plane bridge install' and check the private token file"
  render_candidate "$workspace" "$token_file" "$replace" "$candidate"
}

commit_candidate() {
  local candidate="$1" backup_current="${2:-1}" expected="${PLANE_EXPECTED_ORIGINAL:-}" absent="${PLANE_EXPECTED_ABSENT:-}"
  [ ! -L "$candidate" ] && [ -f "$candidate" ] || die "invalid staged Codex candidate"
  if [ -n "$expected" ]; then
    if [ -f "$absent" ]; then
      [ ! -e "$CONFIG" ] || die "Codex config changed during staging: $CONFIG"
    else
      cmp -s "$CONFIG" "$expected" || die "Codex config changed during staging: $CONFIG"
    fi
  fi
  python3 "$CONFIG_TOOL" validate --file "$candidate" >/dev/null || die "invalid staged Codex candidate"
  mkdir -p "$CODEX_HOME"
  [ ! -L "$CONFIG" ] || die "refusing symlinked Codex config: $CONFIG"
  if [ -f "$CONFIG" ] && cmp -s "$CONFIG" "$candidate"; then
    rm -f -- "$candidate"
    private "$CONFIG" || { chmod 600 "$CONFIG"; }
    ok "Plane Codex MCP already configured"
    return
  fi
  [ ! -e "$CONFIG" ] || [ -f "$CONFIG" ] || die "Codex config is not a regular file: $CONFIG"
  if [ "$backup_current" = 1 ] && [ -f "$CONFIG" ]; then
    python3 "$BACKUP_TOOL" save --root "$MEGAI_HOME/backups/plane" --target "$CONFIG" --kind codex --source "$CONFIG" >/dev/null
  fi
  chmod 600 "$candidate"
  mv -f -- "$candidate" "$CONFIG"
  ok "Plane Codex MCP configured"
}

stage_remove() {
  local candidate="$1" kind
  validate_config
  [ -f "$CONFIG" ] || { : >"$candidate"; chmod 600 "$candidate"; return; }
  kind="$(config_kind)"
  [ "$kind" = missing ] && { cp -- "$CONFIG" "$candidate"; return; }
  [ "$kind" = owned ] || die "existing Codex MCP server 'plane' is user-owned or has invalid markers; refusing to remove it"
  python3 "$CONFIG_TOOL" strip-managed --file "$CONFIG" --begin "$BEGIN" --end "$END" >"$candidate"
  chmod 600 "$candidate"
  python3 "$CONFIG_TOOL" validate --file "$candidate" >/dev/null || die "generated Codex removal is invalid"
}

stage_restore() {
  local candidate="$1"
  [ ! -L "$CONFIG" ] || die "refusing symlinked restore target: $CONFIG"
  mkdir -p "$CODEX_HOME"
  python3 "$BACKUP_TOOL" restore --root "$MEGAI_HOME/backups/plane" --target "$CONFIG" --kind codex --destination "$candidate" >/dev/null
  chmod 600 "$candidate"
}

setup() {
  local workspace="$1" token_file="$2" replace="$3" candidate
  mkdir -p "$CODEX_HOME"
  candidate="$(mktemp "$CODEX_HOME/.config.toml.stage.XXXXXX")"
  stage_setup "$workspace" "$token_file" "$replace" "$candidate"
  commit_candidate "$candidate"
}

remove() {
  local candidate
  candidate="$(mktemp "$CODEX_HOME/.config.toml.stage.XXXXXX")"
  stage_remove "$candidate"
  [ -f "$CONFIG" ] || { rm -f "$candidate"; echo 'Plane Codex MCP: not configured'; return; }
  commit_candidate "$candidate"
  ok 'Plane Codex MCP removed'
}

restore() {
  local candidate
  candidate="$(mktemp "$CODEX_HOME/.config.toml.stage.XXXXXX")"
  stage_restore "$candidate"
  commit_candidate "$candidate" 0
  ok 'Plane Codex connector restored from target-bound private backup'
}

status() {
  validate_config
  case "$(config_kind)" in
    missing) echo 'Plane Codex MCP: not configured' ;;
    owned) echo 'Plane Codex MCP: configured (credential checked at launch)' ;;
    *) echo 'Plane Codex MCP: unmanaged entry preserved' >&2; return 1 ;;
  esac
}

case "${1:-}" in
  setup) [ "$#" -eq 4 ] || die 'usage: plane_codex setup WORKSPACE TOKEN_FILE REPLACE'; setup "$2" "$3" "$4" ;;
  stage-setup) [ "$#" -eq 5 ] || die 'usage: plane_codex stage-setup WORKSPACE TOKEN_FILE REPLACE CANDIDATE'; stage_setup "$2" "$3" "$4" "$5" ;;
  commit) [ "$#" -ge 2 ] && [ "$#" -le 3 ] || die 'usage: plane_codex commit CANDIDATE [NO_BACKUP]'; commit_candidate "$2" "${3:-1}" ;;
  stage-remove) [ "$#" -eq 2 ] || die 'usage: plane_codex stage-remove CANDIDATE'; stage_remove "$2" ;;
  stage-restore) [ "$#" -eq 2 ] || die 'usage: plane_codex stage-restore CANDIDATE'; stage_restore "$2" ;;
  status) status ;;
  remove) remove ;;
  restore) restore ;;
  *) die 'invalid Plane Codex action' ;;
esac

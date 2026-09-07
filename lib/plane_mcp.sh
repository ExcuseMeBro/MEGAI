#!/usr/bin/env bash
# Secure, additive Plane MCP lifecycle for Pi MCP Adapter.
set -euo pipefail

MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"

PLANE_MCP_URL="https://mcp.plane.so/http/api-key/mcp"
PLANE_PYTHON_COMMAND="python3"
PLANE_TOKEN_DEFAULT="$HOME/.config/megai/credentials/plane-api-token"
PLANE_AGENT="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
PLANE_CONFIG="$PLANE_AGENT/mcp.json"
PLANE_HEADER_HELPER="$MEGAI_HOME/lib/plane_mcp_headers.py"
PLANE_CODEX_HELPER="$MEGAI_HOME/lib/plane_codex.sh"

plane_usage() {
  cat <<'EOF'
Usage:
  megai plane setup --workspace SLUG [--token-file PATH] [--client pi|codex|all] [--replace-asana]
  megai plane status [--client pi|codex|all]
  megai plane remove [--client pi|codex|all]
  megai plane restore [--client pi|codex|all]
EOF
}

plane_absolute_path() {
  local path="$1"
  case "$path" in
    ~/*) path="$HOME/${path#~/}" ;;
    /*) ;;
    *) path="$(pwd)/$path" ;;
  esac
  printf '%s\n' "$path"
}

plane_require_tools() {
  command -v jq >/dev/null 2>&1 || die "Plane MCP requires jq"
  command -v python3 >/dev/null 2>&1 || die "Plane MCP requires python3"
  [ -f "$PLANE_HEADER_HELPER" ] || die "Plane MCP header helper is missing: $PLANE_HEADER_HELPER"
}

plane_validate_workspace() {
  local workspace="$1"
  [[ "$workspace" =~ ^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$ ]] || die "invalid Plane workspace slug"
}

plane_validate_token_file() {
  local token_file="$1" workspace="$2"
  plane_validate_workspace "$workspace"
  [ -e "$token_file" ] || die "Plane token file is missing"
  [ ! -L "$token_file" ] || die "Plane token file must not be a symlink"
  [ -f "$token_file" ] || die "Plane token file is not a regular file"
  # The helper repeats these checks at request time with O_NOFOLLOW to close
  # the setup/request TOCTOU window. Setup only receives its exit status.
  python3 "$PLANE_HEADER_HELPER" --check --token-file "$token_file" --workspace "$workspace" \
    >/dev/null 2>&1 || die "Plane token file is missing, empty, or unsafe"
}

plane_validate_config() {
  if [ -L "$PLANE_CONFIG" ]; then
    die "refusing symlinked Pi MCP config: $PLANE_CONFIG"
  fi
  if [ ! -e "$PLANE_CONFIG" ]; then
    return 0
  fi
  [ -f "$PLANE_CONFIG" ] || die "Pi MCP config is not a regular file: $PLANE_CONFIG"
  jq -e 'type == "object" and ((.mcpServers // {}) | type == "object")' \
    "$PLANE_CONFIG" >/dev/null 2>&1 || die "invalid Pi MCP config; no changes made: $PLANE_CONFIG"
}

plane_entry_kind() {
  local helper="$1"
  [ -f "$PLANE_CONFIG" ] || { printf '%s\n' missing; return 0; }
  jq -r --arg helper "$helper" --arg url "$PLANE_MCP_URL" --arg python "$PLANE_PYTHON_COMMAND" '
    (.mcpServers // {}) as $servers
    | if ($servers | has("plane") | not) then "missing"
      elif ($servers.plane | type) != "object" then "unmanaged"
      elif $servers.plane.url == $url and $servers.plane.auth == false
        and $servers.plane.requestHeadersCommand.command == $python
        and ($servers.plane.requestHeadersCommand.args | type) == "array"
        and ($servers.plane.requestHeadersCommand.args | length) == 5
        and $servers.plane.requestHeadersCommand.args[0] == $helper
        and $servers.plane.requestHeadersCommand.args[1] == "--token-file"
        and ($servers.plane.requestHeadersCommand.args[2] | type) == "string"
        and $servers.plane.requestHeadersCommand.args[3] == "--workspace"
        and ($servers.plane.requestHeadersCommand.args[4] | type) == "string"
        and ($servers.plane.requestHeadersCommand.args[4] | test("^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$"))
      then "owned"
      elif $servers.plane.url == $url and $servers.plane.auth == false
        and $servers.plane.requestHeadersCommand.command == $helper
        and ($servers.plane.requestHeadersCommand.args | type) == "array"
        and ($servers.plane.requestHeadersCommand.args | length) == 4
        and $servers.plane.requestHeadersCommand.args[0] == "--token-file"
        and ($servers.plane.requestHeadersCommand.args[1] | type) == "string"
        and $servers.plane.requestHeadersCommand.args[2] == "--workspace"
        and ($servers.plane.requestHeadersCommand.args[3] | type) == "string"
      then "legacy-owned"
      else "unmanaged"
      end
  ' "$PLANE_CONFIG"
}

plane_file_mode() {
  if stat -c '%a' "$1" 2>/dev/null; then
    return 0
  fi
  stat -f '%Lp' "$1" 2>/dev/null
}

plane_config_private() {
  local mode
  mode="$(plane_file_mode "$PLANE_CONFIG")" || return 1
  [ $((0$mode & 077)) -eq 0 ]
}

plane_backup_config() {
  local backup
  [ ! -L "$MEGAI_HOME/backups" ] || die "refusing symlinked MEGAI backup directory"
  mkdir -p "$MEGAI_HOME/backups"
  chmod 700 "$MEGAI_HOME/backups"
  backup="$(mktemp "$MEGAI_HOME/backups/pi-plane-mcp.json.bak.XXXXXX")"
  cp -- "$PLANE_CONFIG" "$backup"
  chmod 600 "$backup"
  printf '%s\n' "$backup"
}

plane_config_matches() {
  local candidate="$1"
  if [ ! -f "$PLANE_CONFIG" ]; then
    return 1
  fi
  cmp -s "$PLANE_CONFIG" "$candidate"
}

plane_render_config() {
  local token_file="$1" workspace="$2" replace_asana="$3"
  local filter='
    (.mcpServers // {}) as $servers
    | (($servers.plane // {}) as $old
      | .mcpServers = ($servers + {
        plane: ({
          url: $url,
          auth: false,
          lifecycle: (if ($old | has("lifecycle")) then $old.lifecycle else "lazy" end),
          requestHeadersCommand: {
            command: $python,
            args: [$helper, "--token-file", $token_file, "--workspace", $workspace]
          }
        } + ($old | del(.url, .auth, .headers, .bearerToken, .bearerTokenEnv,
                        .bearerTokenStore, .oauth, .requestHeadersCommand, .lifecycle)))
      }))
    | if $replace then del(.mcpServers.asana) else . end
  '
  if [ -f "$PLANE_CONFIG" ]; then
    jq --arg url "$PLANE_MCP_URL" --arg python "$PLANE_PYTHON_COMMAND" \
      --arg helper "$PLANE_HEADER_HELPER" --arg token_file "$token_file" \
      --arg workspace "$workspace" --argjson replace "$replace_asana" "$filter" "$PLANE_CONFIG"
  else
    jq -n --arg url "$PLANE_MCP_URL" --arg python "$PLANE_PYTHON_COMMAND" \
      --arg helper "$PLANE_HEADER_HELPER" --arg token_file "$token_file" \
      --arg workspace "$workspace" --argjson replace "$replace_asana" "$filter"
  fi
}

plane_setup() {
  local workspace="" token_file="$PLANE_TOKEN_DEFAULT" client=pi replace_asana=false arg kind
  while [ "$#" -gt 0 ]; do
    arg="$1"
    case "$arg" in
      --workspace)
        [ "$#" -ge 2 ] || die "--workspace requires a value"
        workspace="$2"; shift 2 ;;
      --workspace=*) workspace="${arg#*=}"; shift ;;
      --token-file)
        [ "$#" -ge 2 ] || die "--token-file requires a value"
        token_file="$2"; shift 2 ;;
      --token-file=*) token_file="${arg#*=}"; shift ;;
      --client)
        [ "$#" -ge 2 ] || die "--client requires pi, codex, or all"
        client="$2"; shift 2 ;;
      --client=*) client="${arg#*=}"; shift ;;
      --replace-asana) replace_asana=true; shift ;;
      -h|--help) plane_usage; return 0 ;;
      *) die "unknown Plane setup option: $arg" ;;
    esac
  done
  [ -n "$workspace" ] || die "--workspace is required"
  case "$client" in pi|codex|all) ;; *) die "--client must be pi, codex, or all" ;; esac
  token_file="$(plane_absolute_path "$token_file")"

  plane_require_tools
  plane_validate_token_file "$token_file" "$workspace"
  local kind=missing
  if [ "$client" = pi ] || [ "$client" = all ]; then
    plane_validate_config
    kind="$(plane_entry_kind "$PLANE_HEADER_HELPER")"
    if [ "$kind" = unmanaged ]; then
      die "existing Pi MCP server 'plane' is user-owned; refusing to replace it"
    fi
  fi
  if [ "$client" = codex ] || [ "$client" = all ]; then
    [ -f "$PLANE_CODEX_HELPER" ] || die "Plane Codex helper is missing: $PLANE_CODEX_HELPER"
    local replace_flag=0
    [ "$replace_asana" = true ] && replace_flag=1
    bash "$PLANE_CODEX_HELPER" setup "$workspace" "$token_file" "$replace_flag"
  fi
  [ "$client" != codex ] || return 0

  local candidate
  # Generate into the target directory so the final rename stays atomic. On
  # repeat setup, preserved user fields make the candidate byte-for-byte equal.
  mkdir -p "$PLANE_AGENT"
  candidate="$(mktemp "$PLANE_AGENT/mcp.json.XXXXXX")"
  plane_render_config "$token_file" "$workspace" "$replace_asana" >"$candidate"

  if plane_config_matches "$candidate"; then
    rm -f "$candidate"
    if ! plane_config_private; then
      plane_backup_config >/dev/null
      chmod 600 "$PLANE_CONFIG"
    fi
    ok "Plane MCP already configured (client=pi, workspace=$workspace)"
    return 0
  fi
  if [ -f "$PLANE_CONFIG" ]; then
    plane_backup_config >/dev/null
  fi
  # Candidate was built with jq and is private; move it into place atomically.
  chmod 600 "$candidate"
  mv "$candidate" "$PLANE_CONFIG"
  ok "Plane MCP configured for workspace $workspace"
}

plane_status() {
  local client=pi arg
  while [ "$#" -gt 0 ]; do
    arg="$1"
    case "$arg" in
      --client) [ "$#" -ge 2 ] || die "--client requires pi, codex, or all"; client="$2"; shift 2 ;;
      --client=*) client="${arg#*=}"; shift ;;
      *) die "unknown Plane status option: $arg" ;;
    esac
  done
  case "$client" in
    codex) plane_require_tools; exec bash "$PLANE_CODEX_HELPER" status ;;
    all) plane_status --client pi; bash "$PLANE_CODEX_HELPER" status; return 0 ;;
    pi) ;;
    *) die "--client must be pi, codex, or all" ;;
  esac
  plane_require_tools
  plane_validate_config
  local kind workspace token_file
  kind="$(plane_entry_kind "$PLANE_HEADER_HELPER")"
  case "$kind" in
    missing)
      printf 'Plane MCP: not configured\n'
      return 0
      ;;
    unmanaged)
      printf 'Plane MCP: unmanaged plane entry preserved\n' >&2
      return 1
      ;;
    legacy-owned)
      printf 'Plane MCP: legacy credential reference; rerun setup\n' >&2
      return 1
      ;;
    owned)
      token_file="$(jq -r '.mcpServers.plane.requestHeadersCommand.args[2]' "$PLANE_CONFIG")"
      workspace="$(jq -r '.mcpServers.plane.requestHeadersCommand.args[4]' "$PLANE_CONFIG")"
      if python3 "$PLANE_HEADER_HELPER" --check --token-file "$token_file" --workspace "$workspace" \
        >/dev/null 2>&1; then
        printf 'Plane MCP: configured (workspace=%s, credential=available)\n' "$workspace"
        return 0
      fi
      printf 'Plane MCP: configured (workspace=%s, credential=unavailable)\n' "$workspace" >&2
      return 1
      ;;
  esac
}

plane_remove() {
  local client=pi arg
  while [ "$#" -gt 0 ]; do
    arg="$1"
    case "$arg" in
      --client) [ "$#" -ge 2 ] || die "--client requires pi, codex, or all"; client="$2"; shift 2 ;;
      --client=*) client="${arg#*=}"; shift ;;
      *) die "unknown Plane remove option: $arg" ;;
    esac
  done
  case "$client" in
    codex) plane_require_tools; exec bash "$PLANE_CODEX_HELPER" remove ;;
    all) plane_remove --client pi; bash "$PLANE_CODEX_HELPER" remove; return 0 ;;
    pi) ;;
    *) die "--client must be pi, codex, or all" ;;
  esac
  plane_require_tools
  [ -e "$PLANE_CONFIG" ] || { printf 'Plane MCP: not configured\n'; return 0; }
  plane_validate_config
  local kind tmp
  kind="$(plane_entry_kind "$PLANE_HEADER_HELPER")"
  case "$kind" in
    missing)
      printf 'Plane MCP: not configured\n'
      return 0
      ;;
    unmanaged)
      die "existing Pi MCP server 'plane' is user-owned; refusing to remove it"
      ;;
  esac
  plane_backup_config >/dev/null
  tmp="$(mktemp "$PLANE_AGENT/mcp.json.XXXXXX")"
  jq 'del(.mcpServers.plane)' "$PLANE_CONFIG" >"$tmp"
  chmod 600 "$tmp"
  mv "$tmp" "$PLANE_CONFIG"
  ok "Plane Pi MCP removed; unrelated MCP entries preserved"
}

plane_restore() {
  local client=pi arg
  while [ "$#" -gt 0 ]; do
    arg="$1"
    case "$arg" in
      --client) [ "$#" -ge 2 ] || die "--client requires pi, codex, or all"; client="$2"; shift 2 ;;
      --client=*) client="${arg#*=}"; shift ;;
      *) die "unknown Plane restore option: $arg" ;;
    esac
  done
  case "$client" in
    codex) plane_require_tools; exec bash "$PLANE_CODEX_HELPER" restore ;;
    all) plane_restore --client pi; bash "$PLANE_CODEX_HELPER" restore; return 0 ;;
    pi) ;;
    *) die "--client must be pi, codex, or all" ;;
  esac
  plane_require_tools
  local backup target tmp
  backup="$(ls -t "$MEGAI_HOME"/backups/pi-plane-mcp.json.bak.* 2>/dev/null | head -n1 || true)"
  [ -n "$backup" ] || die "Plane Pi restore: no private backup found"
  [ ! -L "$PLANE_CONFIG" ] || die "refusing symlinked Pi MCP config: $PLANE_CONFIG"
  target="$(dirname "$PLANE_CONFIG")"
  mkdir -p "$target"
  tmp="$(mktemp "$target/mcp.json.XXXXXX")"
  cp -- "$backup" "$tmp"; chmod 600 "$tmp"; mv "$tmp" "$PLANE_CONFIG"
  ok "Plane Pi restored from private backup"
}

plane_main() {
  local action="${1:-}"
  [ "$#" -gt 0 ] && shift || true
  case "$action" in
    setup) plane_setup "$@" ;;
    status) plane_status "$@" ;;
    remove) plane_remove "$@" ;;
    restore) plane_restore "$@" ;;
    -h|--help|help) plane_usage ;;
    *) plane_usage >&2; return 1 ;;
  esac
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  plane_main "$@"
fi

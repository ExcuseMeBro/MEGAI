#!/usr/bin/env bash
# Secure, additive Plane MCP lifecycle for Pi MCP Adapter.
set -euo pipefail

MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"

PLANE_MCP_URL="https://mcp.plane.so/http/api-key/mcp"
PLANE_TOKEN_DEFAULT="$HOME/.config/megai/credentials/plane-api-token"
PLANE_AGENT="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
PLANE_CONFIG="$PLANE_AGENT/mcp.json"
PLANE_HEADER_HELPER="$MEGAI_HOME/lib/plane_mcp_headers.py"

plane_usage() {
  cat <<'EOF'
Usage:
  megai plane setup --workspace SLUG [--token-file PATH]
  megai plane status
  megai plane remove
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
  jq -r --arg helper "$helper" --arg url "$PLANE_MCP_URL" '
    (.mcpServers // {}) as $servers
    | if ($servers | has("plane") | not) then "missing"
      elif ($servers.plane | type) != "object" then "unmanaged"
      elif $servers.plane.url == $url
        and $servers.plane.auth == false
        and $servers.plane.requestHeadersCommand.command == $helper
        and ($servers.plane.requestHeadersCommand.args | type) == "array"
        and ($servers.plane.requestHeadersCommand.args | length) == 4
        and ($servers.plane.requestHeadersCommand.args[1] | type) == "string"
        and ($servers.plane.requestHeadersCommand.args[3] | type) == "string"
        and ($servers.plane.requestHeadersCommand.args[3] | test("^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$"))
        and $servers.plane.requestHeadersCommand.args[0] == "--token-file"
        and $servers.plane.requestHeadersCommand.args[2] == "--workspace"
      then "owned"
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

plane_setup() {
  local workspace="" token_file="$PLANE_TOKEN_DEFAULT" arg kind
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
      -h|--help) plane_usage; return 0 ;;
      *) die "unknown Plane setup option: $arg" ;;
    esac
  done
  [ -n "$workspace" ] || die "--workspace is required"
  token_file="$(plane_absolute_path "$token_file")"

  plane_require_tools
  plane_validate_token_file "$token_file" "$workspace"
  plane_validate_config
  kind="$(plane_entry_kind "$PLANE_HEADER_HELPER")"
  if [ "$kind" = unmanaged ]; then
    die "existing Pi MCP server 'plane' is user-owned; refusing to replace it"
  fi

  local candidate
  candidate="$(mktemp)"
  # Generate into a temporary copy of the config so repeat setup can avoid an
  # unnecessary backup/write. The real write remains atomic in its directory.
  if [ -f "$PLANE_CONFIG" ]; then
    jq --arg url "$PLANE_MCP_URL" --arg helper "$PLANE_HEADER_HELPER" \
      --arg token_file "$token_file" --arg workspace "$workspace" '
      .mcpServers = ((.mcpServers // {}) + {
        plane: {
          url: $url,
          auth: false,
          lifecycle: "lazy",
          requestHeadersCommand: {
            command: $helper,
            args: ["--token-file", $token_file, "--workspace", $workspace]
          }
        }
      })
    ' "$PLANE_CONFIG" >"$candidate"
  else
    jq -n --arg url "$PLANE_MCP_URL" --arg helper "$PLANE_HEADER_HELPER" \
      --arg token_file "$token_file" --arg workspace "$workspace" '
      {mcpServers: {plane: {
        url: $url,
        auth: false,
        lifecycle: "lazy",
        requestHeadersCommand: {
          command: $helper,
          args: ["--token-file", $token_file, "--workspace", $workspace]
        }
      }}}
    ' >"$candidate"
  fi

  if plane_config_matches "$candidate"; then
    rm -f "$candidate"
    if ! plane_config_private; then
      plane_backup_config >/dev/null
      chmod 600 "$PLANE_CONFIG"
    fi
    ok "Plane MCP already configured (workspace=$workspace)"
    return 0
  fi
  if [ -f "$PLANE_CONFIG" ]; then
    plane_backup_config >/dev/null
  fi
  # Candidate was built with jq and is private; move it into place atomically.
  mkdir -p "$PLANE_AGENT"
  chmod 600 "$candidate"
  mv "$candidate" "$PLANE_CONFIG"
  ok "Plane MCP configured for workspace $workspace"
}

plane_status() {
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
    owned)
      token_file="$(jq -r '.mcpServers.plane.requestHeadersCommand.args[1]' "$PLANE_CONFIG")"
      workspace="$(jq -r '.mcpServers.plane.requestHeadersCommand.args[3]' "$PLANE_CONFIG")"
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
  ok "Plane MCP removed; Asana and unrelated MCP entries preserved"
}

plane_main() {
  local action="${1:-}"
  [ "$#" -gt 0 ] && shift || true
  case "$action" in
    setup) plane_setup "$@" ;;
    status) [ "$#" -eq 0 ] || die "plane status takes no options"; plane_status ;;
    remove) [ "$#" -eq 0 ] || die "plane remove takes no options"; plane_remove ;;
    -h|--help|help) plane_usage ;;
    *) plane_usage >&2; return 1 ;;
  esac
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  plane_main "$@"
fi

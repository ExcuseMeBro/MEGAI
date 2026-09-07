#!/usr/bin/env bash
# Secure, additive Plane MCP lifecycle for Pi MCP Adapter and Codex.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
. "$MEGAI_HOME/lib/ui.sh"

PLANE_MCP_URL="https://mcp.plane.so/http/api-key/mcp"
PLANE_PYTHON_COMMAND="python3"
PLANE_TOKEN_DEFAULT="$HOME/.config/megai/credentials/plane-api-token"
PLANE_AGENT="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
PLANE_CONFIG="$PLANE_AGENT/mcp.json"
PLANE_CODEX_CONFIG="${CODEX_HOME:-$HOME/.codex}/config.toml"
PLANE_HEADER_HELPER="$MEGAI_HOME/lib/plane_mcp_headers.py"
PLANE_CODEX_HELPER="$MEGAI_HOME/lib/plane_codex.sh"
PLANE_BACKUP_TOOL="$MEGAI_HOME/lib/plane_backup.py"

plane_usage() {
  cat <<'EOF'
Usage:
  megai plane bridge install
  megai plane setup --workspace SLUG [--token-file PATH] [--client pi|codex|all] [--replace-asana]
  megai plane status [--client pi|codex|all]
  megai plane remove [--client pi|codex|all]
  megai plane restore [--client pi|codex|all]

restore is connector-only and target-bound. Task-flow policy backups are managed
by wire/install_taskflow_policy and are not silently overwritten or restored here.
EOF
}

plane_absolute_path() {
  local path="$1"
  case "$path" in ~/*) path="$HOME/${path#~/}" ;; /*) ;; *) path="$(pwd)/$path" ;; esac
  printf '%s\n' "$path"
}

plane_require_tools() {
  command -v jq >/dev/null 2>&1 || die "Plane MCP requires jq"
  command -v python3 >/dev/null 2>&1 || die "Plane MCP requires python3"
  [ -f "$PLANE_HEADER_HELPER" ] || die "Plane MCP header helper is missing: $PLANE_HEADER_HELPER"
}

plane_validate_workspace() {
  [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$ ]] || die "invalid Plane workspace slug"
}

plane_validate_token_file() {
  local token_file="$1" workspace="$2"
  plane_validate_workspace "$workspace"
  [ -e "$token_file" ] || die "Plane token file is missing"
  [ ! -L "$token_file" ] || die "Plane token file must not be a symlink"
  [ -f "$token_file" ] || die "Plane token file is not a regular file"
  python3 "$PLANE_HEADER_HELPER" --check --token-file "$token_file" --workspace "$workspace" >/dev/null 2>&1 \
    || die "Plane token file is missing, empty, or unsafe"
}

plane_validate_config() {
  [ ! -L "$PLANE_CONFIG" ] || die "refusing symlinked Pi MCP config: $PLANE_CONFIG"
  [ ! -e "$PLANE_CONFIG" ] && return 0
  [ -f "$PLANE_CONFIG" ] || die "Pi MCP config is not a regular file: $PLANE_CONFIG"
  jq -e 'type == "object" and ((.mcpServers // {}) | type == "object")' "$PLANE_CONFIG" >/dev/null 2>&1 \
    || die "invalid Pi MCP config; no changes made: $PLANE_CONFIG"
}

plane_entry_kind() {
  local helper="$1"
  [ -f "$PLANE_CONFIG" ] || { printf '%s\n' missing; return; }
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
        and ($servers.plane.requestHeadersCommand.args[4] | test("^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")) then "owned"
      elif $servers.plane.url == $url and $servers.plane.auth == false
        and $servers.plane.requestHeadersCommand.command == $helper
        and ($servers.plane.requestHeadersCommand.args | type) == "array"
        and ($servers.plane.requestHeadersCommand.args | length) == 4
        and $servers.plane.requestHeadersCommand.args[0] == "--token-file"
        and ($servers.plane.requestHeadersCommand.args[1] | type) == "string"
        and $servers.plane.requestHeadersCommand.args[2] == "--workspace"
        and ($servers.plane.requestHeadersCommand.args[3] | type) == "string" then "legacy-owned"
      else "unmanaged" end
  ' "$PLANE_CONFIG"
}

plane_private() {
  local mode
  mode="$(stat -c '%a' "$1" 2>/dev/null || stat -f '%Lp' "$1")"
  [ $((0$mode & 077)) -eq 0 ]
}

plane_backup() {
  local target="${1:-$PLANE_CONFIG}"
  python3 "$PLANE_BACKUP_TOOL" save --root "$MEGAI_HOME/backups/plane" --target "$target" --kind pi --source "$target" >/dev/null
}

plane_restore_to() {
  python3 "$PLANE_BACKUP_TOOL" restore --root "$MEGAI_HOME/backups/plane" --target "$PLANE_CONFIG" --kind pi --destination "$1" >/dev/null
}

plane_rollback_pi() {
  local had_config="$1" rollback
  if [ "$had_config" = 1 ]; then
    rollback="$(mktemp "$PLANE_AGENT/.mcp.json.rollback.XXXXXX")"
    plane_restore_to "$rollback"
    plane_commit "$rollback" 0
  else
    [ ! -L "$PLANE_CONFIG" ] || die "refusing symlinked Pi rollback target"
    rm -f -- "$PLANE_CONFIG"
  fi
}

plane_render_config() {
  local token_file="$1" workspace="$2" replace_asana="$3"
  local filter='
    (.mcpServers // {}) as $servers
    | (($servers.plane // {}) as $old
      | .mcpServers = ($servers + {plane: ({
          url: $url, auth: false,
          lifecycle: (if ($old | has("lifecycle")) then $old.lifecycle else "lazy" end),
          requestHeadersCommand: {command: $python, args: [$helper, "--token-file", $token_file, "--workspace", $workspace]}
        } + ($old | del(.url, .auth, .headers, .bearerToken, .bearerTokenEnv,
                        .bearerTokenStore, .oauth, .requestHeadersCommand, .lifecycle)))}))
    | if $replace then del(.mcpServers.asana) else . end'
  if [ -f "$PLANE_CONFIG" ]; then
    jq --arg url "$PLANE_MCP_URL" --arg python "$PLANE_PYTHON_COMMAND" --arg helper "$PLANE_HEADER_HELPER" \
      --arg token_file "$token_file" --arg workspace "$workspace" --argjson replace "$replace_asana" "$filter" "$PLANE_CONFIG"
  else
    jq -n --arg url "$PLANE_MCP_URL" --arg python "$PLANE_PYTHON_COMMAND" --arg helper "$PLANE_HEADER_HELPER" \
      --arg token_file "$token_file" --arg workspace "$workspace" --argjson replace "$replace_asana" "$filter"
  fi
}

plane_stage_setup() {
  local candidate="$1" token_file="$2" workspace="$3" replace="$4" kind
  plane_validate_config
  kind="$(plane_entry_kind "$PLANE_HEADER_HELPER")"
  [ "$kind" != unmanaged ] || die "existing Pi MCP server 'plane' is user-owned; refusing to replace it"
  plane_render_config "$token_file" "$workspace" "$replace" >"$candidate"
  chmod 600 "$candidate"
  jq -e 'type == "object" and ((.mcpServers // {}) | type == "object")' "$candidate" >/dev/null \
    || die "generated Pi MCP config is invalid"
}

plane_commit() {
  local candidate="$1" backup_current="${2:-1}"
  [ ! -L "$candidate" ] && [ -f "$candidate" ] || die "invalid staged Pi MCP candidate"
  [ ! -L "$PLANE_CONFIG" ] || die "refusing symlinked Pi MCP config: $PLANE_CONFIG"
  mkdir -p "$PLANE_AGENT"
  if [ -f "$PLANE_CONFIG" ] && cmp -s "$PLANE_CONFIG" "$candidate"; then
    rm -f "$candidate"; plane_private "$PLANE_CONFIG" || chmod 600 "$PLANE_CONFIG"; return 0
  fi
  [ ! -e "$PLANE_CONFIG" ] || [ -f "$PLANE_CONFIG" ] || die "Pi MCP config is not regular"
  if [ "$backup_current" = 1 ] && [ -f "$PLANE_CONFIG" ]; then plane_backup; fi
  chmod 600 "$candidate"
  mv -f -- "$candidate" "$PLANE_CONFIG"
}

plane_stage_remove() {
  local candidate="$1" kind
  plane_validate_config
  [ -f "$PLANE_CONFIG" ] || { : >"$candidate"; chmod 600 "$candidate"; return; }
  kind="$(plane_entry_kind "$PLANE_HEADER_HELPER")"
  [ "$kind" != unmanaged ] || die "existing Pi MCP server 'plane' is user-owned; refusing to remove it"
  [ "$kind" = missing ] && { cp -- "$PLANE_CONFIG" "$candidate"; chmod 600 "$candidate"; return; }
  jq 'del(.mcpServers.plane)' "$PLANE_CONFIG" >"$candidate"
  chmod 600 "$candidate"
}

plane_setup() {
  local workspace="" token_file="$PLANE_TOKEN_DEFAULT" client=pi replace_asana=false arg
  while [ "$#" -gt 0 ]; do
    arg="$1"
    case "$arg" in
      --workspace) [ "$#" -ge 2 ] || die "--workspace requires a value"; workspace="$2"; shift 2;;
      --workspace=*) workspace="${arg#*=}"; shift;;
      --token-file) [ "$#" -ge 2 ] || die "--token-file requires a value"; token_file="$2"; shift 2;;
      --token-file=*) token_file="${arg#*=}"; shift;;
      --client) [ "$#" -ge 2 ] || die "--client requires pi, codex, or all"; client="$2"; shift 2;;
      --client=*) client="${arg#*=}"; shift;;
      --replace-asana) replace_asana=true; shift;;
      -h|--help) plane_usage; return 0;;
      *) die "unknown Plane setup option: $arg";;
    esac
  done
  [ -n "$workspace" ] || die "--workspace is required"
  case "$client" in pi|codex|all);; *) die "--client must be pi, codex, or all";; esac
  token_file="$(plane_absolute_path "$token_file")"
  plane_require_tools; plane_validate_token_file "$token_file" "$workspace"
  local replace_flag=0; [ "$replace_asana" = true ] && replace_flag=1
  local pi_candidate codex_candidate pi_had_config=0 pi_changed=0
  [ -f "$PLANE_CONFIG" ] && pi_had_config=1
  mkdir -p "$PLANE_AGENT" "$(dirname "$PLANE_CODEX_CONFIG")"
  pi_candidate="$(mktemp "$PLANE_AGENT/.mcp.json.stage.XXXXXX")"
  codex_candidate="$(mktemp "$(dirname "$PLANE_CODEX_CONFIG")/.config.toml.stage.XXXXXX")"
  trap 'rm -f -- "$pi_candidate" "$codex_candidate"' RETURN

  # Stage every requested client before any target is replaced.
  if [ "$client" = pi ] || [ "$client" = all ]; then plane_stage_setup "$pi_candidate" "$token_file" "$workspace" "$replace_asana"; fi
  if [ "$client" = codex ] || [ "$client" = all ]; then
    [ -f "$PLANE_CODEX_HELPER" ] || die "Plane Codex helper is missing: $PLANE_CODEX_HELPER"
    bash "$PLANE_CODEX_HELPER" stage-setup "$workspace" "$token_file" "$replace_flag" "$codex_candidate"
  fi
  if [ "$client" = pi ] || [ "$client" = all ]; then
    if [ ! -f "$PLANE_CONFIG" ] || ! cmp -s "$PLANE_CONFIG" "$pi_candidate"; then pi_changed=1; fi
    plane_commit "$pi_candidate"
  fi
  if [ "$client" = codex ] || [ "$client" = all ]; then
    if ! bash "$PLANE_CODEX_HELPER" commit "$codex_candidate"; then
      if [ "$client" = all ] && [ "$pi_changed" = 1 ]; then plane_rollback_pi "$pi_had_config"; fi
      die "Plane Codex commit failed; staged clients were rolled back"
    fi
  fi
  trap - RETURN
  ok "Plane MCP configured (client=$client, workspace=$workspace)"
}

plane_status() {
  local client=pi arg
  while [ "$#" -gt 0 ]; do case "$1" in --client) [ "$#" -ge 2 ] || die "--client requires a value"; client="$2"; shift 2;; --client=*) client="${1#*=}"; shift;; *) die "unknown Plane status option: $1";; esac; done
  case "$client" in codex) exec bash "$PLANE_CODEX_HELPER" status;; all) plane_status --client pi; bash "$PLANE_CODEX_HELPER" status;; pi);; *) die "--client must be pi, codex, or all";; esac
  plane_require_tools; plane_validate_config
  local kind token_file workspace
  kind="$(plane_entry_kind "$PLANE_HEADER_HELPER")"
  case "$kind" in
    missing) echo 'Plane MCP: not configured';;
    unmanaged) echo 'Plane MCP: unmanaged plane entry preserved' >&2; return 1;;
    legacy-owned) echo 'Plane MCP: legacy credential reference; rerun setup' >&2; return 1;;
    owned)
      token_file="$(jq -r '.mcpServers.plane.requestHeadersCommand.args[2]' "$PLANE_CONFIG")"
      workspace="$(jq -r '.mcpServers.plane.requestHeadersCommand.args[4]' "$PLANE_CONFIG")"
      if python3 "$PLANE_HEADER_HELPER" --check --token-file "$token_file" --workspace "$workspace" >/dev/null 2>&1; then
        printf 'Plane MCP: configured (workspace=%s, credential=available)\n' "$workspace"
      else printf 'Plane MCP: configured (workspace=%s, credential=unavailable)\n' "$workspace" >&2; return 1; fi;;
  esac
}

plane_remove() {
  local client=pi arg
  while [ "$#" -gt 0 ]; do case "$1" in --client) [ "$#" -ge 2 ] || die "--client requires a value"; client="$2"; shift 2;; --client=*) client="${1#*=}"; shift;; *) die "unknown Plane remove option: $1";; esac; done
  case "$client" in pi|codex|all);; *) die "--client must be pi, codex, or all";; esac
  plane_require_tools
  local pi_candidate codex_candidate pi_had_config=0 pi_changed=0
  [ -f "$PLANE_CONFIG" ] && pi_had_config=1
  mkdir -p "$PLANE_AGENT" "$(dirname "$PLANE_CODEX_CONFIG")"
  pi_candidate="$(mktemp "$PLANE_AGENT/.mcp.json.stage.XXXXXX")"; codex_candidate="$(mktemp "$(dirname "$PLANE_CODEX_CONFIG")/.config.toml.stage.XXXXXX")"
  trap 'rm -f -- "$pi_candidate" "$codex_candidate"' RETURN
  if [ "$client" = pi ] || [ "$client" = all ]; then plane_stage_remove "$pi_candidate"; fi
  if [ "$client" = codex ] || [ "$client" = all ]; then bash "$PLANE_CODEX_HELPER" stage-remove "$codex_candidate"; fi
  if { [ "$client" = pi ] || [ "$client" = all ]; } && [ -f "$PLANE_CONFIG" ]; then
    if ! cmp -s "$PLANE_CONFIG" "$pi_candidate"; then pi_changed=1; fi
    plane_commit "$pi_candidate"
  fi
  if { [ "$client" = codex ] || [ "$client" = all ]; } && [ -f "$PLANE_CODEX_CONFIG" ]; then
    if ! bash "$PLANE_CODEX_HELPER" commit "$codex_candidate"; then
      if [ "$client" = all ] && [ "$pi_changed" = 1 ]; then plane_rollback_pi "$pi_had_config"; fi
      die "Plane Codex removal failed; staged clients were rolled back"
    fi
  fi
  trap - RETURN
  ok "Plane MCP removed (client=$client)"
}

plane_restore() {
  local client=pi arg
  while [ "$#" -gt 0 ]; do case "$1" in --client) [ "$#" -ge 2 ] || die "--client requires a value"; client="$2"; shift 2;; --client=*) client="${1#*=}"; shift;; *) die "unknown Plane restore option: $1";; esac; done
  case "$client" in pi|codex|all);; *) die "--client must be pi, codex, or all";; esac
  plane_require_tools
  local pi_candidate codex_candidate pi_rollback="" pi_had_config=0 pi_changed=0
  [ -f "$PLANE_CONFIG" ] && pi_had_config=1
  mkdir -p "$PLANE_AGENT" "$(dirname "$PLANE_CODEX_CONFIG")"
  pi_candidate="$(mktemp "$PLANE_AGENT/.mcp.json.stage.XXXXXX")"; codex_candidate="$(mktemp "$(dirname "$PLANE_CODEX_CONFIG")/.config.toml.stage.XXXXXX")"
  if [ "$client" = all ] && [ "$pi_had_config" = 1 ]; then
    pi_rollback="$(mktemp "$PLANE_AGENT/.mcp.json.rollback.XXXXXX")"
    cp -- "$PLANE_CONFIG" "$pi_rollback"
    chmod 600 "$pi_rollback"
  fi
  trap 'rm -f -- "$pi_candidate" "$codex_candidate" "$pi_rollback"' RETURN
  if [ "$client" = pi ] || [ "$client" = all ]; then plane_restore_to "$pi_candidate"; fi
  if [ "$client" = codex ] || [ "$client" = all ]; then bash "$PLANE_CODEX_HELPER" stage-restore "$codex_candidate"; fi
  if [ "$client" = pi ] || [ "$client" = all ]; then
    if [ ! -f "$PLANE_CONFIG" ] || ! cmp -s "$PLANE_CONFIG" "$pi_candidate"; then pi_changed=1; fi
    plane_commit "$pi_candidate" 0
  fi
  if [ "$client" = codex ] || [ "$client" = all ]; then
    if [ "$client" = all ]; then
      if ! bash "$PLANE_CODEX_HELPER" commit "$codex_candidate" 0; then
        if [ "$pi_changed" = 1 ]; then
          [ ! -L "$PLANE_CONFIG" ] || die "refusing symlinked Pi rollback target"
          if [ "$pi_had_config" = 1 ]; then mv -f -- "$pi_rollback" "$PLANE_CONFIG"; else rm -f -- "$PLANE_CONFIG"; fi
        fi
        die "Plane Codex restore failed; staged clients were rolled back"
      fi
    else
      bash "$PLANE_CODEX_HELPER" commit "$codex_candidate" 0
    fi
  fi
  trap - RETURN
  ok "Plane connector restored (client=$client; policy backups untouched)"
}

plane_main() {
  local action="${1:-}"; [ "$#" -gt 0 ] && shift || true
  case "$action" in
    setup) plane_setup "$@";; status) plane_status "$@";; remove) plane_remove "$@";; restore) plane_restore "$@";;
    bridge) exec bash "$MEGAI_HOME/lib/plane_bridge.sh" "$@";;
    -h|--help|help) plane_usage;; *) plane_usage >&2; return 1;;
  esac
}
if [ "${BASH_SOURCE[0]}" = "$0" ]; then plane_main "$@"; fi

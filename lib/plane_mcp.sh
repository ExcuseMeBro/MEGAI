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
PLANE_CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
PLANE_CODEX_CONFIG="$PLANE_CODEX_HOME/config.toml"
PLANE_HEADER_HELPER="$MEGAI_HOME/lib/plane_mcp_headers.py"
PLANE_CODEX_HELPER="$MEGAI_HOME/lib/plane_codex.sh"
PLANE_BACKUP_TOOL="$MEGAI_HOME/lib/plane_backup.py"
PLANE_REMOTE_HELPER="$MEGAI_HOME/lib/plane_mcp_remote.py"
PLANE_CC_CONFIG="$HOME/.claude.json"
plane_omp_config() {
  local profile="${OMP_PROFILE:-${PI_PROFILE:-}}"
  if [ -n "$profile" ]; then
    [[ "$profile" =~ ^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$ ]] || die "invalid OMP profile; use a named profile without path separators: $profile"
    printf '%s\n' "$HOME/.omp/profiles/$profile/agent/mcp.json"
  else
    printf '%s\n' "$HOME/.omp/agent/mcp.json"
  fi
}

plane_validate_target_path() {
  local target="$1" parent
  [ ! -L "$target" ] || die "refusing symlinked Plane target: $target"
  parent="$(dirname "$target")"
  while [ "$parent" != "/" ] && [ "$parent" != "." ]; do
    case "$parent" in
      "$HOME") break;;
      "$MEGAI_HOME"|"$PLANE_CODEX_HOME"|"$PLANE_AGENT")
        [ ! -L "$parent" ] || die "refusing symlinked Plane target parent: $parent"; break;;
      "$HOME"/*|"$MEGAI_HOME"/*|"$PLANE_CODEX_HOME"/*|"$PLANE_AGENT"/*)
        [ ! -L "$parent" ] || die "refusing symlinked Plane target parent: $parent";;
    esac
    parent="$(dirname "$parent")"
  done
}

plane_usage() {
  cat <<'EOF'
Usage:
  megai plane bridge install
  megai plane setup --workspace SLUG [--token-file PATH] [--client pi|codex|cc|omp|all] [--replace-asana]
  megai plane status [--client pi|codex|cc|omp|all]
  megai plane remove [--client pi|codex|cc|omp|all]
  megai plane restore [--client pi|codex|cc|omp|all]

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

plane_validate_generic_config() {
  local target="$1"
  [ ! -L "$target" ] || die "refusing symlinked harness MCP config: $target"
  [ ! -e "$target" ] && return 0
  [ -f "$target" ] || die "harness MCP config is not a regular file: $target"
  jq -e 'type == "object" and ((.mcpServers // {}) | type == "object")' "$target" >/dev/null 2>&1 \
    || die "invalid harness MCP config; no changes made: $target"
}

generic_entry_kind() {
  local target="$1"
  [ -f "$target" ] || { printf '%s\n' missing; return; }
  jq -r --arg helper "$PLANE_REMOTE_HELPER" --arg python "$PLANE_PYTHON_COMMAND" --arg url "$PLANE_MCP_URL" '
    (.mcpServers // {}) as $servers
    | if ($servers | has("plane") | not) then "missing"
      elif ($servers.plane | type) != "object" then "unmanaged"
      elif $servers.plane.command == $python and ($servers.plane.args | type) == "array"
        and ($servers.plane.args | length) == 5 and $servers.plane.args[0] == $helper
        and $servers.plane.args[1] == "--token-file" and ($servers.plane.args[2] | type) == "string"
        and $servers.plane.args[3] == "--workspace" and ($servers.plane.args[4] | type) == "string"
        and ($servers.plane.args[4] | test("^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")) then "owned"
      else "unmanaged" end
  ' "$target"
}

generic_render_config() {
  local target="$1" token_file="$2" workspace="$3"
  if [ -f "$target" ]; then
    jq --arg helper "$PLANE_REMOTE_HELPER" --arg python "$PLANE_PYTHON_COMMAND" \
      --arg token_file "$token_file" --arg workspace "$workspace" '
      (.mcpServers // {}) as $servers
      | (($servers.plane // {}) as $old
        | .mcpServers = ($servers + {plane: ({command:$python,
            args:[$helper,"--token-file",$token_file,"--workspace",$workspace], lifecycle:(if ($old|has("lifecycle")) then $old.lifecycle else "lazy" end)}
            + ($old | del(.command,.args,.lifecycle))) }))' "$target"
  else
    jq -n --arg helper "$PLANE_REMOTE_HELPER" --arg python "$PLANE_PYTHON_COMMAND" \
      --arg token_file "$token_file" --arg workspace "$workspace" \
      '{mcpServers:{plane:{command:$python,args:[$helper,"--token-file",$token_file,"--workspace",$workspace],lifecycle:"lazy"}}}'
  fi
}

generic_stage_setup() {
  local target="$1" candidate="$2" token_file="$3" workspace="$4" kind
  plane_validate_target_path "$target"
  [ -f "$PLANE_REMOTE_HELPER" ] || die "Plane remote bridge is missing: $PLANE_REMOTE_HELPER"
  python3 "$PLANE_REMOTE_HELPER" --check --token-file "$token_file" --workspace "$workspace" >/dev/null \
    || die "Plane remote bridge or credential is unavailable; no changes made for $target"
  plane_validate_generic_config "$target"
  kind="$(generic_entry_kind "$target")"
  [ "$kind" != unmanaged ] || die "existing user-owned Plane entry preserved: $target"
  generic_render_config "$target" "$token_file" "$workspace" >"$candidate"
  chmod 600 "$candidate"
}

generic_stage_remove() {
  local target="$1" candidate="$2" kind
  plane_validate_target_path "$target"
  plane_validate_generic_config "$target"
  [ -f "$target" ] || { : >"$candidate"; chmod 600 "$candidate"; return; }
  kind="$(generic_entry_kind "$target")"
  [ "$kind" != unmanaged ] || die "existing user-owned Plane entry preserved: $target"
  jq 'del(.mcpServers.plane)' "$target" >"$candidate"
  chmod 600 "$candidate"
}

generic_commit() {
  local target="$1" candidate="$2" kind="$3" backup_current="${4:-1}" expected_dir="${5:-${PLANE_EXPECTED_DIR:-}}" expected_key="${6:-${PLANE_EXPECTED_KEY:-}}"
  [ ! -L "$candidate" ] && [ -f "$candidate" ] || die "invalid staged harness MCP candidate"
  if [ -n "$expected_dir" ] && [ "${PLANE_EXPECTED_TARGET:-$target}" = "$target" ]; then plane_txn_assert_original "$expected_dir" "$target" "$expected_key" || return 1; fi
  plane_validate_target_path "$target"
  plane_validate_generic_config "$target"
  mkdir -p "$(dirname "$target")"
  if [ -f "$target" ] && cmp -s "$target" "$candidate"; then rm -f "$candidate"; return; fi
  if [ "$backup_current" = 1 ] && [ -f "$target" ]; then
    python3 "$PLANE_BACKUP_TOOL" save --root "$MEGAI_HOME/backups/plane" --target "$target" --kind "$kind" --source "$target" >/dev/null
  fi
  mv -f -- "$candidate" "$target"
}

plane_txn_directory() {
  mkdir -p "$MEGAI_HOME/backups"
  mktemp -d "$MEGAI_HOME/backups/plane-transaction.XXXXXX"
}

plane_txn_snapshot() {
  local directory="$1" target="$2" key="$3"
  plane_validate_target_path "$target"
  if [ -f "$target" ]; then
    cp -- "$target" "$directory/$key"
    # Store mode portably in a separate private file.
    (stat -f '%Lp' "$target" 2>/dev/null || stat -c '%a' "$target") >"$directory/$key.mode"
  else
    : >"$directory/$key.absent"
  fi
}

plane_txn_assert_original() {
  local directory="$1" target="$2" key="$3"
  PLANE_EXPECTED_DIR="$directory" PLANE_EXPECTED_TARGET="$target" PLANE_EXPECTED_KEY="$key"
  if [ "$target" = "$PLANE_CODEX_CONFIG" ]; then
    export PLANE_EXPECTED_ORIGINAL="$directory/$key" PLANE_EXPECTED_ABSENT="$directory/$key.absent"
  fi
  if [ -f "$directory/$key.absent" ]; then
    [ ! -e "$target" ] || { printf 'concurrent target changed before publication: %s\n' "$target" >&2; return 1; }
  else
    cmp -s "$target" "$directory/$key" || { printf 'concurrent target changed before publication: %s\n' "$target" >&2; return 1; }
  fi
}

plane_txn_mark_after() {
  local directory="$1" target="$2" key="$3"
  if [ -f "$target" ]; then cp -- "$target" "$directory/$key.after"; else : >"$directory/$key.after.absent"; fi
}

plane_txn_rollback() {
  local directory="$1" failed=0 target key
  shift
  while [ "$#" -gt 0 ]; do
    target="$1"; key="$2"; shift 2
    if ! plane_txn_restore "$directory" "$target" "$key"; then failed=1; fi
  done
  return "$failed"
}

plane_txn_restore() {
  local directory="$1" target="$2" key="$3" temporary
  [ ! -L "$target" ] || die "refusing symlinked transaction target: $target"
  # Only roll back a target this transaction successfully committed. A missing
  # marker means the target was staged but never published.
  [ -e "$directory/$key.after" ] || [ -e "$directory/$key.after.absent" ] || return 0
  if [ -f "$directory/$key.after.absent" ]; then
    [ ! -e "$target" ] || { printf 'rollback refused: concurrent target appeared: %s\n' "$target" >&2; return 1; }
  else
    cmp -s "$target" "$directory/$key.after" || { printf 'rollback refused: concurrent target changed: %s\n' "$target" >&2; return 1; }
  fi
  if [ -f "$directory/$key.absent" ]; then rm -f -- "$target"; return; fi
  [ -f "$directory/$key" ] || die "missing transaction recovery for $target"
  temporary="$(mktemp "$(dirname "$target")/.$(basename "$target").restore.XXXXXX")"
  cp -- "$directory/$key" "$temporary"
  chmod "$(cat "$directory/$key.mode")" "$temporary"
  mv -f -- "$temporary" "$target"
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

generic_restore_to() {
  local target="$1" kind="$2" destination="$3"
  plane_validate_target_path "$target"
  python3 "$PLANE_BACKUP_TOOL" restore --root "$MEGAI_HOME/backups/plane" \
    --target "$target" --kind "$kind" --destination "$destination" >/dev/null \
    || die "no valid private target-bound $kind backup; refusing restore: $target"
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
  local candidate="$1" backup_current="${2:-1}" expected_dir="${3:-${PLANE_EXPECTED_DIR:-}}" expected_key="${4:-${PLANE_EXPECTED_KEY:-}}"
  [ ! -L "$candidate" ] && [ -f "$candidate" ] || die "invalid staged Pi MCP candidate"
  if [ -n "$expected_dir" ] && [ "${PLANE_EXPECTED_TARGET:-$PLANE_CONFIG}" = "$PLANE_CONFIG" ]; then plane_txn_assert_original "$expected_dir" "$PLANE_CONFIG" "$expected_key" || return 1; fi
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
      --client) [ "$#" -ge 2 ] || die "--client requires pi, codex, cc, omp, or all"; client="$2"; shift 2;;
      --client=*) client="${arg#*=}"; shift;;
      --replace-asana) replace_asana=true; shift;;
      -h|--help) plane_usage; return 0;;
      *) die "unknown Plane setup option: $arg";;
    esac
  done
  [ -n "$workspace" ] || die "--workspace is required"
  case "$client" in pi|codex|cc|omp|all);; *) die "--client must be pi, codex, cc, omp, or all";; esac
  token_file="$(plane_absolute_path "$token_file")"
  plane_require_tools; plane_validate_token_file "$token_file" "$workspace"
  local replace_flag=0; [ "$replace_asana" = true ] && replace_flag=1
  local pi_candidate codex_candidate cc_candidate omp_candidate cc_config omp_config txn_dir
  cc_config="$PLANE_CC_CONFIG"; omp_config=""
  if [ "$client" = omp ] || [ "$client" = all ]; then omp_config="$(plane_omp_config)"; fi
  pi_candidate=""; codex_candidate=""; cc_candidate=""; omp_candidate=""
  if [ "$client" = pi ] || [ "$client" = all ]; then
    mkdir -p "$PLANE_AGENT"; pi_candidate="$(mktemp "$PLANE_AGENT/.mcp.json.stage.XXXXXX")"
  fi
  if [ "$client" = codex ] || [ "$client" = all ]; then
    mkdir -p "$(dirname "$PLANE_CODEX_CONFIG")"; codex_candidate="$(mktemp "$(dirname "$PLANE_CODEX_CONFIG")/.config.toml.stage.XXXXXX")"
  fi
  if [ "$client" = cc ] || [ "$client" = all ]; then
    mkdir -p "$(dirname "$cc_config")"; cc_candidate="$(mktemp "$(dirname "$cc_config")/.claude.json.stage.XXXXXX")"
  fi
  if [ "$client" = omp ] || [ "$client" = all ]; then
    mkdir -p "$(dirname "$omp_config")"; omp_candidate="$(mktemp "$(dirname "$omp_config")/.mcp.json.stage.XXXXXX")"
  fi
  trap 'rm -f -- "$pi_candidate" "$codex_candidate" "$cc_candidate" "$omp_candidate"' RETURN
  # Capture selected originals before rendering any candidate.
  txn_dir="$(plane_txn_directory)"
  if [ "$client" = pi ] || [ "$client" = all ]; then plane_txn_snapshot "$txn_dir" "$PLANE_CONFIG" pi; fi
  if [ "$client" = codex ] || [ "$client" = all ]; then plane_txn_snapshot "$txn_dir" "$PLANE_CODEX_CONFIG" codex; fi
  if [ "$client" = cc ] || [ "$client" = all ]; then plane_txn_snapshot "$txn_dir" "$cc_config" cc; fi
  if [ "$client" = omp ] || [ "$client" = all ]; then plane_txn_snapshot "$txn_dir" "$omp_config" omp; fi

  # Stage every requested client before any target is replaced.
  if [ "$client" = pi ] || [ "$client" = all ]; then plane_stage_setup "$pi_candidate" "$token_file" "$workspace" "$replace_asana"; fi
  if [ "$client" = codex ] || [ "$client" = all ]; then
    [ -f "$PLANE_CODEX_HELPER" ] || die "Plane Codex helper is missing: $PLANE_CODEX_HELPER"
    bash "$PLANE_CODEX_HELPER" stage-setup "$workspace" "$token_file" "$replace_flag" "$codex_candidate"
  fi
  if [ "$client" = cc ] || [ "$client" = all ]; then generic_stage_setup "$cc_config" "$cc_candidate" "$token_file" "$workspace"; fi
  if [ "$client" = omp ] || [ "$client" = all ]; then generic_stage_setup "$omp_config" "$omp_candidate" "$token_file" "$workspace"; fi
  # All preflight/staging above completes before this first mutation.
  if [ "$client" = pi ] || [ "$client" = all ]; then
    plane_txn_assert_original "$txn_dir" "$PLANE_CONFIG" pi || die "Plane Pi changed during staging; no clients were mutated"
    if ! plane_commit "$pi_candidate" 1 "$txn_dir" pi; then plane_txn_restore "$txn_dir" "$PLANE_CONFIG" pi; die "Plane Pi commit failed; staged clients were rolled back"; fi
    plane_txn_mark_after "$txn_dir" "$PLANE_CONFIG" pi
  fi
  if [ "$client" = codex ] || [ "$client" = all ]; then
    if ! plane_txn_assert_original "$txn_dir" "$PLANE_CODEX_CONFIG" codex; then
      plane_txn_rollback "$txn_dir" "$PLANE_CONFIG" pi || die "Plane Codex preflight rollback refused; recovery evidence retained"
      die "Plane Codex changed during staging; prior clients were rolled back"
    fi
    if ! bash "$PLANE_CODEX_HELPER" commit "$codex_candidate"; then
      plane_txn_rollback "$txn_dir" "$PLANE_CONFIG" pi "$PLANE_CODEX_CONFIG" codex || die "Plane Codex rollback refused; recovery evidence retained"
      die "Plane Codex commit failed; staged clients were rolled back"
    fi
    plane_txn_mark_after "$txn_dir" "$PLANE_CODEX_CONFIG" codex
  fi
  if [ "$client" = cc ] || [ "$client" = all ]; then
    if ! plane_txn_assert_original "$txn_dir" "$cc_config" cc; then
      if ! plane_txn_rollback "$txn_dir" "$PLANE_CONFIG" pi "$PLANE_CODEX_CONFIG" codex; then die "Plane Claude Code preflight rollback refused; recovery evidence retained"; fi
      die "Plane Claude Code changed during staging; prior clients were rolled back"
    fi
    if ! generic_commit "$cc_config" "$cc_candidate" cc; then
      if ! plane_txn_rollback "$txn_dir" "$PLANE_CONFIG" pi "$PLANE_CODEX_CONFIG" codex "$cc_config" cc; then
        die "Plane Claude Code rollback refused; recovery evidence retained"
      fi
      die "Plane Claude Code commit failed; staged clients were rolled back"
    fi
    plane_txn_mark_after "$txn_dir" "$cc_config" cc
  fi
  if [ "$client" = omp ] || [ "$client" = all ]; then
    if ! plane_txn_assert_original "$txn_dir" "$omp_config" omp; then
      if ! plane_txn_rollback "$txn_dir" "$PLANE_CONFIG" pi "$PLANE_CODEX_CONFIG" codex "$cc_config" cc; then die "Plane OMP preflight rollback refused; recovery evidence retained"; fi
      die "Plane OMP changed during staging; prior clients were rolled back"
    fi
    if ! generic_commit "$omp_config" "$omp_candidate" omp; then
      if ! plane_txn_rollback "$txn_dir" "$PLANE_CONFIG" pi "$PLANE_CODEX_CONFIG" codex "$cc_config" cc "$omp_config" omp; then
        die "Plane OMP rollback refused; recovery evidence retained"
      fi
      die "Plane OMP commit failed; staged clients were rolled back"
    fi
    plane_txn_mark_after "$txn_dir" "$omp_config" omp
  fi
  trap - RETURN
  ok "Plane MCP configured (client=$client, workspace=$workspace)"
}

plane_status() {
  local client=pi arg
  while [ "$#" -gt 0 ]; do case "$1" in --client) [ "$#" -ge 2 ] || die "--client requires a value"; client="$2"; shift 2;; --client=*) client="${1#*=}"; shift;; *) die "unknown Plane status option: $1";; esac; done
  case "$client" in codex) exec bash "$PLANE_CODEX_HELPER" status;; cc|omp) ;; all) plane_status --client pi; bash "$PLANE_CODEX_HELPER" status; plane_status --client cc; plane_status --client omp; return;; pi);; *) die "--client must be pi, codex, cc, omp, or all";; esac
  plane_require_tools
  if [ "$client" = cc ] || [ "$client" = omp ]; then
    local generic_config; generic_config="$PLANE_CC_CONFIG"; [ "$client" = omp ] && generic_config="$(plane_omp_config)"
    plane_validate_generic_config "$generic_config"
    case "$(generic_entry_kind "$generic_config")" in
      missing) echo "Plane MCP ($client): not configured";;
      unmanaged) echo "Plane MCP ($client): unmanaged plane entry preserved" >&2; return 1;;
      owned)
        local remote_token remote_workspace
        remote_token="$(jq -r '.mcpServers.plane.args[2]' "$generic_config")"
        remote_workspace="$(jq -r '.mcpServers.plane.args[4]' "$generic_config")"
        if python3 "$PLANE_REMOTE_HELPER" --check --token-file "$remote_token" --workspace "$remote_workspace" >/dev/null 2>&1; then
          echo "Plane MCP ($client): configured (credential and bridge available)"
        else
          echo "Plane MCP ($client): configured but credential or bridge unavailable" >&2
          return 1
        fi;;
    esac
    return
  fi
  plane_validate_config
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
  case "$client" in pi|codex|cc|omp|all);; *) die "--client must be pi, codex, cc, omp, or all";; esac
  plane_require_tools
  local cc_config omp_config
  cc_config="$PLANE_CC_CONFIG"; omp_config=""
  if [ "$client" = omp ] || [ "$client" = all ]; then omp_config="$(plane_omp_config)"; fi
  local pi_candidate codex_candidate cc_candidate omp_candidate txn_dir
  pi_candidate=""; codex_candidate=""; cc_candidate=""; omp_candidate=""
  if [ "$client" = pi ] || [ "$client" = all ]; then
    mkdir -p "$PLANE_AGENT"; pi_candidate="$(mktemp "$PLANE_AGENT/.mcp.json.stage.XXXXXX")"
  fi
  if [ "$client" = codex ] || [ "$client" = all ]; then
    mkdir -p "$(dirname "$PLANE_CODEX_CONFIG")"; codex_candidate="$(mktemp "$(dirname "$PLANE_CODEX_CONFIG")/.config.toml.stage.XXXXXX")"
  fi
  if [ "$client" = cc ] || [ "$client" = all ]; then
    mkdir -p "$(dirname "$cc_config")"; cc_candidate="$(mktemp "$(dirname "$cc_config")/.claude.json.stage.XXXXXX")"
  fi
  if [ "$client" = omp ] || [ "$client" = all ]; then
    mkdir -p "$(dirname "$omp_config")"; omp_candidate="$(mktemp "$(dirname "$omp_config")/.mcp.json.stage.XXXXXX")"
  fi
  trap 'rm -f -- "$pi_candidate" "$codex_candidate" "$cc_candidate" "$omp_candidate"' RETURN
  txn_dir="$(plane_txn_directory)"
  if [ "$client" = pi ] || [ "$client" = all ]; then plane_txn_snapshot "$txn_dir" "$PLANE_CONFIG" pi; fi
  if [ "$client" = codex ] || [ "$client" = all ]; then plane_txn_snapshot "$txn_dir" "$PLANE_CODEX_CONFIG" codex; fi
  if [ "$client" = cc ] || [ "$client" = all ]; then plane_txn_snapshot "$txn_dir" "$cc_config" cc; fi
  if [ "$client" = omp ] || [ "$client" = all ]; then plane_txn_snapshot "$txn_dir" "$omp_config" omp; fi
  if [ "$client" = pi ] || [ "$client" = all ]; then plane_stage_remove "$pi_candidate"; fi
  if [ "$client" = codex ] || [ "$client" = all ]; then bash "$PLANE_CODEX_HELPER" stage-remove "$codex_candidate"; fi
  if [ "$client" = cc ] || [ "$client" = all ]; then generic_stage_remove "$cc_config" "$cc_candidate"; fi
  if [ "$client" = omp ] || [ "$client" = all ]; then generic_stage_remove "$omp_config" "$omp_candidate"; fi
  if { [ "$client" = pi ] || [ "$client" = all ]; } && [ -f "$PLANE_CONFIG" ]; then
    plane_txn_assert_original "$txn_dir" "$PLANE_CONFIG" pi || die "Plane Pi changed during staging; no clients were mutated"
    if ! plane_commit "$pi_candidate" 1 "$txn_dir" pi; then plane_txn_restore "$txn_dir" "$PLANE_CONFIG" pi; die "Plane Pi removal failed; staged clients were rolled back"; fi
    plane_txn_mark_after "$txn_dir" "$PLANE_CONFIG" pi
  fi
  if { [ "$client" = codex ] || [ "$client" = all ]; } && [ -f "$PLANE_CODEX_CONFIG" ]; then
    if ! plane_txn_assert_original "$txn_dir" "$PLANE_CODEX_CONFIG" codex; then
      plane_txn_rollback "$txn_dir" "$PLANE_CONFIG" pi || die "Plane Codex removal rollback refused; recovery evidence retained"
      die "Plane Codex changed during staging; prior clients were rolled back"
    fi
    if ! bash "$PLANE_CODEX_HELPER" commit "$codex_candidate"; then
      if ! plane_txn_rollback "$txn_dir" "$PLANE_CONFIG" pi "$PLANE_CODEX_CONFIG" codex; then
        die "Plane Codex removal rollback refused; recovery evidence retained"
      fi
      die "Plane Codex removal failed; staged clients were rolled back"
    fi
    plane_txn_mark_after "$txn_dir" "$PLANE_CODEX_CONFIG" codex
  fi
  if { [ "$client" = cc ] || [ "$client" = all ]; } && [ -f "$cc_config" ]; then
    if ! plane_txn_assert_original "$txn_dir" "$cc_config" cc; then
      plane_txn_rollback "$txn_dir" "$PLANE_CONFIG" pi "$PLANE_CODEX_CONFIG" codex || die "Plane Claude Code removal rollback refused; recovery evidence retained"
      die "Plane Claude Code changed during staging; prior clients were rolled back"
    fi
    if ! generic_commit "$cc_config" "$cc_candidate" cc; then
      if ! plane_txn_rollback "$txn_dir" "$PLANE_CONFIG" pi "$PLANE_CODEX_CONFIG" codex "$cc_config" cc; then
        die "Plane Claude Code removal rollback refused; recovery evidence retained"
      fi
      die "Plane Claude Code removal failed; staged clients were rolled back"
    fi
    plane_txn_mark_after "$txn_dir" "$cc_config" cc
  fi
  if { [ "$client" = omp ] || [ "$client" = all ]; } && [ -f "$omp_config" ]; then
    if ! plane_txn_assert_original "$txn_dir" "$omp_config" omp; then
      plane_txn_rollback "$txn_dir" "$PLANE_CONFIG" pi "$PLANE_CODEX_CONFIG" codex "$cc_config" cc || die "Plane OMP removal rollback refused; recovery evidence retained"
      die "Plane OMP changed during staging; prior clients were rolled back"
    fi
    if ! generic_commit "$omp_config" "$omp_candidate" omp; then
      if ! plane_txn_rollback "$txn_dir" "$PLANE_CONFIG" pi "$PLANE_CODEX_CONFIG" codex "$cc_config" cc "$omp_config" omp; then
        die "Plane OMP removal rollback refused; recovery evidence retained"
      fi
      die "Plane OMP removal failed; staged clients were rolled back"
    fi
    plane_txn_mark_after "$txn_dir" "$omp_config" omp
  fi
  trap - RETURN
  ok "Plane MCP removed (client=$client)"
}

plane_restore() {
  local client=pi arg
  while [ "$#" -gt 0 ]; do case "$1" in --client) [ "$#" -ge 2 ] || die "--client requires a value"; client="$2"; shift 2;; --client=*) client="${1#*=}"; shift;; *) die "unknown Plane restore option: $1";; esac; done
  case "$client" in pi|codex|cc|omp|all);; *) die "--client must be pi, codex, cc, omp, or all";; esac
  plane_require_tools
  local cc_config omp_config
  cc_config="$PLANE_CC_CONFIG"; omp_config=""
  if [ "$client" = omp ] || [ "$client" = all ]; then omp_config="$(plane_omp_config)"; fi
  local pi_candidate codex_candidate cc_candidate omp_candidate txn_dir
  pi_candidate=""; codex_candidate=""; cc_candidate=""; omp_candidate=""
  if [ "$client" = pi ] || [ "$client" = all ]; then
    mkdir -p "$PLANE_AGENT"; pi_candidate="$(mktemp "$PLANE_AGENT/.mcp.json.stage.XXXXXX")"
  fi
  if [ "$client" = codex ] || [ "$client" = all ]; then
    mkdir -p "$(dirname "$PLANE_CODEX_CONFIG")"; codex_candidate="$(mktemp "$(dirname "$PLANE_CODEX_CONFIG")/.config.toml.stage.XXXXXX")"
  fi
  if [ "$client" = cc ] || [ "$client" = all ]; then
    mkdir -p "$(dirname "$cc_config")"; cc_candidate="$(mktemp "$(dirname "$cc_config")/.claude.json.stage.XXXXXX")"
  fi
  if [ "$client" = omp ] || [ "$client" = all ]; then
    mkdir -p "$(dirname "$omp_config")"; omp_candidate="$(mktemp "$(dirname "$omp_config")/.mcp.json.stage.XXXXXX")"
  fi
  trap 'rm -f -- "$pi_candidate" "$codex_candidate" "$cc_candidate" "$omp_candidate"' RETURN
  txn_dir="$(plane_txn_directory)"
  if [ "$client" = pi ] || [ "$client" = all ]; then plane_txn_snapshot "$txn_dir" "$PLANE_CONFIG" pi; fi
  if [ "$client" = codex ] || [ "$client" = all ]; then plane_txn_snapshot "$txn_dir" "$PLANE_CODEX_CONFIG" codex; fi
  if [ "$client" = cc ] || [ "$client" = all ]; then plane_txn_snapshot "$txn_dir" "$cc_config" cc; fi
  if [ "$client" = omp ] || [ "$client" = all ]; then plane_txn_snapshot "$txn_dir" "$omp_config" omp; fi
  if [ "$client" = pi ] || [ "$client" = all ]; then plane_restore_to "$pi_candidate"; fi
  if [ "$client" = codex ] || [ "$client" = all ]; then bash "$PLANE_CODEX_HELPER" stage-restore "$codex_candidate"; fi
  if [ "$client" = cc ] || [ "$client" = all ]; then generic_restore_to "$cc_config" cc "$cc_candidate"; fi
  if [ "$client" = omp ] || [ "$client" = all ]; then generic_restore_to "$omp_config" omp "$omp_candidate"; fi
  if [ "$client" = pi ] || [ "$client" = all ]; then
    plane_txn_assert_original "$txn_dir" "$PLANE_CONFIG" pi || die "Plane Pi changed during restore staging; no clients were mutated"
    if ! plane_commit "$pi_candidate" 0 "$txn_dir" pi; then die "Plane Pi restore failed; recovery evidence retained"; fi
    plane_txn_mark_after "$txn_dir" "$PLANE_CONFIG" pi
  fi
  if [ "$client" = codex ] || [ "$client" = all ]; then
    if ! plane_txn_assert_original "$txn_dir" "$PLANE_CODEX_CONFIG" codex; then
      plane_txn_restore "$txn_dir" "$PLANE_CONFIG" pi || die "Plane Codex restore rollback refused; recovery evidence retained"
      die "Plane Codex changed during restore staging; prior clients were rolled back"
    fi
    if ! bash "$PLANE_CODEX_HELPER" commit "$codex_candidate" 0; then
      plane_txn_restore "$txn_dir" "$PLANE_CONFIG" pi || die "Plane Codex restore rollback refused; recovery evidence retained"
      die "Plane Codex restore failed; staged clients were rolled back"
    fi
    plane_txn_mark_after "$txn_dir" "$PLANE_CODEX_CONFIG" codex
  fi
  if [ "$client" = cc ] || [ "$client" = all ]; then
    if ! plane_txn_assert_original "$txn_dir" "$cc_config" cc; then
      plane_txn_rollback "$txn_dir" "$PLANE_CONFIG" pi "$PLANE_CODEX_CONFIG" codex || die "Plane CC restore rollback refused; recovery evidence retained"
      die "Plane Claude Code changed during restore staging; prior clients were rolled back"
    fi
    if ! generic_commit "$cc_config" "$cc_candidate" cc 0; then
      plane_txn_rollback "$txn_dir" "$PLANE_CONFIG" pi "$PLANE_CODEX_CONFIG" codex || die "Plane CC restore rollback refused; recovery evidence retained"
      die "Plane Claude Code restore failed; staged clients were rolled back"
    fi
    plane_txn_mark_after "$txn_dir" "$cc_config" cc
  fi
  if [ "$client" = omp ] || [ "$client" = all ]; then
    if ! plane_txn_assert_original "$txn_dir" "$omp_config" omp; then
      plane_txn_rollback "$txn_dir" "$PLANE_CONFIG" pi "$PLANE_CODEX_CONFIG" codex "$cc_config" cc || die "Plane OMP restore rollback refused; recovery evidence retained"
      die "Plane OMP changed during restore staging; prior clients were rolled back"
    fi
    if ! generic_commit "$omp_config" "$omp_candidate" omp 0; then
      plane_txn_rollback "$txn_dir" "$PLANE_CONFIG" pi "$PLANE_CODEX_CONFIG" codex "$cc_config" cc || die "Plane OMP restore rollback refused; recovery evidence retained"
      die "Plane OMP restore failed; staged clients were rolled back"
    fi
    plane_txn_mark_after "$txn_dir" "$omp_config" omp
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

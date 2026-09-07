#!/usr/bin/env bash
# Synthetic Plane MCP lifecycle coverage. No live Plane request is made.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

export HOME="$TMP/home"
export MEGAI_HOME="$TMP/megai"
export PI_CODING_AGENT_DIR="$HOME/.pi/agent"
mkdir -p "$HOME" "$PI_CODING_AGENT_DIR" "$MEGAI_HOME/lib" "$MEGAI_HOME/backups"
cp "$ROOT/lib/ui.sh" "$ROOT/lib/state.sh" "$ROOT/lib/detect.sh" "$ROOT/lib/banner.sh" "$ROOT/lib/wire_pi.sh" "$ROOT/lib/plane_mcp.sh" "$ROOT/lib/plane_codex.sh" "$ROOT/lib/plane_mcp_headers.py" "$ROOT/lib/plane_mcp_remote.py" "$ROOT/lib/install_taskflow_policy.py" "$MEGAI_HOME/lib/"
printf '{"tools":{},"agents":{},"projects":{}}\n' >"$MEGAI_HOME/state.json"

TOKEN_FILE="$TMP/plane-token"
TOKEN='synthetic-plane-token-do-not-print'
printf '%s\n' "$TOKEN" >"$TOKEN_FILE"
chmod 600 "$TOKEN_FILE"

cat >"$PI_CODING_AGENT_DIR/mcp.json" <<'JSON'
{
  "settings": {"hostConfigDiscovery": "off"},
  "mcpServers": {
    "asana": {
      "url": "https://mcp.asana.com/v2/mcp",
      "auth": "oauth",
      "oauth": {"scope": "default"},
      "lifecycle": "keep-alive"
    },
    "unrelated": {"url": "https://example.test/mcp", "auth": "oauth"}
  }
}
JSON

run_plane() { bash "$ROOT/bin/megai" plane "$@"; }

before_setup="$TMP/before-setup.json"
cp "$PI_CODING_AGENT_DIR/mcp.json" "$before_setup"
setup_output="$(run_plane setup --workspace brodev --token-file "$TOKEN_FILE")"
! grep -Fq "$TOKEN" <<<"$setup_output"
! grep -Fq "$TOKEN" "$PI_CODING_AGENT_DIR/mcp.json"
jq -e --arg token "$TOKEN_FILE" --arg helper "$MEGAI_HOME/lib/plane_mcp_headers.py" '
  .settings.hostConfigDiscovery == "off"
  and .mcpServers.asana.auth == "oauth"
  and .mcpServers.asana.oauth.scope == "default"
  and .mcpServers.unrelated.url == "https://example.test/mcp"
  and .mcpServers.plane.url == "https://mcp.plane.so/http/api-key/mcp"
  and .mcpServers.plane.auth == false
  and .mcpServers.plane.lifecycle == "lazy"
  and .mcpServers.plane.requestHeadersCommand.command == "python3"
  and .mcpServers.plane.requestHeadersCommand.args == [$helper, "--token-file", $token, "--workspace", "brodev"]
' "$PI_CODING_AGENT_DIR/mcp.json" >/dev/null
[ "$(find "$MEGAI_HOME/backups" -type f -name 'pi-plane-mcp.json.bak.*' | wc -l | tr -d ' ')" = 1 ]
backup_file="$(find "$MEGAI_HOME/backups" -type f -name 'pi-plane-mcp.json.bak.*' -print -quit)"
cmp "$backup_file" "$before_setup"
config_mode="$(stat -c '%a' "$PI_CODING_AGENT_DIR/mcp.json" 2>/dev/null || stat -f '%Lp' "$PI_CODING_AGENT_DIR/mcp.json")"
backup_mode="$(stat -c '%a' "$backup_file" 2>/dev/null || stat -f '%Lp' "$backup_file")"
[ "$config_mode" = 600 ]
[ "$backup_mode" = 600 ]

# Invoke exactly the generated requestHeadersCommand with the adapter's v1
# envelope; do not bypass the configured interpreter/argument contract.
plane_command="$(jq -r '.mcpServers.plane.requestHeadersCommand.command' "$PI_CODING_AGENT_DIR/mcp.json")"
plane_args=()
while IFS= read -r plane_arg; do plane_args+=("$plane_arg"); done < <(jq -r '.mcpServers.plane.requestHeadersCommand.args[]' "$PI_CODING_AGENT_DIR/mcp.json")
valid_envelope='{"version":1,"method":"POST","url":"https://mcp.plane.so/http/api-key/mcp","bodyBase64":""}'
headers="$(printf '%s' "$valid_envelope" | "$plane_command" "${plane_args[@]}")"
printf '%s' "$headers" | jq -e --arg token "Bearer $TOKEN" '.Authorization == $token and .["x-workspace-slug"] == "brodev"' >/dev/null

# Explicit all-client cutover removes only the legacy entries and keeps the
# Codex credential out of TOML, argv, stdout, and stderr.
export CODEX_HOME="$TMP/custom-codex"
mkdir -p "$CODEX_HOME"
cat >"$CODEX_HOME/config.toml" <<'TOML'
keep = true

[mcp_servers.asana]
command = "legacy-asana"

[mcp_servers.unrelated]
command = "keep-me"
TOML
cutover_output="$(run_plane setup --workspace brodev --token-file "$TOKEN_FILE" --client all --replace-asana 2>&1)"
! grep -Fq "$TOKEN" <<<"$cutover_output"
! grep -Fq "$TOKEN" "$CODEX_HOME/config.toml"
grep -q 'megai-plane-managed' "$CODEX_HOME/config.toml"
! grep -q 'mcp_servers.asana' "$CODEX_HOME/config.toml"
grep -q 'command = "keep-me"' "$CODEX_HOME/config.toml"
python3 -c 'import sys,tomllib; tomllib.load(open(sys.argv[1], "rb"))' "$CODEX_HOME/config.toml"
[ "$(find "$MEGAI_HOME/backups" -type f -name 'codex-plane-mcp.toml.bak.*' | wc -l | tr -d ' ')" = 1 ]
mkdir -p "$TMP/fake-bin"
cat >"$TMP/fake-bin/npx" <<'SH'
#!/usr/bin/env bash
[ "$MEGAI_PLANE_AUTH" = "Bearer $EXPECTED_TOKEN" ]
printf '%s\n' "$*" >"$ARGV_LOG"
SH
chmod +x "$TMP/fake-bin/npx"
EXPECTED_TOKEN="$TOKEN" ARGV_LOG="$TMP/npx-argv" PATH="$TMP/fake-bin:$PATH" \
  python3 "$MEGAI_HOME/lib/plane_mcp_remote.py" --token-file "$TOKEN_FILE" --workspace brodev >/dev/null 2>&1
! grep -Fq "$TOKEN" "$TMP/npx-argv"
grep -Fq 'Authorization:${MEGAI_PLANE_AUTH}' "$TMP/npx-argv"
grep -Fq 'x-workspace-slug:${MEGAI_PLANE_WORKSPACE}' "$TMP/npx-argv"
cp "$CODEX_HOME/config.toml" "$TMP/codex-repeat"
run_plane setup --workspace brodev --token-file "$TOKEN_FILE" --client codex --replace-asana >/dev/null
cmp "$CODEX_HOME/config.toml" "$TMP/codex-repeat"
run_plane restore --client codex >/dev/null
grep -q 'mcp_servers.asana' "$CODEX_HOME/config.toml"
run_plane restore --client pi >/dev/null
jq -e '.mcpServers.asana.auth == "oauth"' "$PI_CODING_AGENT_DIR/mcp.json" >/dev/null
run_plane setup --workspace brodev --token-file "$TOKEN_FILE" --client codex --replace-asana >/dev/null

# Endpoint and envelope binding fail before any credential output.
invalid_output="$TMP/invalid-header-output"
for invalid_url in \
  "http://mcp.plane.so/http/api-key/mcp" \
  "https://mcp.plane.so:443/http/api-key/mcp" \
  "https://user@mcp.plane.so/http/api-key/mcp" \
  "https://mcp.plane.so/other" \
  "https://mcp.plane.so/http/api-key/mcp?discover=1"; do
  invalid_envelope="{\"version\":1,\"method\":\"POST\",\"url\":\"$invalid_url\",\"bodyBase64\":\"\"}"
  if printf '%s' "$invalid_envelope" | "$plane_command" "${plane_args[@]}" >"$invalid_output" 2>/dev/null; then exit 1; fi
  [ ! -s "$invalid_output" ]
done
if printf '%s' '{"version":2,"method":"POST","url":"https://mcp.plane.so/http/api-key/mcp","bodyBase64":""}' | "$plane_command" "${plane_args[@]}" >"$invalid_output" 2>/dev/null; then exit 1; fi
[ ! -s "$invalid_output" ]
if printf '%s' '{"version":1,"method":"POST","url":"https://mcp.plane.so/http/api-key/mcp"}' | "$plane_command" "${plane_args[@]}" >"$invalid_output" 2>/dev/null; then exit 1; fi
[ ! -s "$invalid_output" ]
if printf '%s' '{"version":1,"method":"POST","url":"https://mcp.plane.so/http/api-key/mcp","bodyBase64":"%%%"}' | "$plane_command" "${plane_args[@]}" >"$invalid_output" 2>/dev/null; then exit 1; fi
[ ! -s "$invalid_output" ]
check_output="$("$plane_command" "${plane_args[@]}" --check </dev/null)"
[ -z "$check_output" ]

# Repeat setup is a no-op: no duplicate entry and no second backup.
cp "$PI_CODING_AGENT_DIR/mcp.json" "$TMP/repeat-before"
run_plane setup --workspace brodev --token-file "$TOKEN_FILE" >/dev/null
cmp "$PI_CODING_AGENT_DIR/mcp.json" "$TMP/repeat-before"
[ "$(find "$MEGAI_HOME/backups" -type f -name 'pi-plane-mcp.json.bak.*' | wc -l | tr -d ' ')" = 2 ]

# Owned-entry customizations, including disabled state, survive setup refresh.
jq '.mcpServers.plane.disabled = true | .mcpServers.plane.directTools = false | .mcpServers.plane.lifecycle = "keep-alive"' \
  "$PI_CODING_AGENT_DIR/mcp.json" >"$TMP/custom.json"
mv "$TMP/custom.json" "$PI_CODING_AGENT_DIR/mcp.json"
run_plane setup --workspace brodev --token-file "$TOKEN_FILE" >/dev/null
jq -e '.mcpServers.plane.disabled == true and .mcpServers.plane.directTools == false and .mcpServers.plane.lifecycle == "keep-alive"' \
  "$PI_CODING_AGENT_DIR/mcp.json" >/dev/null
cp "$PI_CODING_AGENT_DIR/mcp.json" "$TMP/custom-repeat-before"
run_plane setup --workspace brodev --token-file "$TOKEN_FILE" >/dev/null
cmp "$PI_CODING_AGENT_DIR/mcp.json" "$TMP/custom-repeat-before"

# Status and setup diagnostics never include the synthetic credential.
status_output="$(run_plane status 2>&1)"
! grep -Fq "$TOKEN" <<<"$status_output"
grep -Fq 'credential=available' <<<"$status_output"

# Normal Pi wiring preserves the enabled Plane entry and does not auth/connect.
cp -R "$ROOT/pi-skill" "$ROOT/task-flow" "$ROOT/skills" "$MEGAI_HOME/"
bash "$MEGAI_HOME/lib/wire_pi.sh" >/dev/null 2>&1
jq -e '.mcpServers.plane.requestHeadersCommand.args[4] == "brodev" and .mcpServers.asana.auth == "oauth"' "$PI_CODING_AGENT_DIR/mcp.json" >/dev/null
bash "$MEGAI_HOME/lib/wire_pi.sh" --remove >/dev/null 2>&1
jq -e '.mcpServers.plane and .mcpServers.asana.auth == "oauth"' "$PI_CODING_AGENT_DIR/mcp.json" >/dev/null
bash "$MEGAI_HOME/lib/wire_pi.sh" >/dev/null 2>&1

# Missing and unsafe credentials fail closed without changing config.
cp "$PI_CODING_AGENT_DIR/mcp.json" "$TMP/missing-before"
rm "$TOKEN_FILE"
if run_plane setup --workspace brodev --token-file "$TOKEN_FILE" >/dev/null 2>&1; then exit 1; fi
cmp "$PI_CODING_AGENT_DIR/mcp.json" "$TMP/missing-before"
printf '%s\n' "$TOKEN" >"$TOKEN_FILE"
chmod 644 "$TOKEN_FILE"
if run_plane setup --workspace brodev --token-file "$TOKEN_FILE" >/dev/null 2>&1; then exit 1; fi
cmp "$PI_CODING_AGENT_DIR/mcp.json" "$TMP/missing-before"
chmod 600 "$TOKEN_FILE"
ln -s "$TOKEN_FILE" "$TMP/token-link"
if run_plane setup --workspace brodev --token-file "$TMP/token-link" >/dev/null 2>&1; then exit 1; fi
cmp "$PI_CODING_AGENT_DIR/mcp.json" "$TMP/missing-before"

# Malformed configuration is rejected before any write.
printf '{not-json\n' >"$PI_CODING_AGENT_DIR/mcp.json"
cp "$PI_CODING_AGENT_DIR/mcp.json" "$TMP/malformed-before"
if run_plane setup --workspace brodev --token-file "$TOKEN_FILE" >/dev/null 2>&1; then exit 1; fi
cmp "$PI_CODING_AGENT_DIR/mcp.json" "$TMP/malformed-before"

# Codex malformed TOML is also rejected before any write.
codex_before="$TMP/codex-malformed-before"
printf 'broken = [\n' >"$CODEX_HOME/config.toml"
cp "$CODEX_HOME/config.toml" "$codex_before"
if run_plane setup --workspace brodev --token-file "$TOKEN_FILE" --client codex >/dev/null 2>&1; then exit 1; fi
cmp "$CODEX_HOME/config.toml" "$codex_before"
run_plane restore --client codex >/dev/null

# A pre-existing user-owned plane name is never adopted or removed.
cat >"$PI_CODING_AGENT_DIR/mcp.json" <<'JSON'
{"mcpServers":{"plane":{"url":"https://user.example/mcp","auth":"oauth"},"asana":{"url":"https://mcp.asana.com/v2/mcp","auth":"oauth"}}}
JSON
cp "$PI_CODING_AGENT_DIR/mcp.json" "$TMP/unmanaged-before"
if run_plane setup --workspace brodev --token-file "$TOKEN_FILE" >/dev/null 2>&1; then exit 1; fi
cmp "$PI_CODING_AGENT_DIR/mcp.json" "$TMP/unmanaged-before"
if run_plane remove >/dev/null 2>&1; then exit 1; fi
cmp "$PI_CODING_AGENT_DIR/mcp.json" "$TMP/unmanaged-before"
jq 'del(.mcpServers.plane)' "$PI_CODING_AGENT_DIR/mcp.json" >"$TMP/no-plane.json"
mv "$TMP/no-plane.json" "$PI_CODING_AGENT_DIR/mcp.json"

# Restore owned config, then remove only that entry. Removal is safe even if the
# token later disappears, and Asana/OAuth configuration remains untouched.
run_plane setup --workspace brodev --token-file "$TOKEN_FILE" >/dev/null
jq -e '.mcpServers.plane and .mcpServers.asana.auth == "oauth"' "$PI_CODING_AGENT_DIR/mcp.json" >/dev/null
rm "$TOKEN_FILE"
remove_output="$(run_plane remove 2>&1)"
! grep -Fq "$TOKEN" <<<"$remove_output"
jq -e '(.mcpServers.plane | not) and .mcpServers.asana.auth == "oauth"' "$PI_CODING_AGENT_DIR/mcp.json" >/dev/null
run_plane remove >/dev/null

# Config symlinks are refused rather than followed.
rm "$PI_CODING_AGENT_DIR/mcp.json"
printf '{"mcpServers":{}}\n' >"$TMP/config-target"
ln -s "$TMP/config-target" "$PI_CODING_AGENT_DIR/mcp.json"
if run_plane setup --workspace brodev --token-file "$TMP/token-link" >/dev/null 2>&1; then exit 1; fi

bash -n "$ROOT/bin/megai" "$ROOT/lib/plane_mcp.sh"
python3 -m py_compile "$ROOT/lib/plane_mcp_headers.py"
rm -rf "$ROOT/lib/__pycache__"
echo 'Plane MCP synthetic lifecycle: ok'

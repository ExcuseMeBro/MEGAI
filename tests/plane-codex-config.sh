#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
HELPER="$TMP/remote.py"
printf '#!/usr/bin/env python3\n' >"$HELPER"
CONFIG="$TMP/config.toml"
cat >"$CONFIG" <<EOF
keep = true

# >>> megai-plane-managed (do not edit) >>>
[mcp_servers."plane"]
command = "$HELPER"
args = ["--token-file", "$TMP/token", "--workspace", "brodev"]
# <<< megai-plane-managed <<<

[mcp_servers.'asana']
command = "legacy"

[mcp_servers.'asana'.env]
TOKEN = "never-copy"
EOF
[ "$(python3 "$ROOT/lib/plane_codex_config.py" inspect --file "$CONFIG" --helper "$HELPER")" = owned ]
python3 "$ROOT/lib/plane_codex_config.py" validate --file "$CONFIG"
stripped="$TMP/stripped"
python3 "$ROOT/lib/plane_codex_config.py" strip-servers --file "$CONFIG" --server asana >"$stripped"
! grep -q asana "$stripped"
grep -q 'mcp_servers."plane"' "$stripped"

# A marker that is duplicated or unpaired is never treated as managed.
cat >"$TMP/bad.toml" <<EOF
# >>> megai-plane-managed (do not edit) >>>
[mcp_servers.plane]
command = "$HELPER"
args = ["--token-file", "$TMP/token", "--workspace", "brodev"]
EOF
if python3 "$ROOT/lib/plane_codex_config.py" inspect --file "$TMP/bad.toml" --helper "$HELPER" >/dev/null 2>&1; then
  exit 1
fi
cat >"$TMP/duplicate.toml" <<EOF
# >>> megai-plane-managed (do not edit) >>>
[mcp_servers.plane]
command = "$HELPER"
args = ["--token-file", "$TMP/token", "--workspace", "brodev"]
# <<< megai-plane-managed <<<
# >>> megai-plane-managed (do not edit) >>>
# <<< megai-plane-managed <<<
EOF
if python3 "$ROOT/lib/plane_codex_config.py" inspect --file "$TMP/duplicate.toml" --helper "$HELPER" >/dev/null 2>&1; then
  exit 1
fi
cat >"$TMP/dotted.toml" <<EOF
mcp_servers.asana.command = "legacy"
EOF
if python3 "$ROOT/lib/plane_codex_config.py" strip-servers --file "$TMP/dotted.toml" --server asana >/dev/null 2>&1; then
  exit 1
fi
echo 'Codex semantic config fixtures: ok'

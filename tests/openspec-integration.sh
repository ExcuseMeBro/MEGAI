#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
REAL_NODE="$(command -v node)"
REAL_JQ="$(command -v jq)"
export HOME="$TMP/home"
export MEGAI_HOME="$HOME/.megai"
export PI_CODING_AGENT_DIR="$HOME/.pi/agent"
export MOCK_BIN="$TMP/bin"
mkdir -p "$MOCK_BIN" "$MEGAI_HOME/skills" "$TMP/project/openspec"
cp -R "$ROOT/lib" "$MEGAI_HOME/"
cp -R "$ROOT/skills/megai-openspec" "$MEGAI_HOME/skills/"
ln -s "$REAL_NODE" "$MOCK_BIN/node"
ln -s "$REAL_JQ" "$MOCK_BIN/jq"
# Exclude the user's real npm/openspec; this test is offline and isolated.
export PATH="$MOCK_BIN:/usr/bin:/bin"
cat >"$MOCK_BIN/npm" <<'NPM'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$HOME/npm.calls"
cat >"$MOCK_BIN/openspec" <<'CLI'
#!/usr/bin/env bash
set -euo pipefail
[ "${OPENSPEC_TELEMETRY:-}" = 0 ] || exit 70
if [ "$*" = --version ]; then
  printf '%s\n' "${MOCK_VERSION:-1.12.0}"
elif [ "$*" = 'config set telemetry.enabled false' ]; then
  printf 'disabled\n' >"$HOME/telemetry"
else
  echo "unexpected command: $*" >&2
  exit 71
fi
CLI
chmod +x "$MOCK_BIN/openspec"
NPM
chmod +x "$MOCK_BIN/npm"
printf 'preserve\n' >"$TMP/project/openspec/spec.md"
cd "$TMP/project"

bash "$ROOT/lib/install_openspec.sh" >/dev/null
bash "$ROOT/lib/install_openspec.sh" >/dev/null
[ "$(wc -l <"$HOME/npm.calls" | tr -d ' ')" = 1 ]
grep -Fxq 'install --global --ignore-scripts --no-audit --no-fund @fission-ai/openspec@1.12.0' "$HOME/npm.calls"
[ "$(readlink "$PI_CODING_AGENT_DIR/skills/megai-openspec")" = "$MEGAI_HOME/skills/megai-openspec" ]
grep -Fxq disabled "$HOME/telemetry"
jq -e '.tools.openspec.version == "1.12.0" and .tools.openspec.scope == "pi" and .tools.openspec.optional == true' "$MEGAI_HOME/state.json" >/dev/null
[ ! -e .pi ]
[ ! -e openspec/config.yaml ]
grep -Fxq preserve openspec/spec.md

bash "$ROOT/lib/install_openspec.sh" --remove >/dev/null
[ ! -L "$PI_CODING_AGENT_DIR/skills/megai-openspec" ]
[ -x "$MOCK_BIN/openspec" ]
grep -Fxq disabled "$HOME/telemetry"
grep -Fxq preserve openspec/spec.md
jq -e '.tools | has("openspec") | not' "$MEGAI_HOME/state.json" >/dev/null

# Refuse mismatched CLIs rather than modifying a user's installation.
if MOCK_VERSION=9.0.0 bash "$ROOT/lib/install_openspec.sh" >"$TMP/version.log" 2>&1; then exit 1; fi
grep -q 'retained' "$TMP/version.log"
[ ! -L "$PI_CODING_AGENT_DIR/skills/megai-openspec" ]
[ "$(wc -l <"$HOME/npm.calls" | tr -d ' ')" = 1 ]

# Preserve both user-authored directories and foreign/dangling links.
mkdir -p "$PI_CODING_AGENT_DIR/skills/megai-openspec"
printf 'user\n' >"$PI_CODING_AGENT_DIR/skills/megai-openspec/SKILL.md"
if bash "$ROOT/lib/install_openspec.sh" >"$TMP/conflict.log" 2>&1; then exit 1; fi
bash "$ROOT/lib/install_openspec.sh" --remove >/dev/null
grep -Fxq user "$PI_CODING_AGENT_DIR/skills/megai-openspec/SKILL.md"
rm "$PI_CODING_AGENT_DIR/skills/megai-openspec/SKILL.md"
rmdir "$PI_CODING_AGENT_DIR/skills/megai-openspec"
ln -s "$TMP/user-owned-missing" "$PI_CODING_AGENT_DIR/skills/megai-openspec"
if bash "$ROOT/lib/install_openspec.sh" >"$TMP/link.log" 2>&1; then exit 1; fi
bash "$ROOT/lib/install_openspec.sh" --remove >/dev/null
[ "$(readlink "$PI_CODING_AGENT_DIR/skills/megai-openspec")" = "$TMP/user-owned-missing" ]

# Track every managed Pi location, even when uninstall runs without the install-time override.
rm "$PI_CODING_AGENT_DIR/skills/megai-openspec"  # test-owned foreign symlink
bash "$ROOT/lib/install_openspec.sh" >/dev/null
PI_CODING_AGENT_DIR="$TMP/custom pi" bash "$ROOT/lib/install_openspec.sh" >/dev/null
[ -L "$TMP/custom pi/skills/megai-openspec" ]
jq -e '.tools.openspec.destinations | length == 2' "$MEGAI_HOME/state.json" >/dev/null
env -u PI_CODING_AGENT_DIR bash "$ROOT/lib/install_openspec.sh" --remove >/dev/null
[ ! -L "$TMP/custom pi/skills/megai-openspec" ]
[ ! -L "$PI_CODING_AGENT_DIR/skills/megai-openspec" ]
jq -e '.tools | has("openspec") | not' "$MEGAI_HOME/state.json" >/dev/null

# A recorded link replaced by its owner is not ours to remove anymore.
PI_CODING_AGENT_DIR="$TMP/custom pi" bash "$ROOT/lib/install_openspec.sh" >/dev/null
rm "$TMP/custom pi/skills/megai-openspec"
ln -s "$TMP/replacement" "$TMP/custom pi/skills/megai-openspec"
env -u PI_CODING_AGENT_DIR bash "$ROOT/lib/install_openspec.sh" --remove >/dev/null
[ "$(readlink "$TMP/custom pi/skills/megai-openspec")" = "$TMP/replacement" ]

grep -Fq 'install_openspec.sh" --remove' "$ROOT/bin/megai"
! grep -Fq 'install_openspec.sh' "$ROOT/lib/main.sh"
echo 'OpenSpec installer: install/repeat/privacy/preservation/version/remove checks passed'

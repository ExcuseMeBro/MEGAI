#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home"
export MEGAI_HOME="$TMP/megai"
mkdir -p "$HOME" "$MEGAI_HOME/bin" "$MEGAI_HOME/lib" "$TMP/fake-bin"
cp "$ROOT/lib/ui.sh" "$ROOT/lib/state.sh" "$ROOT/lib/ix_safety.py" "$MEGAI_HOME/lib/"
printf '{"tools":{},"ports":{},"agents":{},"projects":{}}\n' > "$MEGAI_HOME/state.json"

cat > "$TMP/ix-install.sh" <<'SH'
#!/bin/sh
set -eu
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/ix" <<'IX'
#!/bin/sh
case "${1:-}" in
  --version) echo "1.2.3" ;;
  status) exit 0 ;;
esac
IX
chmod +x "$HOME/.local/bin/ix"
SH
cat > "$TMP/ix-codex-install.sh" <<'SH'
#!/bin/sh
if [ "${IX_CODEX_TEST_CONFLICT:-0}" = "1" ] && [ "$#" -eq 0 ]; then
  source_dir="${IX_HOME:-$HOME/.ix}/codex-plugin-source"
  mkdir -p "$source_dir/.codex/hooks" "$source_dir/scripts"
  cat > "$source_dir/.codex/hooks.json" <<'JSON'
{"hooks":{"SessionStart":[{"hooks":[{"type":"command","command":"ix-hook"}]}]}}
JSON
  cat > "$source_dir/.codex/hooks/session_start.py" <<'PY'
print("ix hook")
PY
  cat > "$source_dir/scripts/install_codex_integration.py" <<'PY'
def ensure_codex_hooks_enabled(path):
    text = path.read_text() if path.exists() else ""
    if "codex_hooks = true" not in text:
        path.write_text(text + "\n[features]\ncodex_hooks = true\n")
PY
  exit 1
fi
touch "$HOME/codex-hooks-installed"
SH
cat > "$TMP/fake-bin/claude" <<'SH'
#!/bin/sh
case "$*" in
  *"plugin list"*) [ -f "$HOME/claude-plugin-installed" ] && echo ix-memory ;;
  *"plugin install"*) touch "$HOME/claude-plugin-installed" ;;
esac
SH
cat > "$TMP/fake-bin/codex" <<'SH'
#!/bin/sh
case "$*" in
  *"plugin list"*)
    if [ -f "$HOME/codex-plugin-installed" ]; then
      echo '{"installed":[{"pluginId":"ix-memory@ix-codex-plugin","installed":true,"enabled":true}]}'
    else
      echo '{"installed":[]}'
    fi
    ;;
  *"plugin add"*) touch "$HOME/codex-plugin-installed" ;;
esac
SH
chmod +x "$TMP/fake-bin/"*
export PATH="$TMP/fake-bin:$PATH"
export IX_INSTALL_URL="file://$TMP/ix-install.sh"
export IX_CODEX_INSTALL_URL="file://$TMP/ix-codex-install.sh"

bash "$ROOT/lib/install_ix.sh" >/dev/null
bash "$ROOT/lib/install_ix.sh" >/dev/null

[ -x "$MEGAI_HOME/bin/ix" ]
[ "$("$MEGAI_HOME/bin/ix" --version)" = "1.2.3" ]
[ -f "$HOME/claude-plugin-installed" ]
[ -f "$HOME/codex-hooks-installed" ]
[ -f "$HOME/codex-plugin-installed" ]
jq -e '.tools.ix.version == "1.2.3" and .tools.ix.bin == env.MEGAI_HOME + "/bin/ix" and .tools.ix.claudePlugin and .tools.ix.codexPlugin and .tools.ix.codexHooks' "$MEGAI_HOME/state.json" >/dev/null

# If the upstream bootstrap fails but a working Ix CLI is already installed,
# MEGAI must still finish the Codex/Claude plugin and hook wiring.
cat > "$TMP/ix-install-fails.sh" <<'SH'
#!/bin/sh
exit 1
SH
rm -f "$HOME/claude-plugin-installed" "$HOME/codex-hooks-installed" "$HOME/codex-plugin-installed"
jq 'del(.tools.ix)' "$MEGAI_HOME/state.json" > "$MEGAI_HOME/state.tmp"
mv "$MEGAI_HOME/state.tmp" "$MEGAI_HOME/state.json"
export IX_INSTALL_URL="file://$TMP/ix-install-fails.sh"

bash "$ROOT/lib/install_ix.sh" >/dev/null

[ -f "$HOME/claude-plugin-installed" ]
[ -f "$HOME/codex-hooks-installed" ]
[ -f "$HOME/codex-plugin-installed" ]
jq -e '.tools.ix.version == "1.2.3" and .tools.ix.codexPlugin and .tools.ix.codexHooks' "$MEGAI_HOME/state.json" >/dev/null

# A pre-existing Codex hooks.json belongs to other integrations too. If the Ix
# installer refuses to overwrite it, MEGAI must merge Ix hooks and preserve the
# existing entries.
mkdir -p "$HOME/.codex"
cat > "$HOME/.codex/hooks.json" <<'JSON'
{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"existing-hook"}]}]}}
JSON
rm -f "$HOME/codex-hooks-installed"
export IX_CODEX_TEST_CONFLICT=1

bash "$ROOT/lib/install_ix.sh" >/dev/null

[ -f "$HOME/codex-hooks-installed" ]
[ -f "$HOME/.codex/hooks/session_start.py" ]
jq -e '
  .hooks.Stop[0].hooks[0].command == "existing-hook"
  and .hooks.SessionStart[0].hooks[0].command == "ix-hook"
' "$HOME/.codex/hooks.json" >/dev/null
grep -q '^codex_hooks = true$' "$HOME/.codex/config.toml"
jq -e '.tools.ix.codexHooks' "$MEGAI_HOME/state.json" >/dev/null

echo "ix integration: ok"

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home"
export MEGAI_HOME="$TMP/megai"
mkdir -p "$MEGAI_HOME/bin" "$MEGAI_HOME/lib" "$TMP/fake-bin"
cp "$ROOT/lib/ui.sh" "$ROOT/lib/state.sh" "$MEGAI_HOME/lib/"
printf '{"tools":{},"ports":{},"agents":{},"projects":{}}\n' > "$MEGAI_HOME/state.json"

cat > "$TMP/fake-bin/uv" <<'SH'
#!/bin/sh
case "$1 $2" in
  "tool install")
    mkdir -p "$HOME/.local/bin"
    cat > "$HOME/.local/bin/repowise" <<'RW'
#!/bin/sh
[ "${1:-}" = "--version" ] && echo "repowise 0.39.0"
RW
    chmod +x "$HOME/.local/bin/repowise"
    ;;
  "tool list") echo "repowise v0.39.0" ;;
  "tool upgrade") touch "$HOME/repowise-updated" ;;
esac
SH
chmod +x "$TMP/fake-bin/uv"
JQ_DIR="$(dirname "$(command -v jq)")"
export PATH="$TMP/fake-bin:$JQ_DIR:/usr/bin:/bin"

bash "$ROOT/lib/install_repowise.sh" >/dev/null
MEGAI_UPDATE=1 bash "$ROOT/lib/install_repowise.sh" >/dev/null

[ -x "$MEGAI_HOME/bin/repowise" ]
[ -f "$HOME/repowise-updated" ]
jq -e '.tools.repowise.version == "repowise 0.39.0" and .tools.repowise.bin == env.MEGAI_HOME + "/bin/repowise"' "$MEGAI_HOME/state.json" >/dev/null

echo "RepoWise integration: ok"

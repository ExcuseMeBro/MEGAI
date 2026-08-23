#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home"
export MEGAI_HOME="$TMP/megai"
mkdir -p "$MEGAI_HOME/lib" "$TMP/fake-bin"
cp "$ROOT/lib/ui.sh" "$ROOT/lib/state.sh" "$MEGAI_HOME/lib/"
printf '{"tools":{},"ports":{},"agents":{},"projects":{}}\n' > "$MEGAI_HOME/state.json"

cat > "$TMP/fake-bin/npm" <<'SH'
#!/bin/sh
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/argent" <<'ARGENT'
#!/bin/sh
[ "${1:-}" = "--version" ] && echo "0.22.0"
ARGENT
chmod +x "$HOME/.local/bin/argent"
[ "${MEGAI_UPDATE:-0}" = "1" ] && touch "$HOME/argent-updated"
exit 0
SH
chmod +x "$TMP/fake-bin/npm"
JQ_DIR="$(dirname "$(command -v jq)")"
export PATH="$TMP/fake-bin:$HOME/.local/bin:$JQ_DIR:/usr/bin:/bin"

bash "$ROOT/lib/install_argent.sh" >/dev/null
jq -e '.tools.argent.version == "0.22.0"' "$MEGAI_HOME/state.json" >/dev/null
MEGAI_UPDATE=1 bash "$ROOT/lib/install_argent.sh" >/dev/null

[ -x "$HOME/.local/bin/argent" ]
[ -f "$HOME/argent-updated" ]
jq -e '.tools.argent.version == "0.22.0" and .tools.argent.bin == env.HOME + "/.local/bin/argent"' "$MEGAI_HOME/state.json" >/dev/null

echo "Argent integration: ok"

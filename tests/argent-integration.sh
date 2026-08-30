#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home"
export MEGAI_HOME="$TMP/megai"
mkdir -p "$MEGAI_HOME/lib" "$MEGAI_HOME/skills/argent" "$MEGAI_HOME/task-flow/commands" "$TMP/fake-bin" "$HOME/.omp/profiles/work/agent"
cp "$ROOT/lib/ui.sh" "$ROOT/lib/state.sh" "$MEGAI_HOME/lib/"
cp "$ROOT/skills/argent/SKILL.md" "$MEGAI_HOME/skills/argent/SKILL.md"
cp "$ROOT/task-flow/commands/argent.md" "$MEGAI_HOME/task-flow/commands/argent.md"
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
for artifact in \
  "$HOME/.agents/skills/argent/SKILL.md" \
  "$HOME/.claude/skills/argent/SKILL.md" \
  "$HOME/.pi/agent/skills/argent/SKILL.md" \
  "$HOME/.omp/agent/skills/argent/SKILL.md" \
  "$HOME/.omp/profiles/work/agent/skills/argent/SKILL.md" \
  "$HOME/.claude/commands/argent.md"; do
  [ -f "$artifact" ]
  grep -q '^managed-by: megai$' "$artifact"
  grep -q '/argent' "$artifact"
done
printf '%s\n' 'user-owned argent skill' >"$HOME/.agents/skills/argent/SKILL.md"
MEGAI_UPDATE=1 bash "$ROOT/lib/install_argent.sh" >/dev/null
grep -q '^user-owned argent skill$' "$HOME/.agents/skills/argent/SKILL.md"

[ -x "$HOME/.local/bin/argent" ]
[ -f "$HOME/argent-updated" ]
jq -e '.tools.argent.version == "0.22.0" and .tools.argent.bin == env.HOME + "/.local/bin/argent"' "$MEGAI_HOME/state.json" >/dev/null

bash "$ROOT/lib/install_argent.sh" --remove >/dev/null
grep -q '^user-owned argent skill$' "$HOME/.agents/skills/argent/SKILL.md"
[ ! -e "$HOME/.claude/skills/argent/SKILL.md" ]
[ ! -e "$HOME/.pi/agent/skills/argent/SKILL.md" ]
[ ! -e "$HOME/.omp/agent/skills/argent/SKILL.md" ]
[ ! -e "$HOME/.omp/profiles/work/agent/skills/argent/SKILL.md" ]
[ ! -e "$HOME/.claude/commands/argent.md" ]

echo "Argent integration: ok"

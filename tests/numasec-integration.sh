#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home"
export MEGAI_HOME="$TMP/megai"
export NUMASEC_SKILL_SOURCE="$TMP/skill"
mkdir -p "$MEGAI_HOME/lib" "$NUMASEC_SKILL_SOURCE" "$TMP/fake-bin"
cp "$ROOT/lib/ui.sh" "$ROOT/lib/state.sh" "$MEGAI_HOME/lib/"
printf '{"tools":{},"ports":{},"agents":{},"projects":{}}\n' >"$MEGAI_HOME/state.json"
cp "$ROOT/skills/numasec-security/SKILL.md" "$NUMASEC_SKILL_SOURCE/SKILL.md"

cat >"$TMP/fake-bin/npm" <<'SH'
#!/bin/sh
mkdir -p "$HOME/.local/bin"
cat >"$HOME/.local/bin/numasec" <<'NUMASEC'
#!/bin/sh
[ "${1:-}" = "--version" ] && echo "numasec 1.2.1"
NUMASEC
chmod +x "$HOME/.local/bin/numasec"
[ "${MEGAI_UPDATE:-0}" = "1" ] && touch "$HOME/numasec-updated"
exit 0
SH
chmod +x "$TMP/fake-bin/npm"
JQ_DIR="$(dirname "$(command -v jq)")"
export PATH="$TMP/fake-bin:$HOME/.local/bin:$JQ_DIR:/usr/bin:/bin"

mkdir -p "$HOME/.agents/skills/numasec-security"
printf 'keep\n' >"$HOME/.agents/skills/numasec-security/SKILL.md"

bash "$ROOT/lib/install_numasec.sh" >/dev/null
bash "$ROOT/lib/install_numasec.sh" >/dev/null
MEGAI_UPDATE=1 bash "$ROOT/lib/install_numasec.sh" >/dev/null

[ -f "$HOME/.agents/skills/numasec-security/SKILL.md" ]
[ "$(cat "$HOME/.agents/skills/numasec-security/SKILL.md")" = keep ]
for root in "$HOME/.claude/skills" "$HOME/.codex/skills" "$HOME/.pi/agent/skills"; do
  [ -L "$root/numasec-security" ]
done
[ -f "$HOME/numasec-updated" ]
jq -e '.tools.numasec == {bin: (env.HOME + "/.local/bin/numasec"), version:"numasec 1.2.1", skill:env.NUMASEC_SKILL_SOURCE}' "$MEGAI_HOME/state.json" >/dev/null

bash "$ROOT/lib/install_numasec.sh" --remove >/dev/null
[ ! -e "$HOME/.claude/skills/numasec-security" ]
[ ! -e "$HOME/.codex/skills/numasec-security" ]
[ ! -e "$HOME/.pi/agent/skills/numasec-security" ]
[ -f "$HOME/.agents/skills/numasec-security/SKILL.md" ]

printf 'numasec integration: ok\n'

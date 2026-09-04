#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

export HOME="$TMP/home"
export MEGAI_HOME="$TMP/megai"
mkdir -p "$HOME" "$MEGAI_HOME/bin" "$MEGAI_HOME/lib" "$MEGAI_HOME/venv/cocoindex/bin" "$TMP/bin"
cp "$ROOT/lib/install_zvec_grep.sh" "$ROOT/lib/state.sh" "$ROOT/lib/ui.sh" "$MEGAI_HOME/lib/"
printf '%s\n' '{"tools":{"cocoindex":{"bin":"/old/cocoindex"}},"agents":{},"projects":{}}' >"$MEGAI_HOME/state.json"
printf '#!/usr/bin/env bash\nexit 0\n' >"$MEGAI_HOME/lib/install_cocoindex.sh"
printf '#!/usr/bin/env bash\nexit 0\n' >"$MEGAI_HOME/venv/cocoindex/bin/cocoindex"
ln -s "$MEGAI_HOME/venv/cocoindex/bin/cocoindex" "$MEGAI_HOME/bin/cocoindex"

cat >"$TMP/bin/npm" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
[ "$*" = "install -g @zvec/zvec-grep@latest" ]
cat >"$(dirname "$0")/zg" <<'ZG'
#!/usr/bin/env bash
if [ "${1:-}" = version ]; then
  echo "zvec-grep 0.2.1"
  exit 0
fi
exit 0
ZG
chmod +x "$(dirname "$0")/zg"
SH
chmod +x "$TMP/bin/npm"
export PATH="$TMP/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

bash "$MEGAI_HOME/lib/install_zvec_grep.sh" >/dev/null
bash "$MEGAI_HOME/lib/install_zvec_grep.sh" >/dev/null
[ -x "$MEGAI_HOME/bin/zg" ]
[ "$("$MEGAI_HOME/bin/zg" version)" = "zvec-grep 0.2.1" ]
jq -e '
  .tools["zvec-grep"].bin == $bin
  and .tools["zvec-grep"].version == "zvec-grep 0.2.1"
  and (.tools.cocoindex | not)
' --arg bin "$MEGAI_HOME/bin/zg" "$MEGAI_HOME/state.json" >/dev/null
[ ! -e "$MEGAI_HOME/lib/install_cocoindex.sh" ]
[ ! -e "$MEGAI_HOME/bin/cocoindex" ]
[ ! -e "$MEGAI_HOME/venv/cocoindex" ]

! rg -q 'install_cocoindex|cocoindex CLI|Tools:.*cocoindex' \
  "$ROOT/bin/megai" "$ROOT/lib/main.sh" "$ROOT/README.md"
rg -q 'install_zvec_grep' "$ROOT/bin/megai" "$ROOT/lib/main.sh"
rg -q 'Node.js `22\+`' "$ROOT/README.md"

# Project activation creates one local hybrid index, keeps it out of git, and
# explicit reindex refreshes the existing zvec-grep index.
RUNTIME_HOME="$TMP/runtime-home"
RUNTIME_MEGAI="$TMP/runtime-megai"
RUNTIME_BIN="$TMP/runtime-bin"
PROJECT="$TMP/project"
mkdir -p "$RUNTIME_HOME" "$RUNTIME_MEGAI" "$RUNTIME_BIN" "$PROJECT"
cp -R "$ROOT/bin" "$ROOT/lib" "$RUNTIME_MEGAI/"
printf '#!/usr/bin/env bash\nexit 0\n' >"$RUNTIME_MEGAI/lib/ensure_dev.sh"
printf '%s\n' '{"tools":{},"ports":{},"agents":{},"projects":{}}' >"$RUNTIME_MEGAI/state.json"
git init -q "$PROJECT"
PROJECT_ROOT="$(git -C "$PROJECT" rev-parse --show-toplevel)"

cat >"$RUNTIME_BIN/agentmemory" <<'SH'
#!/usr/bin/env bash
exit 0
SH
cat >"$RUNTIME_BIN/codedb" <<'SH'
#!/usr/bin/env bash
exit 0
SH
cat >"$RUNTIME_BIN/zg" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  index)
    printf '%s\n' "$*" >>"$ZG_CALLS"
    mkdir -p "$2/.zvec-grep"
    printf '%s\n' '{}' >"$2/.zvec-grep/manifest.json"
    ;;
  version) echo "0.2.1" ;;
  *) exit 0 ;;
esac
SH
chmod +x "$RUNTIME_BIN/agentmemory" "$RUNTIME_BIN/codedb" "$RUNTIME_BIN/zg" "$RUNTIME_MEGAI/bin/megai"
export HOME="$RUNTIME_HOME"
export MEGAI_HOME="$RUNTIME_MEGAI"
export ZG_CALLS="$TMP/zg-calls"
export PATH="$RUNTIME_BIN:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
(
  cd "$PROJECT"
  "$RUNTIME_MEGAI/bin/megai" >/dev/null
  "$RUNTIME_MEGAI/bin/megai" >/dev/null
)
[ "$(wc -l <"$ZG_CALLS" | tr -d ' ')" = "1" ]
grep -Fxq "index $PROJECT_ROOT --embedding local/potion-code-16m-v2" "$ZG_CALLS"
grep -Fxq '/.zvec-grep/' "$PROJECT/.git/info/exclude"
(
  cd "$PROJECT"
  "$RUNTIME_MEGAI/bin/megai" reindex >/dev/null
)
[ "$(wc -l <"$ZG_CALLS" | tr -d ' ')" = "2" ]
tail -n1 "$ZG_CALLS" | grep -Fxq "index $PROJECT_ROOT --rebuild"

echo "zvec-grep integration: ok"

#!/usr/bin/env bash
# Append `export PATH=".../.megai/bin:$PATH"` to user's shell rc files.
# Idempotent via marker block. Removable via --remove.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"

MODE="${1:-install}"
MARK_BEG="# >>> megai-managed (do not edit) >>>"
MARK_END="# <<< megai-managed <<<"
LINE='export PATH="'"$MEGAI_HOME"'/bin:$PATH"'

targets=()
[ -f "$HOME/.bashrc"  ] && targets+=("$HOME/.bashrc")
[ -f "$HOME/.zshrc"   ] && targets+=("$HOME/.zshrc")
[ -f "$HOME/.profile" ] && targets+=("$HOME/.profile")

# If user shell is zsh and no .zshrc, create it. Same for bash + .bashrc.
if [ "${#targets[@]}" -eq 0 ]; then
  case "${SHELL:-}" in
    */zsh)  : > "$HOME/.zshrc";  targets+=("$HOME/.zshrc") ;;
    */bash) : > "$HOME/.bashrc"; targets+=("$HOME/.bashrc") ;;
    *)      : > "$HOME/.profile"; targets+=("$HOME/.profile") ;;
  esac
fi

strip_block() {
  awk -v b="$MARK_BEG" -v e="$MARK_END" '
    $0==b { skip=1; next }
    $0==e { skip=0; next }
    !skip { print }
  ' "$1"
}

for rc in "${targets[@]}"; do
  cp "$rc" "$MEGAI_HOME/backups/$(basename "$rc").bak.$(date +%s)" 2>/dev/null || true

  stripped="$(strip_block "$rc")"

  if [ "$MODE" = "--remove" ]; then
    printf "%s\n" "$stripped" > "$rc"
    ok "PATH: removed megai block from $rc"
    continue
  fi

  {
    printf "%s\n" "$stripped"
    printf "\n%s\n" "$MARK_BEG"
    printf "%s\n" "$LINE"
    printf "%s\n" "$MARK_END"
  } > "$rc"
  ok "PATH: wired $rc"
done

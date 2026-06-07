#!/usr/bin/env bash
# Append a task line to <project>/.todos/todo.md, creating the board if missing.
# Usage: taskflow-add.sh <task text...>   (priority markers !! !!! !!!! supported)
set -euo pipefail

TEXT="${*:-}"
TEXT="$(printf '%s' "$TEXT" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
[ -n "$TEXT" ] && [ "$TEXT" != "\$ARGUMENTS" ] || { echo "usage: /ta <task text>"; exit 0; }

# Find the project root by walking up for a marker; default to CWD.
markers=(.todos .git package.json pyproject.toml go.mod Cargo.toml pom.xml build.gradle Gemfile composer.json requirements.txt CLAUDE.md .megai)
root=""; dir="$PWD"
for _ in $(seq 1 30); do
  for m in "${markers[@]}"; do [ -e "$dir/$m" ] && { root="$dir"; break; }; done
  [ -n "$root" ] && break
  parent="$(dirname "$dir")"; [ "$parent" = "$dir" ] && break; dir="$parent"
done
[ -n "$root" ] || root="$PWD"

base="$root/.todos"
mkdir -p "$base"
[ -f "$base/todo.md" ]       || printf '# TODO\n\n'         > "$base/todo.md"
[ -f "$base/inprogress.md" ] || printf '# IN PROGRESS\n\n' > "$base/inprogress.md"
[ -f "$base/done.md" ]       || printf '# DONE\n\n'        > "$base/done.md"

# Pick highest priority marker present, strip it from the text.
prio=""
case "$TEXT" in
  *'!!!!'*) prio="!!!! "; TEXT="${TEXT//!!!!/}";;
  *'!!!'*)  prio="!!! ";  TEXT="${TEXT//!!!/}";;
  *'!!'*)   prio="!! ";   TEXT="${TEXT//!!/}";;
esac
TEXT="$(printf '%s' "$TEXT" | sed 's/  */ /g; s/^[[:space:]]*//; s/[[:space:]]*$//')"
[ -n "$TEXT" ] || { echo "usage: /ta <task text>"; exit 0; }

printf -- '- [ ] %s%s\n' "$prio" "$TEXT" >> "$base/todo.md"
echo "added -> $base/todo.md"
echo "  - [ ] ${prio}${TEXT}"

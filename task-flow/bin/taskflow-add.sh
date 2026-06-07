#!/usr/bin/env bash
# Append a task line to <project>/.todos/todo.md, creating the board if missing.
# Usage: taskflow-add.sh <task text...>   (priority markers !! !!! !!!! supported)
# Writes pretty emoji lines:  - [ ] 🟠 fix the login bug
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
[ -f "$base/todo.md" ]       || printf '# 📋 TODO\n\n'         > "$base/todo.md"
[ -f "$base/inprogress.md" ] || printf '# 🚧 IN PROGRESS\n\n' > "$base/inprogress.md"
[ -f "$base/done.md" ]       || printf '# ✅ DONE\n\n'        > "$base/done.md"

# Pick highest priority marker -> emoji, strip it from the text.
emoji="🟡"  # default: medium
case " $TEXT " in
  *'!!!!'*) emoji="🔴"; TEXT="${TEXT//!!!!/}";;
  *'!!!'*)  emoji="🟠"; TEXT="${TEXT//!!!/}";;
  *'!!'*)   emoji="🟡"; TEXT="${TEXT//!!/}";;
  *' ! '*|*' !') emoji="🟢"; TEXT="${TEXT/ !/}";;
esac
TEXT="$(printf '%s' "$TEXT" | sed 's/  */ /g; s/^[[:space:]]*//; s/[[:space:]]*$//')"
[ -n "$TEXT" ] || { echo "usage: /ta <task text>"; exit 0; }

printf -- '- [ ] %s %s\n' "$emoji" "$TEXT" >> "$base/todo.md"

# Refresh the monitoring dashboard.
if command -v node >/dev/null 2>&1 && [ -f "$HOME/.claude/hooks/taskflow-monitor.js" ]; then
  node "$HOME/.claude/hooks/taskflow-monitor.js" "$base" 2>/dev/null || true
fi

echo "✅ added -> $base/todo.md"
echo "   - [ ] ${emoji} ${TEXT}"

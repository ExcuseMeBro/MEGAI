#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home"
export MEGAI_HOME="$TMP/megai"
export REPOWISE_TEST_COUNT="$TMP/repowise-runs"
mkdir -p "$HOME" "$MEGAI_HOME/lib" "$MEGAI_HOME/logs" "$TMP/bin" "$TMP/repo"
cp -R "$ROOT/lib/." "$MEGAI_HOME/lib/"

cat > "$TMP/bin/lsof" <<'SH'
#!/bin/sh
exit 0
SH
cat > "$TMP/bin/codedb" <<'SH'
#!/bin/sh
exit 0
SH
cat > "$TMP/bin/graphify" <<'SH'
#!/bin/sh
exit 0
SH
cat > "$TMP/bin/repowise" <<'SH'
#!/bin/sh
if [ "${1:-}" = "init" ]; then
  echo run >> "$REPOWISE_TEST_COUNT"
  mkdir -p .repowise
  exit 1
fi
SH
chmod +x "$TMP/bin/"*
JQ_DIR="$(dirname "$(command -v jq)")"
export PATH="$TMP/bin:$JQ_DIR:/usr/bin:/bin"
git -C "$TMP/repo" init -q

wait_for_failed_run() {
  local pidf pid i=0
  pidf="$(find "$MEGAI_HOME/logs" -name 'repowise-*.pid' -print -quit)"
  while [ -z "$pidf" ] && [ "$i" -lt 50 ]; do
    sleep 0.02
    pidf="$(find "$MEGAI_HOME/logs" -name 'repowise-*.pid' -print -quit)"
    i=$((i + 1))
  done
  pid="$(cat "$pidf")"
  while kill -0 "$pid" 2>/dev/null && [ "$i" -lt 100 ]; do sleep 0.02; i=$((i + 1)); done
}

(cd "$TMP/repo" && bash "$ROOT/bin/megai" >/dev/null 2>&1)
wait_for_failed_run
(cd "$TMP/repo" && bash "$ROOT/bin/megai" >/dev/null 2>&1)
wait_for_failed_run

[ "$(wc -l < "$REPOWISE_TEST_COUNT" | tr -d ' ')" = "2" ]
log="$(find "$MEGAI_HOME/logs" -name 'repowise-*.log' -print -quit)"
[ "$(grep -c '^--- RepoWise init ' "$log")" = "2" ]

echo "RepoWise background retry: ok"

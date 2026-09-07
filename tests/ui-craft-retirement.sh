#!/usr/bin/env bash
# Real dispatch, sandboxed installers; shared retirement proof for removed CLI dependencies.
set -euo pipefail
ROOT="${MEGAI_TEST_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
assert_absent() {
  if grep -Ei 'ui[-_]craft|repowise|dembrandt|graphify' "$@"; then
    echo 'FAIL: retired tool was invoked or advertised' >&2
    exit 1
  fi
}
export HOME="$TMP/home" MEGAI_HOME="$TMP/megai" CALLS="$TMP/calls"
mkdir -p "$HOME" "$MEGAI_HOME/lib" "$TMP/bin"
for tool in ui-craft repowise dembrandt graphify; do
  mkdir -p "$TMP/project/.$tool"
  printf 'user design/index notes\n' > "$TMP/project/.$tool/keep"
  cat > "$TMP/bin/$tool" <<'SH'
#!/bin/sh
printf 'FORBIDDEN %s %s\n' "$0" "$*" >> "$CALLS"
exit 1
SH
done
mkdir -p "$TMP/project/graphify-out"
printf 'user graph\n' > "$TMP/project/graphify-out/graph.json"
cp "$ROOT/lib/"*.sh "$MEGAI_HOME/lib/"
cat > "$MEGAI_HOME/lib/detect.sh" <<'SH'
detect_os() { MEGAI_OS=darwin; MEGAI_ARCH=arm64; }
detect_runtimes() { MEGAI_HAS_CURL=1; MEGAI_HAS_NODE=1; MEGAI_HAS_PY=1; MEGAI_HAS_BREW=1; MEGAI_HAS_JQ=1; }
require_or_install_jq() { :; }
require_or_install_node() { :; }
require_or_install_python() { :; }
require_or_install_pipx() { :; }
SH
# Stale installers must never be called even if left by an older installation.
for f in "$MEGAI_HOME/lib/"install_*.sh "$MEGAI_HOME/lib/"wire_*.sh "$MEGAI_HOME/lib/plane_mcp.sh" "$MEGAI_HOME/lib/install_ui_craft.sh" "$MEGAI_HOME/lib/install_repowise.sh" "$MEGAI_HOME/lib/install_dembrandt.sh" "$MEGAI_HOME/lib/install_graphify.sh"; do
  printf '#!/bin/sh\nprintf "%%s\\n" "%s" >> "$CALLS"\n' "$(basename "$f")" > "$f"
done
printf '#!/bin/sh\nexit 0\n' > "$TMP/bin/agentmemory"
cp "$TMP/bin/dembrandt" "$TMP/bin/dembrandt-mcp"
chmod +x "$TMP/bin/"*
export PATH="$TMP/bin:$PATH"
printf '{"tools":{"ui-craft":{"version":"old"},"repowise":{"version":"old"},"dembrandt":{"version":"old"},"graphify":{"version":"old"}},"ports":{},"agents":{},"projects":{}}\n' > "$MEGAI_HOME/state.json"
: > "$CALLS"
cd "$TMP/project"
bash "$ROOT/lib/main.sh" > "$TMP/install.out"
assert_absent "$CALLS"
bash "$ROOT/bin/megai" update > "$TMP/update.out"
assert_absent "$CALLS"
bash "$ROOT/bin/megai" status > "$TMP/status.out"
assert_absent "$TMP/status.out"
bash "$ROOT/bin/megai" doctor > "$TMP/doctor.out" 2>&1
assert_absent "$TMP/doctor.out" "$CALLS"
if bash "$ROOT/bin/megai" graph > "$TMP/graph.out" 2>&1; then exit 1; fi
assert_absent "$CALLS"
printf 'y\n' | bash "$ROOT/bin/megai" uninstall > "$TMP/uninstall.out" 2>&1
assert_absent "$CALLS"
[ -x "$TMP/bin/dembrandt-mcp" ]
[ "$(< "$TMP/project/graphify-out/graph.json")" = 'user graph' ]
for tool in ui-craft repowise dembrandt graphify; do
  [ -x "$TMP/bin/$tool" ] # generic removal must not uninstall independent tools
  [ "$(< "$TMP/project/.$tool/keep")" = 'user design/index notes' ]
done
[ ! -f "$ROOT/lib/install_ui_craft.sh" ]
[ ! -f "$ROOT/lib/install_repowise.sh" ]
[ ! -f "$ROOT/lib/install_dembrandt.sh" ]
[ ! -f "$ROOT/lib/install_graphify.sh" ]
assert_absent "$ROOT/bin/megai" "$ROOT/lib/main.sh"
python3 - "$ROOT/lib/main.sh" <<'PY'
import re, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
total = int(re.search(r'^TOTAL=(\d+)$', text, re.M)[1])
steps = [int(n) for n in re.findall(r'^step (\d+) \$TOTAL ', text, re.M)]
assert steps == list(range(1, total + 1)), (total, steps)
PY
printf 'Retired tools PASS: dispatch skips retired tools; independent CLIs and project data retained\n'

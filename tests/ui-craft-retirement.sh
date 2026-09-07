#!/usr/bin/env bash
# Exercise real MEGAI dispatch with sandboxed installers; no host tools/services.
set -euo pipefail
ROOT="${MEGAI_TEST_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home" MEGAI_HOME="$TMP/megai" CALLS="$TMP/calls"
mkdir -p "$HOME" "$MEGAI_HOME/lib" "$TMP/bin" "$TMP/project/.ui-craft"
printf 'user design notes\n' > "$TMP/project/.ui-craft/brief.md"
cp "$ROOT/lib/"*.sh "$MEGAI_HOME/lib/"
cat > "$MEGAI_HOME/lib/detect.sh" <<'SH'
detect_os() { MEGAI_OS=darwin; MEGAI_ARCH=arm64; }
detect_runtimes() { MEGAI_HAS_CURL=1; MEGAI_HAS_NODE=1; MEGAI_HAS_PY=1; MEGAI_HAS_BREW=1; MEGAI_HAS_JQ=1; }
require_or_install_jq() { :; }
require_or_install_node() { :; }
require_or_install_python() { :; }
require_or_install_pipx() { :; }
SH
# Preserve a stale installer to prove current dispatch never invokes it.
for f in "$MEGAI_HOME/lib/"install_*.sh "$MEGAI_HOME/lib/"wire_*.sh "$MEGAI_HOME/lib/plane_mcp.sh" "$MEGAI_HOME/lib/install_ui_craft.sh"; do
  printf '#!/bin/sh\nprintf "%%s\\n" "%s" >> "$CALLS"\n' "$(basename "$f")" > "$f"
done
cat > "$TMP/bin/ui-craft" <<'SH'
#!/bin/sh
printf 'FORBIDDEN ui-craft %s\n' "$*" >> "$CALLS"
exit 1
SH
printf '#!/bin/sh\nexit 0\n' > "$TMP/bin/agentmemory"
chmod +x "$TMP/bin/"*
export PATH="$TMP/bin:$PATH"
printf '{"tools":{"ui-craft":{"bin":"%s","version":"old"}},"ports":{},"agents":{},"projects":{}}\n' "$TMP/bin/ui-craft" > "$MEGAI_HOME/state.json"
: > "$CALLS"
cd "$TMP/project"
bash "$ROOT/lib/main.sh" > "$TMP/install.out"
! grep -q 'ui-craft' "$CALLS"
bash "$ROOT/bin/megai" update > "$TMP/update.out"
! grep -q 'ui-craft' "$CALLS"
bash "$ROOT/bin/megai" status > "$TMP/status.out"
! grep -q 'ui-craft' "$TMP/status.out"
bash "$ROOT/bin/megai" doctor > "$TMP/doctor.out" 2>&1
! grep -q 'ui-craft' "$TMP/doctor.out"
! grep -q 'ui-craft' "$CALLS"
printf 'y\n' | bash "$ROOT/bin/megai" uninstall > "$TMP/uninstall.out" 2>&1
! grep -q 'ui-craft' "$CALLS"
[ -x "$TMP/bin/ui-craft" ] # generic MEGAI removal must not uninstall independent tools
[ "$(< "$TMP/project/.ui-craft/brief.md")" = 'user design notes' ]
[ ! -f "$ROOT/lib/install_ui_craft.sh" ]
! grep -q 'ui-craft' "$ROOT/bin/megai" "$ROOT/lib/main.sh"
python3 - "$ROOT/lib/main.sh" <<'PY'
import re, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
total = int(re.search(r'^TOTAL=(\d+)$', text, re.M)[1])
steps = [int(n) for n in re.findall(r'^step (\d+) \$TOTAL ', text, re.M)]
assert steps == list(range(1, total + 1)), (total, steps)
PY
printf 'ui-craft retirement PASS: install/update/status/doctor/uninstall skip retired tool; design data retained\n'

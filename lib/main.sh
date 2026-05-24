#!/usr/bin/env bash
# main pipeline — invoked by install.sh after files are in place
set -euo pipefail

MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
LIB="$MEGAI_HOME/lib"

# shellcheck source=ui.sh
. "$LIB/ui.sh"
# shellcheck source=detect.sh
. "$LIB/detect.sh"
# shellcheck source=state.sh
. "$LIB/state.sh"

TOTAL=8

step 1 $TOTAL "Detecting OS / runtimes"
detect_os
detect_runtimes
[ "$MEGAI_OS" = "unsupported" ] && die "Unsupported OS"
[ "$MEGAI_HAS_CURL" = "1" ] || die "curl required"
ok "$MEGAI_OS/$MEGAI_ARCH (node=$MEGAI_HAS_NODE py=$MEGAI_HAS_PY brew=$MEGAI_HAS_BREW jq=$MEGAI_HAS_JQ)"

require_or_install_jq
require_or_install_node
require_or_install_python
require_or_install_pipx

state_init
ok "state initialized -> $MEGAI_HOME/state.json"

step 2 $TOTAL "Installing Fusion"
bash "$LIB/install_fusion.sh"

step 3 $TOTAL "Installing agent-memory"
bash "$LIB/install_agent_memory.sh"

step 4 $TOTAL "Installing codedb"
bash "$LIB/install_codedb.sh"

step 5 $TOTAL "Installing cocoindex"
bash "$LIB/install_cocoindex.sh"

step 6 $TOTAL "Installing caveman (token-compression skill)"
bash "$LIB/install_caveman.sh"

step 7 $TOTAL "Installing rtk (Rust Token Killer)"
bash "$LIB/install_rtk.sh"

step 8 $TOTAL "Wiring MCP into cc / codex / pi"
bash "$LIB/wire_cc.sh"    || warn "cc wiring skipped"
bash "$LIB/wire_codex.sh" || warn "codex wiring skipped"
bash "$LIB/wire_pi.sh"    || warn "pi wiring skipped"

# PATH hint
case ":$PATH:" in
  *":$MEGAI_HOME/bin:"*) ;;
  *)
    warn "PATH ga qo'shing:  export PATH=\"$MEGAI_HOME/bin:\$PATH\""
    ;;
esac

ok "MEGAI ready"
echo
echo "    megai status"
echo "    megai doctor"
echo "    megai update"
echo

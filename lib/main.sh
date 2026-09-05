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
# shellcheck source=banner.sh
. "$LIB/banner.sh"
megai_banner

TOTAL=17

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

step 2 $TOTAL "Installing agent-memory"
bash "$LIB/install_agent_memory.sh"

step 3 $TOTAL "Installing codedb"
bash "$LIB/install_codedb.sh"

step 4 $TOTAL "Installing zvec-grep hybrid workspace search"
bash "$LIB/install_zvec_grep.sh"

step 5 $TOTAL "Optional caveman (MEGAI_CAVEMAN=1 to install)"
bash "$LIB/install_caveman.sh"

step 6 $TOTAL "Installing rtk (Rust Token Killer)"
bash "$LIB/install_rtk.sh"

step 7 $TOTAL "Installing graphify (knowledge-graph skill)"
bash "$LIB/install_graphify.sh"

step 8 $TOTAL "Installing task-flow + safe agent worktree lifecycle"
bash "$LIB/install_taskflow.sh" || warn "task-flow install skipped"
bash "$LIB/install_worktree_lifecycle.sh" || warn "worktree lifecycle install skipped"

step 9 $TOTAL "Installing ui-craft (design-system skill + MCP gates)"
bash "$LIB/install_ui_craft.sh" || warn "ui-craft install skipped"

step 10 $TOTAL "Installing ux-ui-agent-skills (global, 3 agents)"
bash "$LIB/install_ux_ui_agent_skills.sh" || warn "ux-ui-agent-skills install skipped"

step 11 $TOTAL "Installing Dembrandt (design-system extraction CLI + MCP)"
bash "$LIB/install_dembrandt.sh" || warn "Dembrandt install skipped"

step 12 $TOTAL "Installing RepoWise (codebase intelligence + MCP)"
bash "$LIB/install_repowise.sh" || warn "RepoWise install skipped"

step 13 $TOTAL "Installing Argent (agent-driven app testing CLI + MCP)"
bash "$LIB/install_argent.sh" || warn "Argent install skipped"

step 14 $TOTAL "Installing Numasec (authorized security CLI + global skill)"
bash "$LIB/install_numasec.sh" || warn "Numasec install skipped"

step 15 $TOTAL "Installing Matt Pocock's engineering skills (global, 3 agents)"
bash "$LIB/install_mattpocock_skills.sh" || warn "Matt Pocock skills install skipped"

step 16 $TOTAL "Installing recommended Pi packages (global)"
bash "$LIB/install_pi_packages.sh" || warn "Pi package install skipped"

step 17 $TOTAL "Wiring MCP into cc / codex / pi / OMP + shell PATH"
bash "$LIB/wire_cc.sh"    || warn "cc wiring skipped"
bash "$LIB/wire_codex.sh" || warn "codex wiring skipped"
bash "$LIB/wire_pi.sh"    || warn "pi wiring skipped"
bash "$LIB/wire_omp.sh"   || warn "OMP wiring skipped"
bash "$LIB/wire_path.sh"  || warn "PATH wiring skipped"

ok "MEGAI ready"
echo
echo "    Open a new shell (or 'source ~/.zshrc') so PATH picks up megai/bin"
echo
echo "    megai           # activate stack for the current folder"
echo "    megai cc        # Claude Code (full stack)"
echo "    megai omp       # Oh My Pi (full stack)"
echo "    megai status"
echo "    megai doctor"
echo

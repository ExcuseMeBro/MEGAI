#!/usr/bin/env bash
# Slim MEGAI installer pipeline: the nine requested product entries, including core codedb.
set -euo pipefail

MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
LIB="$MEGAI_HOME/lib"
export PATH="$PATH:$MEGAI_HOME/bin:$HOME/.local/bin"

. "$LIB/ui.sh"
. "$LIB/detect.sh"
. "$LIB/state.sh"
. "$LIB/banner.sh"
megai_banner

step 1 7 "Detecting core runtimes"
detect_os
detect_runtimes
[ "$MEGAI_OS" = "unsupported" ] && die "Unsupported OS"
[ "$MEGAI_HAS_CURL" = "1" ] || die "curl required"
[ "$MEGAI_HAS_PY" = "1" ] || die "Python 3.11+ required for safe policy/config validation"
python3 -c 'import tomllib' || die "Python 3.11+ required"
# Validate migration before any third-party installer or config mutation.
python3 "$LIB/slim_wiring.py" all --check
command -v git >/dev/null 2>&1 || die "Git required"
command -v rg >/dev/null 2>&1 || die "ripgrep required; install rg before retrying"
require_or_install_jq
require_or_install_node
if ! command -v ruff >/dev/null 2>&1 && ! command -v uv >/dev/null 2>&1; then require_or_install_pipx; fi
ok "$MEGAI_OS/$MEGAI_ARCH (node=$MEGAI_HAS_NODE py=$MEGAI_HAS_PY jq=$MEGAI_HAS_JQ)"

state_init
ok "state initialized -> $MEGAI_HOME/state.json"

step 2 7 "Installing agent-memory (daemon starts only on request)"
bash "$LIB/install_agent_memory.sh" || die "agent-memory install failed"

step 3 7 "Installing core search (indexing starts only on request)"
bash "$LIB/install_zvec_grep.sh" || die "zvec-grep install failed"
bash "$LIB/install_codedb.sh" || die "codedb install failed"

step 4 7 "Installing rtk, Ruff, and requested skill kits"
bash "$LIB/install_rtk.sh" || die "rtk install failed"
bash "$LIB/install_ruff.sh" || die "Ruff install failed"
bash "$LIB/install_ux_ui_agent_skills.sh" || die "ux-ui-agent-skills install failed"
bash "$LIB/install_mattpocock_skills.sh" || die "Matt Pocock skills install failed"

step 5 7 "Installing Plane-only task flow and worktree safety"
bash "$LIB/install_taskflow.sh" || die "Plane-only task-flow install failed; inspect the reported migration conflict"
bash "$LIB/install_worktree_lifecycle.sh" || die "worktree safety install failed; inspect the reported migration conflict"

step 6 7 "Installing the lazy Pi MCP adapter"
bash "$LIB/install_pi_packages.sh" || die "Pi adapter install failed"

step 7 7 "Wiring core harness policies"
# Shared ownership-aware wiring; no legacy routing or service/index warmups.
bash "$LIB/wire_cc.sh"    || die "Claude wiring failed"
bash "$LIB/wire_codex.sh" || die "Codex wiring failed"
bash "$LIB/wire_pi.sh"    || die "Pi wiring failed"
bash "$LIB/wire_omp.sh"   || die "OMP wiring failed"
bash "$LIB/wire_path.sh"  || warn "PATH wiring skipped"

for tool in agentmemory zg codedb rtk ruff; do
  command -v "$tool" >/dev/null 2>&1 || die "$tool missing after installation; slim is not ready"
done
[ -f "$MEGAI_HOME/ux-ui-agent-skills/package.json" ] || die "UX/UI kit missing after installation"
[ -d "$MEGAI_HOME/mattpocock-skills/skills" ] || die "Matt skill kit missing after installation"
python3 "$LIB/slim_wiring.py" all --verify
ok "MEGAI slim core ready"
echo
echo "    Open a new shell (or 'source ~/.zshrc') so PATH picks up megai/bin"
echo "    megai           # verify the current Git worktree and Plane wiring"
echo "    megai cc|codex|pi|omp  # launch without service/index warmup"
echo "    megai start agent-memory  # start memory explicitly when needed"
echo "    megai reindex            # rebuild zvec explicitly when needed"
echo "    Existing user config, project data, indexes, and credentials are preserved."
echo

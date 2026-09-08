#!/usr/bin/env bash
# Slim MEGAI installer pipeline: task-appropriate tools, including core tgrep and codedb.
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
# Validate every selected client and every retirement manifest before any
# third-party installer, source publication, or config mutation.
python3 "$LIB/slim_wiring.py" all --check
python3 "$LIB/retire_legacy_sources.py" --check
command -v git >/dev/null 2>&1 || die "Git required"
command -v rg >/dev/null 2>&1 || die "ripgrep required; install rg before retrying"
require_or_install_jq
require_or_install_node
if ! command -v ruff >/dev/null 2>&1 && ! command -v uv >/dev/null 2>&1; then require_or_install_pipx; fi
ok "$MEGAI_OS/$MEGAI_ARCH (node=$MEGAI_HAS_NODE py=$MEGAI_HAS_PY jq=$MEGAI_HAS_JQ)"

state_init
ok "state initialized -> $MEGAI_HOME/state.json"

step 2 7 "Installing isolated Headroom runtime"
if [ "${MEGAI_HEADROOM_PREPARED:-0}" != 1 ]; then
  bash "$LIB/install_headroom.sh" || die "Headroom install failed"
fi
state_set '.tools.headroom' '{"installed":true,"version":"0.37.0","mode":"local-library"}'

# Retire only verified MEGAI-owned legacy registrations and source files,
# after Headroom is ready and before publication/wiring cleanup.
bash "$LIB/retire_argent.sh"
bash "$LIB/retire_numasec.sh"
bash "$LIB/retire_openspec.sh"
python3 "$LIB/retire_legacy_sources.py"

step 3 7 "Installing core search (indexing starts only on request)"
bash "$LIB/install_tgrep.sh" || die "tgrep install failed"
bash "$LIB/install_zvec_grep.sh" || die "zvec-grep install failed"
bash "$LIB/install_codedb.sh" || die "codedb install failed"

step 4 7 "Installing Ruff and requested skill kits"
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

for tool in tgrep zg codedb ruff; do
  command -v "$tool" >/dev/null 2>&1 || die "$tool missing after installation; slim is not ready"
done
[ -f "$MEGAI_HOME/ux-ui-agent-skills/package.json" ] || die "UX/UI kit missing after installation"
[ -d "$MEGAI_HOME/mattpocock-skills/skills" ] || die "Matt skill kit missing after installation"
python3 "$LIB/slim_wiring.py" all --verify
if command -v pi >/dev/null 2>&1 && bash "$LIB/verify_headroom_activation.sh"; then
  ok "MEGAI core ready; native Pi Headroom activation verified"
else
  activation_status=$?
  [ "$activation_status" = 2 ] || [ ! -x "$LIB/verify_headroom_activation.sh" ] || warn "Headroom installed; native Pi activation is inactive or unavailable (resources preserved)"
  ok "MEGAI core ready; Headroom inactive status reported honestly"
fi
echo
echo "    Open a new shell (or 'source ~/.zshrc') so PATH picks up megai/bin"
echo "    megai           # verify the current Git worktree and Plane wiring"
echo "    megai cc|codex|pi|omp  # launch without service/index warmup"
echo "    megai headroom doctor   # verify local compression and memory runtime"
echo "    megai headroom recall 'query'      # explicit local memory"
echo "    megai headroom save 'text'         # only when persistence is requested"
echo "    megai reindex            # rebuild zvec explicitly when needed"
echo "    Existing user config, project data, indexes, and credentials are preserved."
echo

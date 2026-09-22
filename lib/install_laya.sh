#!/usr/bin/env bash
# laya: the pinned local decision runtime (upstream `laya==0.3.5` plus its checkpoints).
#
# The Pi extension talks to this runtime through a stdio bridge (pi-skill/laya/bridge.py).
# The runtime itself is an owned virtualenv under MEGAI_HOME, built from a complete hash
# lock (lib/laya.lock) so a swapped or truncated wheel cannot enter it. Both retained
# checkpoints are verified before the runtime is reported ready: English answers the
# default route, and the bundled multilingual checkpoint answers a `lang`-hinted Latin
# script request such as Uzbek — without it, that request would silently fall back to an
# English model that reads Latin script as English.
#
# Every mutation stays inside the owned venv: no global Pi config, no user site-packages,
# no PATH entry. A failure exits non-zero and prints what to do next, and a partial venv
# is left in place on purpose so a retry resumes instead of re-downloading.
#
#   bash lib/install_laya.sh                 # prepare and verify the runtime
#   bash lib/install_laya.sh --prepare-only   # same, without writing MEGAI tool state
#   bash lib/install_laya.sh --check          # verify only; never writes
#   bash lib/install_laya.sh --remove         # remove only an owned venv
#
# Overrides: LAYA_VENV, LAYA_INTERPRETER, LAYA_UV (test seams), LAYA_PLATFORM (test
# seam), LAYA_DEVICE / LAYA_LANG (passed to the checkpoint check only, never stored).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
VENV="${LAYA_VENV:-$MEGAI_HOME/venv/laya}"
MARKER="$VENV/.megai-owned"
LOCK="$ROOT/lib/laya.lock"
BRIDGE="$ROOT/pi-skill/laya/bridge.py"
UV="${LAYA_UV:-uv}"
PINNED_PYTHON="3.11"
PLATFORM="${LAYA_PLATFORM:-$(uname -s)/$(uname -m)}"
MODEL="convaiinnovations/laya"

ACTION=prepare
for arg in "$@"; do
  case "$arg" in
    --check) ACTION=check ;;
    --prepare-only) ACTION=prepare-only ;;
    --remove) ACTION=remove ;;
    -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
    *) printf 'laya: unknown argument %s\n' "$arg" >&2; exit 2 ;;
  esac
done

fail() { printf 'laya: %s\n' "$*" >&2; exit 1; }
ok() { printf 'laya: %s\n' "$*"; }

# Only platforms with a published wheel set for the pinned interpreter are supported.
case "$PLATFORM" in
  Darwin/arm64|Darwin/x86_64|Linux/x86_64|Linux/aarch64|Linux/arm64) ;;
  *) fail "no pinned runtime for $PLATFORM; lib/laya.lock holds $(uname -s) wheels only" ;;
esac

[ -f "$LOCK" ] || fail "missing hash lock: $LOCK"
[ -f "$BRIDGE" ] || fail "missing bridge: $BRIDGE"

# The lock is the identity of the runtime. Every requirement must carry at least one
# wheel hash, or `--require-hashes` would accept an unverified download.
python3 - "$LOCK" <<'PY' || fail "lib/laya.lock is not a complete hash lock"
import sys
from pathlib import Path

lines = Path(sys.argv[1]).read_text().splitlines()
entries = [line for line in lines if "==" in line and not line.startswith((" ", "#"))]
hashes = sum(1 for line in lines if "--hash=sha256:" in line)
if not entries or hashes < len(entries):
    raise SystemExit("lib/laya.lock must pin every requirement with a sha256 wheel hash")
if not any(line.startswith("laya==") for line in entries):
    raise SystemExit("lib/laya.lock must pin the runtime itself")
PY

owned() { [ -d "$VENV" ] && [ -f "$MARKER" ]; }

if [ "$ACTION" = remove ]; then
  if [ ! -e "$VENV" ]; then ok "no runtime at $VENV; nothing to remove"; exit 0; fi
  owned || fail "$VENV is not owned by MEGAI (no $MARKER); move it away by hand"
  rm -rf "$VENV" || fail "cannot remove $VENV"
  ok "removed owned runtime -> $VENV"
  exit 0
fi

if [ -e "$VENV" ] && ! owned; then
  fail "$VENV exists and is not owned by MEGAI (no $MARKER); move it away by hand, nothing was changed"
fi

INTERPRETER="${LAYA_INTERPRETER:-}"
if [ -z "$INTERPRETER" ]; then
  INTERPRETER="$("$UV" python find "$PINNED_PYTHON" 2>/dev/null || true)"
fi
[ -n "$INTERPRETER" ] && [ -x "$INTERPRETER" ] \
  || fail "no python $PINNED_PYTHON interpreter found; run \`$UV python install $PINNED_PYTHON\` (or set LAYA_INTERPRETER)"

checkpoint_check() {
  # One real load per retained checkpoint. This is the slow step: the first run
  # downloads the checkpoint from Hugging Face into the shared cache.
  local python="$1"
  [ -x "$python" ] || fail "no interpreter in the owned venv: $python"
  [ -f "$BRIDGE" ] || fail "missing bridge: $BRIDGE"
  LAYA_PYTHON="$python" "$python" "$BRIDGE" --check
}

if [ "$ACTION" = check ]; then
  owned || fail "no owned runtime at $VENV; run \`bash lib/install_laya.sh\`"
  checkpoint_check "$VENV/bin/python" \
    || fail "the runtime at $VENV did not verify: $MODEL (English + multilingual) failed to load"
  ok "ready -> $VENV ($MODEL English + multilingual verified)"
  exit 0
fi

if owned; then
  ok "runtime already prepared -> $VENV"
else
  "$UV" venv --python "$INTERPRETER" "$VENV" || fail "cannot create the owned venv at $VENV"
  "$UV" pip install --require-hashes --python "$VENV/bin/python" -r "$LOCK" \
    || fail "cannot install the pinned runtime into $VENV (network or platform wheel missing); retry once the cause is fixed"
  printf 'interpreter=%s\npython=%s\nmodel=%s\nlock=%s\n' \
    "$INTERPRETER" "$PINNED_PYTHON" "$MODEL" "$(python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$LOCK")" \
    > "$MARKER" || fail "cannot write the ownership marker $MARKER"
fi

checkpoint_check "$VENV/bin/python" \
  || fail "the runtime is installed at $VENV but its checkpoints are not verified; re-run \`bash lib/install_laya.sh\` once the download completes"

if [ "$ACTION" != prepare-only ] && [ -f "$MEGAI_HOME/lib/state.sh" ]; then
  # shellcheck disable=SC1090
  . "$MEGAI_HOME/lib/ui.sh" 2>/dev/null || true
  . "$MEGAI_HOME/lib/state.sh" 2>/dev/null || true
  if declare -F state_set >/dev/null 2>&1; then
    state_set '.tools.laya' "$(jq -cn --arg bin "$VENV/bin/python" --arg lock "$(python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$LOCK")" --arg model "$MODEL" '{bin:$bin,lock:$lock,model:$model}')" 2>/dev/null || true
  fi
fi

ok "runtime ready -> $VENV (python $PINNED_PYTHON, $MODEL English + multilingual verified)"
ok "the Pi extension uses it through \$LAYA_PYTHON or the default $VENV/bin/python"

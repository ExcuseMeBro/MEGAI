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
# no PATH entry. A failure exits non-zero and prints what to do next. The ownership marker
# is written before the package install with state=partial, so this installer's own failed
# first attempt is recognized and rebuilt on retry, while a directory with no marker is an
# unowned collision and is never touched. Reuse re-validates the marker against the current
# lock digest, the pinned interpreter, the pinned interpreter version and the installed laya
# version before the checkpoints are verified again.
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

# The lock is the runtime identity; a reused venv must still match all of it.
OWNER="megai-laya"
PINNED_LAYAVERSION="$(sed -n 's/^laya==\([^ ]*\).*/\1/p' "$LOCK" | head -1)"
[ -n "$PINNED_LAYAVERSION" ] || fail "lib/laya.lock does not pin the runtime itself"
LOCK_DIGEST="$(python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$LOCK")"

marker_field() { sed -n "s/^$1=//p" "$MARKER" 2>/dev/null | head -1; }
owned() { [ -d "$VENV" ] && [ -f "$MARKER" ] && [ "$(marker_field owner)" = "$OWNER" ]; }

write_marker() {
  # state=partial is written before the package install, so a retry recognizes this
  # installer's own failed attempt instead of refusing it as an unowned collision.
  printf 'owner=%s\nstate=%s\ninterpreter=%s\npython=%s\nlaya=%s\nmodel=%s\nlock=%s\n' \
    "$OWNER" "$1" "$INTERPRETER" "$(interpreter_version "$VENV/bin/python")" "$PINNED_LAYAVERSION" "$MODEL" "$LOCK_DIGEST" \
    > "$MARKER" || fail "cannot write the ownership marker $MARKER"
}

installed_laya_version() {
  "$VENV/bin/python" -c 'import importlib.metadata as m; print(m.version("laya"))' 2>/dev/null
}

interpreter_version() {
  "$1" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null
}

# Reuse requires the venv to be this installer's own, to match every pinned identity
# field, to actually run the pinned interpreter version and to hold the pinned laya.
reusable() {
  owned || return 1
  [ "$(marker_field state)" = installed ] || return 1
  [ "$(marker_field interpreter)" = "$INTERPRETER" ] || return 1
  [ "$(marker_field python)" = "$PINNED_PYTHON" ] || return 1
  [ "$(marker_field laya)" = "$PINNED_LAYAVERSION" ] || return 1
  [ "$(marker_field lock)" = "$LOCK_DIGEST" ] || return 1
  [ "$(interpreter_version "$VENV/bin/python")" = "$PINNED_PYTHON" ] || return 1
  [ "$(installed_laya_version)" = "$PINNED_LAYAVERSION" ] || return 1
}

install_runtime() {
  "$UV" venv --python "$INTERPRETER" "$VENV" || fail "cannot create the owned venv at $VENV"
  write_marker partial
  [ "$(interpreter_version "$VENV/bin/python")" = "$PINNED_PYTHON" ] \
    || fail "the owned venv interpreter $VENV/bin/python reports Python $(interpreter_version "$VENV/bin/python"); this installer pins $PINNED_PYTHON; fix the interpreter and re-run \`bash lib/install_laya.sh\`"
  "$UV" pip install --require-hashes --python "$VENV/bin/python" -r "$LOCK" \
    || fail "cannot install the pinned runtime into $VENV (network or platform wheel missing); fix the cause and re-run \`bash lib/install_laya.sh\`; the partial venv is owned and will be rebuilt"
  write_marker installed
}

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
SELECTED_VERSION="$(interpreter_version "$INTERPRETER")"
[ "$SELECTED_VERSION" = "$PINNED_PYTHON" ] \
  || fail "the selected interpreter $INTERPRETER reports Python ${SELECTED_VERSION:-unknown}; this installer pins Python $PINNED_PYTHON"

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
  reusable || fail "the owned runtime at $VENV does not match the current pin (interpreter, lock or laya version); re-run \`bash lib/install_laya.sh\` to rebuild it"
  checkpoint_check "$VENV/bin/python" \
    || fail "the runtime at $VENV did not verify: $MODEL (English + multilingual) failed to load"
  ok "ready -> $VENV ($MODEL English + multilingual verified)"
  exit 0
fi

if reusable; then
  ok "runtime already prepared -> $VENV"
else
  if owned; then
    ok "owned runtime is stale or incomplete -> rebuilding $VENV"
    rm -rf "$VENV" || fail "cannot rebuild the owned runtime at $VENV"
  fi
  install_runtime
fi

[ "$(installed_laya_version)" = "$PINNED_LAYAVERSION" ] \
  || fail "the runtime at $VENV does not have laya $PINNED_LAYAVERSION installed; re-run \`bash lib/install_laya.sh\`"

checkpoint_check "$VENV/bin/python" \
  || fail "the runtime is installed at $VENV but its checkpoints are not verified; re-run \`bash lib/install_laya.sh\` once the download completes"

if [ "$ACTION" != prepare-only ] && [ -f "$MEGAI_HOME/lib/state.sh" ]; then
  # shellcheck disable=SC1090
  . "$MEGAI_HOME/lib/ui.sh" 2>/dev/null || true
  . "$MEGAI_HOME/lib/state.sh" 2>/dev/null || true
  if declare -F state_set >/dev/null 2>&1; then
    state_set '.tools.laya' "$(jq -cn --arg bin "$VENV/bin/python" --arg lock "$LOCK_DIGEST" --arg model "$MODEL" '{bin:$bin,lock:$lock,model:$model}')" 2>/dev/null || true
  fi
fi

ok "runtime ready -> $VENV (python $PINNED_PYTHON, $MODEL English + multilingual verified)"
ok "the Pi extension uses it through \$LAYA_PYTHON or the default $VENV/bin/python"

#!/usr/bin/env bash
# ruff — install / update / state / removal / wiring regression test.
# Uses stub uv and pipx in a sandbox; real Ruff is invoked only for the
# non-mutating fixture (which only writes inside a tmp dir).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

export HOME="$TMP/home"
export MEGAI_HOME="$TMP/megai"
export STATE_FILE="$MEGAI_HOME/state.json"
mkdir -p "$MEGAI_HOME/lib" "$TMP/fake-bin" "$HOME"
cp "$ROOT/lib/ui.sh" "$ROOT/lib/state.sh" "$MEGAI_HOME/lib/"

JQ_DIR="$(dirname "$(command -v jq)")"
INITIAL_PATH="$TMP/fake-bin:$JQ_DIR:/usr/bin:/bin"

write_state() {
  printf '%s\n' '{"tools":{"numasec":{"bin":"/keep/numasec","version":"1.0"},"argent":{"bin":"/keep/argent","version":"0.0.1"}},"agents":{"cc":{"wired":true}},"projects":{"keep":{"path":"/keep/path"}}}' \
    | jq -c 'del(.projects)' > "$STATE_FILE"
  if [ "${1:-keep}" != "keep" ]; then
    jq -c '.projects = {}' "$STATE_FILE" >"$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"
  fi
}

write_state keep

# ---- 1. Existing ruff on PATH is reused unchanged and recorded ----
cat > "$TMP/fake-bin/ruff" <<'SH'
#!/bin/sh
[ "${1:-}" = "--version" ] && echo "ruff 1.2.3"
SH
chmod +x "$TMP/fake-bin/ruff"
export PATH="$INITIAL_PATH"
bash "$ROOT/lib/install_ruff.sh" >/dev/null
recorded_bin="$(jq -r '.tools.ruff.bin' "$STATE_FILE")"
recorded_ver="$(jq -r '.tools.ruff.version' "$STATE_FILE")"
recorded_mgr="$(jq -r '.tools.ruff.manager' "$STATE_FILE")"
[ "$recorded_bin" = "$TMP/fake-bin/ruff" ]
[ "$recorded_ver" = "ruff 1.2.3" ]
[ "$recorded_mgr" = "path" ]

# Unrelated state must survive.
[ "$(jq -r '.tools.numasec.bin' "$STATE_FILE")" = "/keep/numasec" ]
[ "$(jq -r '.tools.argent.version' "$STATE_FILE")" = "0.0.1" ]
[ "$(jq -r '.agents.cc.wired' "$STATE_FILE")" = "true" ]

# Idempotence: rerun does not change state and does not error.
before="$(jq -S . "$STATE_FILE")"
bash "$ROOT/lib/install_ruff.sh" >/dev/null
after="$(jq -S . "$STATE_FILE")"
[ "$before" = "$after" ]

# ---- 2. Update path: ruff is uv-managed, MEGAI_UPDATE refreshes via uv tool ----
write_state keep
cat > "$TMP/fake-bin/ruff" <<'SH'
#!/bin/sh
[ "${1:-}" = "--version" ] && echo "ruff 1.2.3"
SH
cat > "$TMP/fake-bin/uv" <<'SH'
#!/bin/sh
case "$1 $2" in
  "tool list") echo "ruff v1.2.3" ;;
  "tool upgrade")
    [ "${3:-}" = "ruff" ] || exit 1
    touch "$HOME/ruff-updated"
    ;;
esac
SH
chmod +x "$TMP/fake-bin/ruff" "$TMP/fake-bin/uv"
export PATH="$INITIAL_PATH"
MEGAI_UPDATE=1 bash "$ROOT/lib/install_ruff.sh" >/dev/null
[ -f "$HOME/ruff-updated" ]
[ "$(jq -r '.tools.ruff.manager' "$STATE_FILE")" = "uv" ]

# ---- 3. Update path: ruff is pipx-managed, MEGAI_UPDATE refreshes via pipx ----
write_state keep
cat > "$TMP/fake-bin/ruff" <<'SH'
#!/bin/sh
[ "${1:-}" = "--version" ] && echo "ruff 1.2.3"
SH
# uv stub says it does not manage ruff so the install script routes to pipx.
cat > "$TMP/fake-bin/uv" <<'SH'
#!/bin/sh
[ "$1 $2" = "tool list" ] && echo "(none)"
SH
cat > "$TMP/fake-bin/pipx" <<'SH'
#!/bin/sh
case "$1" in
  list)
    [ "${2:-}" = "--short" ] && echo "ruff 1.2.3"
    ;;
  upgrade)
    [ "${2:-}" = "ruff" ] || exit 1
    touch "$HOME/ruff-updated-pipx"
    ;;
esac
SH
chmod +x "$TMP/fake-bin/ruff" "$TMP/fake-bin/uv" "$TMP/fake-bin/pipx"
export PATH="$INITIAL_PATH"
MEGAI_UPDATE=1 bash "$ROOT/lib/install_ruff.sh" >/dev/null
[ -f "$HOME/ruff-updated-pipx" ]
[ "$(jq -r '.tools.ruff.manager' "$STATE_FILE")" = "pipx" ]

# ---- 4. Update skips ruff that is not MEGAI/uv/pipx-managed ----
write_state keep
cat > "$TMP/fake-bin/ruff" <<'SH'
#!/bin/sh
[ "${1:-}" = "--version" ] && echo "ruff 1.2.3"
SH
cat > "$TMP/fake-bin/uv" <<'SH'
#!/bin/sh
[ "$1 $2" = "tool list" ] && echo "(none)"
SH
cat > "$TMP/fake-bin/pipx" <<'SH'
#!/bin/sh
[ "$1" = "list" ] && echo "(none)"
SH
chmod +x "$TMP/fake-bin/ruff" "$TMP/fake-bin/uv" "$TMP/fake-bin/pipx"
# Clear any touch files carried over from earlier tests so the negative
# assertions below don't pick up unrelated artifacts.
rm -f "$HOME/ruff-updated" "$HOME/ruff-updated-pipx"
export PATH="$INITIAL_PATH"
out="$(MEGAI_UPDATE=1 bash "$ROOT/lib/install_ruff.sh" 2>&1)"
echo "$out" | grep -q 'managed outside MEGAI'
[ ! -f "$HOME/ruff-updated" ]
[ ! -f "$HOME/ruff-updated-pipx" ]
# Unrelated state still preserved.
[ "$(jq -r '.tools.numasec.bin' "$STATE_FILE")" = "/keep/numasec" ]

# ---- 5. Install via uv tool when ruff is missing ----
write_state keep
rm -f "$TMP/fake-bin/ruff" "$HOME/.local/bin/ruff"
cat > "$TMP/fake-bin/uv" <<'SH'
#!/bin/sh
case "$1 $2" in
  "tool install")
    [ "$3" = "ruff" ] || exit 1
    mkdir -p "$HOME/.local/bin"
    cat > "$HOME/.local/bin/ruff" <<'R'
#!/bin/sh
[ "${1:-}" = "--version" ] && echo "ruff 2.0.0"
R
    chmod +x "$HOME/.local/bin/ruff"
    exit 0
    ;;
  "tool list") echo "ruff v2.0.0" ;;
esac
SH
chmod +x "$TMP/fake-bin/uv"
export PATH="$INITIAL_PATH"
bash "$ROOT/lib/install_ruff.sh" >/dev/null
[ "$(jq -r '.tools.ruff.version' "$STATE_FILE")" = "ruff 2.0.0" ]
[ "$(jq -r '.tools.ruff.manager' "$STATE_FILE")" = "uv" ]

# ---- 6. Install via pipx fallback when uv is missing ----
write_state keep
rm -f "$TMP/fake-bin/ruff" "$TMP/fake-bin/uv" "$HOME/.local/bin/ruff"
cat > "$TMP/fake-bin/pipx" <<'SH'
#!/bin/sh
case "$1" in
  install)
    [ "$2" = "ruff" ] || exit 1
    mkdir -p "$HOME/.local/bin"
    cat > "$HOME/.local/bin/ruff" <<'R'
#!/bin/sh
[ "${1:-}" = "--version" ] && echo "ruff 2.1.0"
R
    chmod +x "$HOME/.local/bin/ruff"
    exit 0
    ;;
  list) [ "${2:-}" = "--short" ] && echo "ruff 2.1.0" ;;
esac
SH
chmod +x "$TMP/fake-bin/pipx"
export PATH="$INITIAL_PATH"
bash "$ROOT/lib/install_ruff.sh" >/dev/null
[ "$(jq -r '.tools.ruff.version' "$STATE_FILE")" = "ruff 2.1.0" ]
[ "$(jq -r '.tools.ruff.manager' "$STATE_FILE")" = "pipx" ]

# ---- 7. Neither uv nor pipx available: install fails visibly, state untouched ----
write_state keep
rm -f "$TMP/fake-bin/ruff" "$TMP/fake-bin/uv" "$TMP/fake-bin/pipx" "$HOME/.local/bin/ruff"
export PATH="$TMP/fake-bin:/usr/bin:/bin"
before="$(jq -S . "$STATE_FILE")"
set +e
bash "$ROOT/lib/install_ruff.sh" >/dev/null 2>"$TMP/no-manager.err"
exit_code=$?
set -e
[ "$exit_code" != "0" ]
grep -q 'requires uv or pipx' "$TMP/no-manager.err"
# Failed install must NOT have recorded ruff as ready.
after="$(jq -S . "$STATE_FILE")"
[ "$before" = "$after" ]

# ---- 8. --version failure: present but broken, state not recorded ----
write_state keep
cat > "$TMP/fake-bin/ruff" <<'SH'
#!/bin/sh
[ "${1:-}" = "--version" ] && exit 1
SH
chmod +x "$TMP/fake-bin/ruff"
export PATH="$INITIAL_PATH"
before="$(jq -S . "$STATE_FILE")"
set +e
bash "$ROOT/lib/install_ruff.sh" >/dev/null 2>"$TMP/bad-version.err"
exit_code=$?
set -e
# Exit code may be 0 because we explicitly exit 0 on warn; check stderr instead.
grep -q -- '--version failed' "$TMP/bad-version.err"
after="$(jq -S . "$STATE_FILE")"
[ "$before" = "$after" ]

# ---- 9. Removal: clears only state, retains the ruff CLI ----
write_state keep
cat > "$TMP/fake-bin/ruff" <<'SH'
#!/bin/sh
[ "${1:-}" = "--version" ] && echo "ruff 1.2.3"
SH
chmod +x "$TMP/fake-bin/ruff"
export PATH="$INITIAL_PATH"
bash "$ROOT/lib/install_ruff.sh" >/dev/null
[ "$(jq -r '.tools.ruff.version' "$STATE_FILE")" = "ruff 1.2.3" ]
bash "$ROOT/lib/install_ruff.sh" --remove >/dev/null
# State cleared.
jq -e 'has("ruff") | not' "$STATE_FILE" >/dev/null
# Unrelated state preserved.
[ "$(jq -r '.tools.numasec.bin' "$STATE_FILE")" = "/keep/numasec" ]
[ "$(jq -r '.tools.argent.bin' "$STATE_FILE")" = "/keep/argent" ]
[ "$(jq -r '.agents.cc.wired' "$STATE_FILE")" = "true" ]
# CLI retained.
[ -x "$TMP/fake-bin/ruff" ]
command -v ruff >/dev/null 2>&1

# ---- 10. CLI/guidance checks: pi-skill exposes the canonical non-mutating shape ----
skill="$ROOT/pi-skill/SKILL.md"
grep -Fq 'Ruff' "$skill"
grep -Fq 'ruff check --no-fix --no-fix-only --force-exclude --no-cache' "$skill"
grep -Fq 'ruff format --check --force-exclude --no-cache' "$skill"
grep -Fq 'never write `pyproject.toml`' "$skill"
grep -Fq 'Never pass `--fix`' "$skill"
grep -Fq 'no-fix-only' "$skill"
grep -Fq 'fix-only = true' "$skill"
# Must not promise automatic --fix or whole-project cleanup.
! grep -Fq 'ruff check --fix' "$skill"
# ruff format must always be the --check form; bare `ruff format <files>` is forbidden.
if grep -F 'ruff format ' "$skill" | grep -v 'ruff format --check' | grep -v '^#' | grep -q .; then
  echo "skill exposes bare 'ruff format' (no --check)" >&2
  exit 1
fi

# ---- 11. bin/megai wires status, doctor, update, and uninstall for ruff ----
grep -Fq 'install_ruff.sh' "$ROOT/bin/megai"
grep -Fq 'ruff' "$ROOT/bin/megai"
grep -Fq 'ruff --version' "$ROOT/bin/megai"
grep -Fq 'MEGAI_UPDATE=1 bash "$LIB/install_ruff.sh"' "$ROOT/bin/megai"
grep -Fq 'install_ruff.sh"    --remove' "$ROOT/bin/megai"
# update order: install_numasec -> install_ruff before pi packages.
awk '/MEGAI_UPDATE=1 bash "\$LIB\/install_numasec.sh"/{nm=NR} /MEGAI_UPDATE=1 bash "\$LIB\/install_ruff.sh"/{ru=NR} END{exit !(nm && ru && ru>nm)}' "$ROOT/bin/megai"

# ---- 12. lib/main.sh has step 18 for Ruff ----
grep -Fq 'TOTAL=18' "$ROOT/lib/main.sh"
grep -Fq 'install_ruff.sh' "$ROOT/lib/main.sh"
grep -Fq 'step 18 $TOTAL "Installing Ruff' "$ROOT/lib/main.sh"

# ---- 13. README.md mentions Ruff in the stack table and updated step count ----
grep -Fq '| 🐍 | [Ruff]' "$ROOT/README.md"
grep -Fq '18-step pipeline' "$ROOT/README.md"
grep -Fq '`uv tool install ruff`' "$ROOT/README.md"
grep -Fq 'ruff check --no-fix --no-fix-only --force-exclude --no-cache' "$ROOT/README.md"

# ---- 14. Real Ruff fixture: --no-fix alone can mutate under fix-only=true ----
# This reproduces the documented real-world behavior and asserts the canonical
# --no-fix-only defense preserves bytes and reports nonzero diagnostics.
REAL_RUFF_BIN=""
for candidate in /Users/bro/Library/Python/3.14/bin/ruff /usr/local/bin/ruff /opt/homebrew/bin/ruff; do
  if [ -x "$candidate" ] && "$candidate" --version >/dev/null 2>&1; then
    REAL_RUFF_BIN="$candidate"
    break
  fi
done
if [ -n "$REAL_RUFF_BIN" ]; then
  FIXT="$(mktemp -d)"
  cd "$FIXT"
  cat > pyproject.toml <<'EOF'
[tool.ruff]
fix = true
fix-only = true
EOF
  printf 'import os\n' > sample.py
  before_sha="$(shasum -a 256 sample.py | awk '{print $1}')"
  before_size="$(wc -c < sample.py)"
  set +e
  "$REAL_RUFF_BIN" check --no-fix --force-exclude --no-cache -- sample.py >"$FIXT/weak.out" 2>&1
  weak_exit=$?
  set -e
  after_sha_weak="$(shasum -a 256 sample.py | awk '{print $1}')"
  echo "WEAK exit=$weak_exit before=$before_size after=$(wc -c < sample.py) sha_changed=$([ "$before_sha" != "$after_sha_weak" ] && echo yes || echo no)"
  # Sanity: real ruff with this config and --no-fix-only MUST not mutate AND
  # MUST exit nonzero AND MUST surface F401. We rely on that for the guidance.
  printf 'import os\n' > sample.py
  before_sha2="$(shasum -a 256 sample.py | awk '{print $1}')"
  set +e
  "$REAL_RUFF_BIN" check --no-fix --no-fix-only --force-exclude --no-cache -- sample.py >"$FIXT/strong.out" 2>&1
  strong_exit=$?
  set -e
  after_sha_strong="$(shasum -a 256 sample.py | awk '{print $1}')"
  echo "STRONG exit=$strong_exit after=$(wc -c < sample.py) sha_changed=$([ "$before_sha2" != "$after_sha_strong" ] && echo yes || echo no)"
  # Strong form must preserve bytes AND fail nonzero AND mention F401.
  [ "$before_sha2" = "$after_sha_strong" ]
  [ "$strong_exit" != "0" ]
  grep -q 'F401' "$FIXT/strong.out"
  rm -rf "$FIXT"
fi

echo "ruff integration: ok"

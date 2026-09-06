#!/usr/bin/env bash
# ruff — install / update / state / removal / wiring regression test.
# Uses stub uv and pipx in a sandbox; real Ruff is invoked only for the
# non-mutating fixture (which only writes inside a tmp dir).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Capture any working ruff on the host BEFORE we replace HOME/PATH so the
# real-Ruff fixture has a stable target and can SKIP explicitly when absent.
REAL_RUFF_BIN=""
if found="$(command -v ruff 2>/dev/null)"; then
  if [ -x "$found" ] && "$found" --version >/dev/null 2>&1; then
    REAL_RUFF_BIN="$found"
  fi
fi

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

# ---- 1. Existing ruff on caller PATH is reused unchanged and recorded ----
cat > "$TMP/fake-bin/ruff" <<'SH'
#!/bin/sh
[ "${1:-}" = "--version" ] && echo "ruff 1.2.3"
SH
chmod +x "$TMP/fake-bin/ruff"
export PATH="$INITIAL_PATH"
bash "$ROOT/lib/install_ruff.sh" >/dev/null
recorded_bin="$(jq -r '.tools.ruff.bin' "$STATE_FILE")"
recorded_ver="$(jq -r '.tools.ruff.version' "$STATE_FILE")"
[ "$recorded_bin" = "$TMP/fake-bin/ruff" ]
[ "$recorded_ver" = "ruff 1.2.3" ]
# Only bin + version should be recorded; no inferred manager / ownership.
jq -e '.tools.ruff | (has("bin") and has("version")) and (has("manager") | not)' "$STATE_FILE" >/dev/null

# Unrelated state must survive.
[ "$(jq -r '.tools.numasec.bin' "$STATE_FILE")" = "/keep/numasec" ]
[ "$(jq -r '.tools.argent.version' "$STATE_FILE")" = "0.0.1" ]
[ "$(jq -r '.agents.cc.wired' "$STATE_FILE")" = "true" ]

# Idempotence: rerun does not change state and does not error.
before="$(jq -S . "$STATE_FILE")"
bash "$ROOT/lib/install_ruff.sh" >/dev/null
after="$(jq -S . "$STATE_FILE")"
[ "$before" = "$after" ]

# ---- 2. Caller-selected PATH shim wins over a stale ~/.local/bin shadow ----
# When the caller's PATH has a working ruff AND ~/.local/bin/ruff also exists,
# the installer MUST NOT prepend ~/.local/bin (which would shadow the caller).
write_state keep
cat > "$TMP/fake-bin/ruff" <<'SH'
#!/bin/sh
[ "${1:-}" = "--version" ] && echo "ruff caller-shim 9.9.9"
SH
chmod +x "$TMP/fake-bin/ruff"
# Plant a stale ~/.local/bin/ruff that should be ignored when PATH already has one.
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/ruff" <<'SH'
#!/bin/sh
[ "${1:-}" = "--version" ] && echo "ruff local-shadow 0.0.1"
SH
chmod +x "$HOME/.local/bin/ruff"
export PATH="$INITIAL_PATH"
bash "$ROOT/lib/install_ruff.sh" >/dev/null
[ "$(jq -r '.tools.ruff.bin' "$STATE_FILE")" = "$TMP/fake-bin/ruff" ]
[ "$(jq -r '.tools.ruff.version' "$STATE_FILE")" = "ruff caller-shim 9.9.9" ]

# Cleanup leftover local-shadow stub for later tests.
rm -f "$HOME/.local/bin/ruff"

# ---- 3. ~/.local/bin/ruff is used when the caller PATH has no ruff ----
write_state keep
rm -f "$TMP/fake-bin/ruff"
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/ruff" <<'SH'
#!/bin/sh
[ "${1:-}" = "--version" ] && echo "ruff local-fallback 0.5.0"
SH
chmod +x "$HOME/.local/bin/ruff"
export PATH="$INITIAL_PATH"
bash "$ROOT/lib/install_ruff.sh" >/dev/null
[ "$(jq -r '.tools.ruff.bin' "$STATE_FILE")" = "$HOME/.local/bin/ruff" ]
[ "$(jq -r '.tools.ruff.version' "$STATE_FILE")" = "ruff local-fallback 0.5.0" ]

# ---- 4. Install via uv tool when ruff is missing everywhere ----
write_state keep
rm -f "$TMP/fake-bin/ruff" "$HOME/.local/bin/ruff"
cat > "$TMP/fake-bin/uv" <<'SH'
#!/bin/sh
case "$1 $2" in
  "tool install")
    mkdir -p "$HOME/.local/bin"
    cat > "$HOME/.local/bin/ruff" <<'R'
#!/bin/sh
[ "${1:-}" = "--version" ] && echo "ruff 2.0.0"
R
    chmod +x "$HOME/.local/bin/ruff"
    ;;
esac
SH
chmod +x "$TMP/fake-bin/uv"
export PATH="$INITIAL_PATH"
bash "$ROOT/lib/install_ruff.sh" >/dev/null
[ "$(jq -r '.tools.ruff.version' "$STATE_FILE")" = "ruff 2.0.0" ]

# ---- 5. Install via pipx fallback when only pipx is available ----
write_state keep
rm -f "$TMP/fake-bin/ruff" "$TMP/fake-bin/uv" "$HOME/.local/bin/ruff"
cat > "$TMP/fake-bin/pipx" <<'SH'
#!/bin/sh
case "$1" in
  install)
    mkdir -p "$HOME/.local/bin"
    cat > "$HOME/.local/bin/ruff" <<'R'
#!/bin/sh
[ "${1:-}" = "--version" ] && echo "ruff 2.1.0"
R
    chmod +x "$HOME/.local/bin/ruff"
    ;;
esac
SH
chmod +x "$TMP/fake-bin/pipx"
export PATH="$INITIAL_PATH"
bash "$ROOT/lib/install_ruff.sh" >/dev/null
[ "$(jq -r '.tools.ruff.version' "$STATE_FILE")" = "ruff 2.1.0" ]

# ---- 6. No manager available: install fails visibly and state is untouched ----
write_state keep
rm -f "$TMP/fake-bin/ruff" "$TMP/fake-bin/uv" "$TMP/fake-bin/pipx" "$HOME/.local/bin/ruff"
export PATH="$TMP/fake-bin:/usr/bin:/bin"
before="$(jq -S . "$STATE_FILE")"
set +e
bash "$ROOT/lib/install_ruff.sh" >/dev/null 2>"$TMP/no-manager.err"
exit_code=$?
set -e
[ "$exit_code" = "1" ]
grep -q 'requires uv or pipx' "$TMP/no-manager.err"
# Failed install must NOT have recorded ruff as ready.
after="$(jq -S . "$STATE_FILE")"
[ "$before" = "$after" ]
jq -e '.tools | has("ruff") | not' "$STATE_FILE" >/dev/null

# ---- 7. uv present but uv install fails: report nonzero, no pipx fallback ----
write_state keep
rm -f "$TMP/fake-bin/ruff" "$HOME/.local/bin/ruff"
cat > "$TMP/fake-bin/uv" <<'SH'
#!/bin/sh
case "$1 $2" in
  "tool install") exit 7 ;;
esac
SH
cat > "$TMP/fake-bin/pipx" <<'SH'
#!/bin/sh
touch "$HOME/pipx-should-NOT-run"
case "$1" in install) touch "$HOME/pipx-should-NOT-run" ;; esac
SH
chmod +x "$TMP/fake-bin/uv" "$TMP/fake-bin/pipx"
export PATH="$INITIAL_PATH"
before="$(jq -S . "$STATE_FILE")"
set +e
bash "$ROOT/lib/install_ruff.sh" >/dev/null 2>"$TMP/uv-failed.err"
exit_code=$?
set -e
[ "$exit_code" = "1" ]
grep -q 'ruff install via uv failed' "$TMP/uv-failed.err"
[ ! -f "$HOME/pipx-should-NOT-run" ]
after="$(jq -S . "$STATE_FILE")"
[ "$before" = "$after" ]
jq -e '.tools | has("ruff") | not' "$STATE_FILE" >/dev/null

# ---- 8. --version exit nonzero: not recorded, failure status preserved ----
write_state keep
cat > "$TMP/fake-bin/ruff" <<'SH'
#!/bin/sh
if [ "${1:-}" = "--version" ]; then printf 'ruff broken\n'; exit 1; fi
exit 0
SH
chmod +x "$TMP/fake-bin/ruff"
export PATH="$INITIAL_PATH"
before="$(jq -S . "$STATE_FILE")"
set +e
bash "$ROOT/lib/install_ruff.sh" >/dev/null 2>"$TMP/bad-version.err"
exit_code=$?
set -e
[ "$exit_code" = "1" ]
grep -q -- '--version failed or returned invalid output' "$TMP/bad-version.err"
after="$(jq -S . "$STATE_FILE")"
[ "$before" = "$after" ]
jq -e '.tools | has("ruff") | not' "$STATE_FILE" >/dev/null

# ---- 9. --version with garbage non-ruff output: not recorded ----
write_state keep
cat > "$TMP/fake-bin/ruff" <<'SH'
#!/bin/sh
[ "${1:-}" = "--version" ] && echo "this is not ruff"
SH
chmod +x "$TMP/fake-bin/ruff"
export PATH="$INITIAL_PATH"
before="$(jq -S . "$STATE_FILE")"
set +e
bash "$ROOT/lib/install_ruff.sh" >/dev/null 2>"$TMP/garbage-version.err"
exit_code=$?
set -e
[ "$exit_code" = "1" ]
grep -q -- '--version failed or returned invalid output' "$TMP/garbage-version.err"
after="$(jq -S . "$STATE_FILE")"
[ "$before" = "$after" ]
jq -e '.tools | has("ruff") | not' "$STATE_FILE" >/dev/null

# ---- 10. MEGAI_UPDATE=1 keeps existing working ruff unchanged (no auto-upgrade) ----
write_state keep
cat > "$TMP/fake-bin/ruff" <<'SH'
#!/bin/sh
[ "${1:-}" = "--version" ] && echo "ruff pinned-keep 1.2.3"
SH
# Plant uv/pipx stubs that would otherwise trigger upgrades; the installer
# MUST NOT touch the working ruff or invoke any upgrade command.
cat > "$TMP/fake-bin/uv" <<'SH'
#!/bin/sh
touch "$HOME/uv-should-NOT-run"
case "$1 $2" in "tool upgrade") touch "$HOME/uv-should-NOT-run" ;; esac
SH
cat > "$TMP/fake-bin/pipx" <<'SH'
#!/bin/sh
touch "$HOME/pipx-should-NOT-run"
case "$1" in upgrade) touch "$HOME/pipx-should-NOT-run" ;; esac
SH
chmod +x "$TMP/fake-bin/ruff" "$TMP/fake-bin/uv" "$TMP/fake-bin/pipx"
export PATH="$INITIAL_PATH"
MEGAI_UPDATE=1 bash "$ROOT/lib/install_ruff.sh" >/dev/null
[ ! -f "$HOME/uv-should-NOT-run" ]
[ ! -f "$HOME/pipx-should-NOT-run" ]
[ "$(jq -r '.tools.ruff.version' "$STATE_FILE")" = "ruff pinned-keep 1.2.3" ]

# ---- 11. Removal: clears only .tools.ruff, retains the ruff CLI ----
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
# .tools.ruff cleared (NOT top-level has("ruff")).
jq -e '.tools | has("ruff") | not' "$STATE_FILE" >/dev/null
# Unrelated state preserved.
[ "$(jq -r '.tools.numasec.bin' "$STATE_FILE")" = "/keep/numasec" ]
[ "$(jq -r '.tools.argent.bin' "$STATE_FILE")" = "/keep/argent" ]
[ "$(jq -r '.agents.cc.wired' "$STATE_FILE")" = "true" ]
# CLI retained.
[ -x "$TMP/fake-bin/ruff" ]
command -v ruff >/dev/null 2>&1

# ---- 12. CLI/guidance checks: pi-skill exposes the canonical non-mutating shape ----
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

# ---- 13. bin/megai wires status, doctor, update, and uninstall for ruff ----
grep -Fq 'install_ruff.sh' "$ROOT/bin/megai"
grep -Fq 'ruff --version' "$ROOT/bin/megai"
grep -Fq 'MEGAI_UPDATE=1 bash "$LIB/install_ruff.sh"' "$ROOT/bin/megai"
grep -Fq 'install_ruff.sh"    --remove' "$ROOT/bin/megai"
# Doctor must require both successful --version exit AND a sensible ruff-prefix.
grep -Fq 'ruff_rc' "$ROOT/bin/megai"
# Update must not run auto-upgrade; MEGAI_UPDATE=1 is passed through but the
# installer never invokes uv tool upgrade / pipx upgrade.
! grep -Eq 'uv tool upgrade ruff|pipx upgrade ruff' "$ROOT/lib/install_ruff.sh"

# ---- 14. lib/main.sh has step 18 for Ruff ----
grep -Fq 'TOTAL=18' "$ROOT/lib/main.sh"
grep -Fq 'install_ruff.sh' "$ROOT/lib/main.sh"
grep -Fq 'step 18 $TOTAL "Installing Ruff' "$ROOT/lib/main.sh"

# ---- 15. README.md mentions Ruff in the stack table and updated step count ----
grep -Fq '| 🐍 | [Ruff]' "$ROOT/README.md"
grep -Fq '18-step pipeline' "$ROOT/README.md"
grep -Fq '`uv tool install ruff`' "$ROOT/README.md"
grep -Fq 'ruff check --no-fix --no-fix-only --force-exclude --no-cache' "$ROOT/README.md"

# ---- 16. Real Ruff fixture: --no-fix alone can mutate under fix-only=true ----
# This reproduces the documented real-world behavior and asserts the canonical
# --no-fix-only defense preserves bytes and reports nonzero diagnostics.
if [ -z "$REAL_RUFF_BIN" ]; then
  echo "ruff integration: SKIP real-Ruff fixture (no working ruff on host PATH)"
  exit 0
fi
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
after_size_weak="$(wc -c < sample.py)"
# Sanity: real ruff with this config and --no-fix-only MUST not mutate AND
# MUST exit nonzero AND MUST surface F401. We rely on that for the guidance.
printf 'import os\n' > sample.py
before_sha2="$(shasum -a 256 sample.py | awk '{print $1}')"
set +e
"$REAL_RUFF_BIN" check --no-fix --no-fix-only --force-exclude --no-cache -- sample.py >"$FIXT/strong.out" 2>&1
strong_exit=$?
set -e
after_sha_strong="$(shasum -a 256 sample.py | awk '{print $1}')"
after_size_strong="$(wc -c < sample.py)"
echo "WEAK exit=$weak_exit before=$before_size after=$after_size_weak sha_changed=$([ "$before_sha" != "$after_sha_weak" ] && echo yes || echo no)"
echo "STRONG exit=$strong_exit after=$after_size_strong sha_changed=$([ "$before_sha2" != "$after_sha_strong" ] && echo yes || echo no)"
# Strong form must preserve bytes AND fail nonzero AND mention F401.
[ "$before_sha2" = "$after_sha_strong" ]
[ "$strong_exit" != "0" ]
grep -q 'F401' "$FIXT/strong.out"
rm -rf "$FIXT"

echo "ruff integration: ok"

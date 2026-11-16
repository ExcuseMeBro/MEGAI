#!/usr/bin/env bash
# Restore this Pi setup on a Mac (Apple silicon) with one command:
#
#   curl -fsSL https://raw.githubusercontent.com/ExcuseMeBro/MEGAI/pi/install.sh | bash
#
# Installs, per user and without sudo:
# - Pi, Pi-Bolt and the npm-installed Pi packages;
# - the MCP servers (brokan, agentmemory, figma-console);
# - Unharnessed's ipython kernel and megai-task-resources;
# - this snapshot's config into ~/.pi/agent, and the Codex CLI config into ~/.codex.
# Logins are left to you; the list is printed at the end.
#
# Safe to run again: existing config files are backed up first. Credentials, sessions and
# trust decisions in ~/.pi/agent are never touched. Skip steps with PI_RESTORE_SKIP, a
# comma list of: pi,pibolt,config,codex,packages,mcp,brokan,kernel,megai.
set -euo pipefail

REPO_URL="${PI_RESTORE_REPO:-https://github.com/ExcuseMeBro/MEGAI.git}"
BRANCH="${PI_RESTORE_BRANCH:-pi}"

# Run from a checkout of the branch; when piped from curl, fetch one first.
HERE=""
src="${BASH_SOURCE[0]:-}"
if [ -n "$src" ] && [ -f "$src" ]; then HERE=$(cd "$(dirname "$src")" && pwd); fi
if [ -z "$HERE" ] || [ ! -f "$HERE/versions.env" ] || [ ! -d "$HERE/agent" ]; then
	command -v git >/dev/null || { echo "git is missing: run 'xcode-select --install', then run this again" >&2; exit 1; }
	tmp=$(mktemp -d)
	git clone -q --depth 1 -b "$BRANCH" "$REPO_URL" "$tmp/src"
	exec bash "$tmp/src/install.sh" "$@"
fi

# shellcheck source=/dev/null
. "$HERE/versions.env"
A="$HOME/.pi/agent"
BIN="$HOME/.local/bin"
SHARE="$HOME/.local/share"
LOG="$HOME/.pi/restore-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$BIN" "$SHARE" "$A" "$(dirname "$LOG")"
export PATH="$BIN:$HOME/.cargo/bin:$PATH"

skip() { case ",${PI_RESTORE_SKIP:-}," in *",$1,"*) return 0 ;; esac; return 1; }
step() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
note() { printf '    %s\n' "$*"; }
warn() { printf '    \033[33m! %s\033[0m\n' "$*"; WARNINGS+=("$*"); }
die() { printf '\033[31mfailed: %s\033[0m (log: %s)\n' "$*" "$LOG" >&2; exit 1; }
WARNINGS=()
quiet() { "$@" >>"$LOG" 2>&1 || die "$* (see log)"; }
# fetch URL FILE: download an installer script before running it with stdin closed.
fetch() { curl --proto '=https' --tlsv1.2 -fsSL "$1" -o "$2" || die "download $1"; }
DL=$(mktemp -d)

[ "$(uname -s)" = Darwin ] || die "this snapshot is for macOS"
[ "$(uname -m)" = arm64 ] || warn "snapshot was made on Apple silicon; $(uname -m) is untested"
xcode-select -p >/dev/null 2>&1 || die "Xcode Command Line Tools are missing: run 'xcode-select --install', then run this again"
note "log: $LOG"

# ---------------------------------------------------------------- Node
# Pi's installer only installs Node when it can prompt in a terminal, so provide it here: the
# latest Node 22 from nodejs.org (checksum verified), where Pi's installer would put it.
node_ok() { command -v node >/dev/null && node -e 'const [a,b]=process.versions.node.split(".").map(Number);process.exit(a>22||(a===22&&b>=19)?0:1)' 2>/dev/null; }
BREW_BIN=/opt/homebrew/bin; [ -z "${PI_RESTORE_IGNORE_BREW:-}" ] || BREW_BIN=/nonexistent
for c in "$BREW_BIN" "$SHARE"/pi-node/*/bin; do [ -x "$c/node" ] && export PATH="$c:$PATH"; done
if ! node_ok; then
	step "Node.js 22 (nodejs.org)"
	base=https://nodejs.org/dist/latest-v22.x
	fetch "$base/SHASUMS256.txt" "$DL/SHASUMS256.txt"
	tarball=$(awk '/node-v22\.[0-9.]+-darwin-arm64\.tar\.gz$/ {print $2}' "$DL/SHASUMS256.txt")
	[ -n "$tarball" ] || die "no darwin-arm64 Node 22 build listed at $base"
	fetch "$base/$tarball" "$DL/$tarball"
	(cd "$DL" && grep " $tarball\$" SHASUMS256.txt | shasum -a 256 -c - >>"$LOG" 2>&1) || die "Node checksum mismatch"
	mkdir -p "$SHARE/pi-node"
	tar -xzf "$DL/$tarball" -C "$SHARE/pi-node"
	export PATH="$SHARE/pi-node/${tarball%.tar.gz}/bin:$PATH"
	node_ok || die "Node install"
	note "node $(node --version)"
fi

# ---------------------------------------------------------------- Pi and Pi-Bolt
if ! skip pi; then
	step "Pi (snapshot: $PI_VERSION)"
	if [ -x "$BIN/pi" ]; then
		note "already installed: $("$BIN/pi" --version 2>/dev/null | head -1)"
	else
		# Stdout is not a terminal here, so the installer does not offer to start pi.
		fetch https://pi.dev/install.sh "$DL/pi.sh"
		sh "$DL/pi.sh" >>"$LOG" 2>&1 </dev/null || die "Pi installer"
	fi
	v=$("$BIN/pi" --version 2>/dev/null | head -1 || true)
	[ "$v" = "$PI_VERSION" ] && note "pi $v" || warn "pi is $v, snapshot was made with $PI_VERSION (pi.dev installs the latest)"
fi

if ! skip pibolt; then
	step "Pi-Bolt ($PIBOLT_VERSION)"
	if [ -x "$BIN/pi-bolt" ] && "$BIN/pi-bolt" --version 2>/dev/null | grep -q "Pi-Bolt ${PIBOLT_VERSION#bolt-v},"; then
		note "already installed: $("$BIN/pi-bolt" --version)"
	else
		fetch https://pi-bolt.opensec.in/install.sh "$DL/pi-bolt.sh"
		PIBOLT_VERSION="$PIBOLT_VERSION" PIBOLT_YES=1 PIBOLT_EXTENSIONS=no sh "$DL/pi-bolt.sh" >>"$LOG" 2>&1 </dev/null ||
			die "Pi-Bolt installer"
		note "$("$BIN/pi-bolt" --version)"
	fi
fi

# Node for npm installs and the MCP servers: Pi's own, else whatever is on PATH.
NODE=""
for c in "$BREW_BIN/node" "$SHARE"/pi-node/*/bin/node "$(command -v node 2>/dev/null || true)"; do
	[ -n "$c" ] && [ -x "$c" ] && { NODE="$c"; break; }
done
[ -n "$NODE" ] || die "no node found (the Pi installer normally provides one)"
NPM="$(dirname "$NODE")/npm"
[ -x "$NPM" ] || NPM=$(command -v npm) || die "npm not found next to $NODE"
export PATH="$(dirname "$NODE"):$PATH"

# ---------------------------------------------------------------- config
if ! skip config; then
	step "Config into $A"
	backup="$A/backups/pre-restore-$(date +%Y%m%d-%H%M%S)"
	for f in settings.json mcp.json models.json AGENTS.md APPEND_SYSTEM.md defaults extensions prompts skills npm/package.json npm/package-lock.json; do
		if [ -e "$A/$f" ]; then
			mkdir -p "$backup/$(dirname "$f")"
			cp -R "$A/$f" "$backup/$f"
		fi
	done
	[ -d "$backup" ] && note "previous config backed up to $backup"
	# Replace the snapshot's directories as a whole so removed extensions/skills do not linger.
	for d in defaults extensions prompts skills; do rm -rf "${A:?}/$d"; done
	(cd "$HERE/agent" && tar cf - --exclude uh-kernel .) | (cd "$A" && tar xf -)
	mkdir -p "$A/uh-kernel" && cp "$HERE/agent/uh-kernel/SOURCE" "$A/uh-kernel/SOURCE"
	python3 -I - "$A/mcp.json" "$HOME" "$NODE" <<'PY'
import sys, pathlib
p, home, node = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
p.write_text(p.read_text().replace("__HOME__", home).replace("__NODE__", node))
PY
	chmod 600 "$A/mcp.json"
	if [ -d "$HERE/extras/config" ]; then
		(cd "$HERE/extras/config" && find . -type f) | while read -r f; do
			f=${f#./}
			[ -e "$HOME/.config/$f" ] && { mkdir -p "$backup/.config/$(dirname "$f")"; cp "$HOME/.config/$f" "$backup/.config/$f"; }
			mkdir -p "$HOME/.config/$(dirname "$f")"
			cp "$HERE/extras/config/$f" "$HOME/.config/$f"
			note "~/.config/$f"
		done
	fi
	note "$(find "$HERE/agent" -type f | wc -l | tr -d ' ') files restored"
fi

# ---------------------------------------------------------------- Codex CLI config
# config.toml (model, xhigh reasoning, no approvals, full-access sandbox), the global
# AGENTS.md and the keep-going Stop hook. auth.json, sessions and state are never touched.
if ! skip codex && [ -f "$HERE/codex/config.toml" ]; then
	CX="${CODEX_HOME:-$HOME/.codex}"
	step "Codex CLI config into $CX"
	mkdir -p "$CX/hooks"
	cbackup="$CX/backups/pre-restore-$(date +%Y%m%d-%H%M%S)"
	for f in config.toml AGENTS.md hooks.json hooks; do
		if [ -e "$CX/$f" ]; then mkdir -p "$cbackup"; cp -R "$CX/$f" "$cbackup/$f"; fi
	done
	[ -d "$cbackup" ] && note "previous Codex config backed up to $cbackup"
	cp "$HERE/codex/AGENTS.md" "$CX/AGENTS.md"
	[ -f "$HERE/codex/hooks.json" ] && cp "$HERE/codex/hooks.json" "$CX/hooks.json"
	cp "$HERE"/codex/hooks/*.mjs "$CX/hooks/" 2>/dev/null || true
	missing=$(python3 -I - "$HERE/codex/config.toml" "$CX/config.toml" "$HOME" "$NODE" <<'PY'
import os, re, sys, pathlib
src, dst, home, node = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3], sys.argv[4]
t = src.read_text().replace("__HOME__", home).replace("__NODE__", node)
missing = []
def fill(m):
    v = os.environ.get(m.group(1))
    if v is None:
        missing.append(m.group(1))
        return m.group(0)
    return v.replace("\\", "\\\\").replace('"', '\\"')
t = re.sub(r"\$\{([A-Z0-9_]+)\}", fill, t)
dst.write_text(t)
os.chmod(dst, 0o600)
print(" ".join(sorted(set(missing))))
PY
) || die "Codex config"
	[ -z "$missing" ] || warn "Codex config.toml still has placeholders for: $missing (export them and run with PI_RESTORE_SKIP=pi,pibolt,config,packages,mcp,brokan,kernel,megai, or edit $CX/config.toml)"
	command -v codex >/dev/null || warn "codex CLI is not installed; config is in place for when it is"
	note "config.toml, AGENTS.md, hooks restored"
fi

# ---------------------------------------------------------------- packages
if ! skip packages; then
	step "Pi packages (exact versions from package-lock.json)"
	# The same peer handling Pi uses for its managed npm installs (package-manager.ts).
	(cd "$A/npm" && quiet "$NPM" ci --omit=dev --legacy-peer-deps --no-audit --no-fund)
	note "$(cd "$A/npm" && "$NODE" -e 'const d=require("./package.json").dependencies;console.log(Object.keys(d).join(", "))')"
fi

if ! skip mcp; then
	step "MCP servers: agentmemory, figma-console"
	for d in agentmemory-package figma-console-mcp; do
		[ -d "$HERE/extras/$d" ] || continue
		mkdir -p "$SHARE/$d"
		cp "$HERE/extras/$d/package.json" "$HERE/extras/$d/package-lock.json" "$SHARE/$d/"
		(cd "$SHARE/$d" && quiet "$NPM" ci --no-audit --no-fund)
		note "$d ok"
	done
fi

if ! skip brokan; then
	step "brokan (${BROKAN_REV:0:12})"
	if [ -x "$BIN/brokan" ]; then
		note "already installed: $("$BIN/brokan" --version)"
	else
		if ! command -v cargo >/dev/null; then
			note "installing Rust (rustup, per user)"
			fetch https://sh.rustup.rs "$DL/rustup.sh"
			sh "$DL/rustup.sh" -y --no-modify-path --profile minimal >>"$LOG" 2>&1 </dev/null || die "rustup"
			export PATH="$HOME/.cargo/bin:$PATH"
		fi
		note "building from source (a few minutes)"
		quiet cargo install --locked --git "$BROKAN_REPO" --rev "$BROKAN_REV" --root "$HOME/.local" brokan
		note "$("$BIN/brokan" --version)"
	fi
fi

# ---------------------------------------------------------------- ipython kernel
if ! skip kernel; then
	step "ipython kernel (Python $PYTHON_VERSION + unharnessed-runtime ${UNHARNESSED_REV:0:7})"
	if ! command -v uv >/dev/null; then
		fetch https://astral.sh/uv/install.sh "$DL/uv.sh"
		env UV_INSTALL_DIR="$BIN" UV_NO_MODIFY_PATH=1 sh "$DL/uv.sh" >>"$LOG" 2>&1 </dev/null || die "uv installer"
	fi
	quiet uv python install "$PYTHON_VERSION"
	rm -rf "$A/uh-kernel/venv"
	quiet uv venv --seed --python "$PYTHON_VERSION" "$A/uh-kernel/venv"
	quiet uv pip install --python "$A/uh-kernel/venv/bin/python" -r "$HERE/agent/uh-kernel/requirements.txt" \
		"unharnessed-runtime @ git+$UNHARNESSED_REPO@$UNHARNESSED_REV#subdirectory=unharnessed-runtime"
	"$A/uh-kernel/venv/bin/python" -c 'import rlm.repl, rlm.bash, pandas' >>"$LOG" 2>&1 || die "kernel import check"
	"$A/uh-kernel/venv/bin/python" -m pip freeze >"$A/uh-kernel/freeze.txt" 2>>"$LOG" || true
	note "kernel ok"
fi

# ---------------------------------------------------------------- megai-task-resources
if ! skip megai; then
	step "megai-task-resources (from MEGAI dev)"
	tmp=$(mktemp -d)
	if git clone -q --depth 1 -b dev "$REPO_URL" "$tmp/megai" >>"$LOG" 2>&1; then
		quiet python3 "$tmp/megai/scripts/install_task_resources.py" "$HOME" "$tmp/megai"
		note "installed $BIN/megai-task-resources"
	else
		warn "could not clone MEGAI dev; install megai-task-resources later with scripts/install_task_resources.py"
	fi
	rm -rf "$tmp"
fi

# ---------------------------------------------------------------- check
step "Check"
if [ -x "$BIN/pi-bolt" ]; then
	"$BIN/pi-bolt" list >>"$LOG" 2>&1 && note "pi-bolt loads the restored settings" || warn "pi-bolt list failed (see log)"
fi
if ! grep -qs '.local/bin' "$HOME/.zshrc" "$HOME/.zprofile"; then
	printf '\n# Pi, Pi-Bolt, brokan, uv (added by the Pi config restore)\nexport PATH="$HOME/.local/bin:$PATH"\n' >>"$HOME/.zprofile"
	note "added ~/.local/bin to PATH in ~/.zprofile (open a new terminal)"
fi

cat <<EOF

Done. What is left is logging in:
  1. pi-bolt, then /login: choose OpenAI and sign in with ChatGPT.
  2. Antigravity accounts (pi-antigravity): sign in again from inside Pi.
  3. Figma MCP: put your token in the environment, e.g.
       echo 'export FIGMA_ACCESS_TOKEN=figd_...' >> ~/.zshrc
  4. MCP servers that use OAuth: /mcp inside Pi.
  5. brokan: run 'brokan service install' to keep the board running; set up board Sync
     in its Settings to bring your board over.
  6. agentmemory starts its own engine on first use. Memories are not copied; they live in
     ~/.agentmemory on the old Mac.
  7. Codex CLI: 'codex login' (ChatGPT). Its config runs with no approvals and no sandbox.
EOF
if [ ${#WARNINGS[@]} -gt 0 ]; then
	printf '\nWarnings:\n'
	printf '  - %s\n' "${WARNINGS[@]}"
fi

#!/usr/bin/env bash
# Ix — persistent codebase map and system-memory CLI.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
IX_INSTALL_URL="${IX_INSTALL_URL:-https://ix-infra.com/install.sh}"
IX_CODEX_INSTALL_URL="${IX_CODEX_INSTALL_URL:-https://ix-infra.com/codex-install.sh}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

run_installer() {
  local url="$1" tmp
  shift
  tmp="$(mktemp)"
  if ! curl -fsSL "$url" -o "$tmp"; then
    rm -f "$tmp"
    return 1
  fi
  if ! IX_HOME="${IX_HOME:-$HOME/.ix}" IX_SKIP_BACKEND="${IX_SKIP_BACKEND:-0}" sh "$tmp" "$@"; then
    rm -f "$tmp"
    return 1
  fi
  rm -f "$tmp"
}

merge_codex_hooks() {
  local source_dir="${IX_HOME:-$HOME/.ix}/codex-plugin-source"
  [ -f "$source_dir/.codex/hooks.json" ] || return 1
  [ -d "$source_dir/.codex/hooks" ] || return 1
  [ -f "$source_dir/scripts/install_codex_integration.py" ] || return 1

  python3 - "$source_dir" "$HOME/.codex" <<'PY'
import importlib.util
import json
from pathlib import Path
import shutil
import sys

source_root = Path(sys.argv[1])
codex_dir = Path(sys.argv[2])
installer_path = source_root / "scripts" / "install_codex_integration.py"
spec = importlib.util.spec_from_file_location("ix_codex_installer", installer_path)
if spec is None or spec.loader is None:
    raise SystemExit("could not load Ix Codex installer")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

codex_dir.mkdir(parents=True, exist_ok=True)
installer.ensure_codex_hooks_enabled(codex_dir / "config.toml")

source_hooks = json.loads((source_root / ".codex" / "hooks.json").read_text())
hooks_path = codex_dir / "hooks.json"
if hooks_path.exists():
    installed_hooks = json.loads(hooks_path.read_text())
else:
    installed_hooks = {"hooks": {}}
installed_hooks.setdefault("hooks", {})
for event, blocks in source_hooks.get("hooks", {}).items():
    target = installed_hooks["hooks"].setdefault(event, [])
    for block in blocks:
        if block not in target:
            target.append(block)
hooks_path.write_text(json.dumps(installed_hooks, indent=2) + "\n")

hooks_dir = codex_dir / "hooks"
hooks_dir.mkdir(parents=True, exist_ok=True)
for source in (source_root / ".codex" / "hooks").glob("*.py"):
    shutil.copy2(source, hooks_dir / source.name)
PY
}

if ! run_installer "$IX_INSTALL_URL"; then
  existing_ix="$(command -v ix || true)"
  for candidate in "$HOME/.local/bin/ix" /opt/homebrew/bin/ix /usr/local/bin/ix; do
    [ -x "$candidate" ] && existing_ix="$candidate" && break
  done
  if [ -z "$existing_ix" ]; then
    warn "Ix install failed and no existing CLI was found — skipping"
    exit 0
  fi
  warn "Ix bootstrap failed; continuing with existing CLI -> $existing_ix"
fi

ix_bin="$(command -v ix || true)"
for candidate in "$HOME/.local/bin/ix" /opt/homebrew/bin/ix /usr/local/bin/ix; do
  [ -x "$candidate" ] && ix_bin="$candidate" && break
done
if [ -z "$ix_bin" ]; then
  warn "Ix installer finished but ix was not found"
  exit 0
fi
ln -sf "$ix_bin" "$MEGAI_HOME/bin/ix"
export PATH="$MEGAI_HOME/bin:$PATH"
ok "Ix installed -> $ix_bin"

claude_plugin=false
codex_hooks=false
codex_plugin=false
codex_mcp=false
if command -v claude >/dev/null 2>&1; then
  claude plugin marketplace add ix-infrastructure/ix-claude-plugin --scope user >/dev/null 2>&1 || true
  if claude plugin list 2>/dev/null | grep -q 'ix-memory'; then
    claude plugin update ix-memory@ix-claude-plugin >/dev/null 2>&1 || true
  else
    claude plugin install ix-memory@ix-claude-plugin --scope user >/dev/null 2>&1 || true
  fi
  if claude plugin list 2>/dev/null | grep -q 'ix-memory'; then
    claude_plugin=true
    ok "Ix Claude plugin ready"
  else
    warn "Ix Claude plugin not enabled — run: claude plugin install ix-memory@ix-claude-plugin"
  fi
fi

if command -v codex >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
  if run_installer "$IX_CODEX_INSTALL_URL" >/dev/null 2>&1; then
    codex_hooks=true
  elif run_installer "$IX_CODEX_INSTALL_URL" --home --plugin --mcp --force >/dev/null 2>&1 \
    && merge_codex_hooks; then
    codex_hooks=true
    ok "Ix Codex hooks merged with existing hooks"
  else
    warn "Ix Codex hooks/MCP install failed"
  fi
  codex plugin add ix-memory@ix-codex-plugin --json >/dev/null 2>&1 || true
  if codex plugin list --json 2>/dev/null | jq -e '
    .installed[]? | select(.pluginId == "ix-memory@ix-codex-plugin" and .installed == true and .enabled == true)
  ' >/dev/null; then
    codex_plugin=true
    ok "Ix Codex plugin ready"
  else
    warn "Ix Codex plugin not enabled — run: codex plugin add ix-memory@ix-codex-plugin"
  fi

  ix_mcp="$HOME/.codex/mcp/server.py"
  if [ -f "$ix_mcp" ]; then
    if codex mcp get ix-memory --json 2>/dev/null | jq -e \
      --arg script "$ix_mcp" \
      '.transport.type == "stdio" and .transport.command == "python3" and .transport.args == [$script]' \
      >/dev/null; then
      codex_mcp=true
    else
      codex mcp remove ix-memory >/dev/null 2>&1 || true
      codex mcp add ix-memory -- python3 "$ix_mcp" >/dev/null 2>&1 || true
      codex mcp get ix-memory --json 2>/dev/null | jq -e \
        --arg script "$ix_mcp" \
        '.transport.type == "stdio" and .transport.command == "python3" and .transport.args == [$script]' \
        >/dev/null && codex_mcp=true
    fi
    [ "$codex_mcp" = "true" ] && ok "Ix Codex MCP ready" || warn "Ix Codex MCP registration failed"
  fi
fi

ver="$(ix --version 2>/dev/null | head -n1 || echo "")"
state_set '.tools["ix"]' "{\"bin\":\"$MEGAI_HOME/bin/ix\",\"version\":\"$ver\",\"claudePlugin\":$claude_plugin,\"codexPlugin\":$codex_plugin,\"codexHooks\":$codex_hooks,\"codexMcp\":$codex_mcp}"

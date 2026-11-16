#!/usr/bin/env bash
# Regenerate this snapshot from the live Pi setup on the source Mac:
#   ./export.sh            then commit and push (the branch keeps a single commit).
#
# Copies configuration only: no credentials, sessions, caches or installs. Secret-looking MCP
# env values become ${VAR} placeholders, home paths become __HOME__, and the run fails if any
# credential value from the live auth files appears in the result.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
A="${PI_AGENT_DIR:-$HOME/.pi/agent}"
cd "$HERE"

rm -rf agent extras codex
mkdir -p agent/npm agent/uh-kernel extras

(cd "$A" && rsync -a --exclude node_modules --exclude .DS_Store --exclude __pycache__ \
	AGENTS.md APPEND_SYSTEM.md models.json defaults extensions prompts skills "$HERE/agent/")
cp "$A/npm/package.json" "$A/npm/package-lock.json" agent/npm/

for d in agentmemory-package figma-console-mcp; do
	if [ -f "$HOME/.local/share/$d/package.json" ]; then
		mkdir -p "extras/$d"
		cp "$HOME/.local/share/$d/package.json" "$HOME/.local/share/$d/package-lock.json" "extras/$d/"
	fi
done

# Package config homes outside ~/.pi/agent that change Pi's behaviour.
# billion-context.json: subagents (acp_delegate tools) off, no auto-update.
for f in billion-context/billion-context.json; do
	if [ -f "$HOME/.config/$f" ]; then
		mkdir -p "extras/config/$(dirname "$f")"
		cp "$HOME/.config/$f" "extras/config/$f"
	fi
done

KPY="$A/uh-kernel/venv/bin/python"
"$KPY" -m pip freeze --exclude-editable | grep -v -i '^unharnessed-runtime' >agent/uh-kernel/requirements.txt
cp "$A/uh-kernel/SOURCE" agent/uh-kernel/SOURCE

python3 -I - "$A" "$HERE" "$HOME" <<'PY'
import json, sys, re, pathlib
src, out, home = map(pathlib.Path, sys.argv[1:4])
s = json.loads((src / "settings.json").read_text())
s.pop("deviceId", None)  # per-device ChatGPT login id
(out / "agent/settings.json").write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n")
m = json.loads((src / "mcp.json").read_text())
for srv in m.get("mcpServers", {}).values():
    for k in list(srv.get("env") or {}):
        if re.search(r"TOKEN|KEY|SECRET|PASSWORD", k, re.I):
            srv["env"][k] = "${" + k + "}"
    if srv.get("command", "").endswith("/node"):
        srv["command"] = "__NODE__"  # install.sh picks the node it installed or found
    for k in ("headers",):
        for h in list(srv.get(k) or {}):
            if not str(srv[k][h]).startswith("${"):
                srv[k][h] = "${MCP_" + re.sub(r"\W", "_", h).upper() + "}"
text = json.dumps(m, indent=2, ensure_ascii=False) + "\n"
(out / "agent/mcp.json").write_text(text.replace(str(home), "__HOME__"))
PY

# Codex CLI config: config.toml, global AGENTS.md and the keep-going Stop hook. Never auth,
# sessions, sqlite state or backups. Secret-looking values become ${VAR} placeholders that
# install.sh fills from the environment.
C="${CODEX_HOME:-$HOME/.codex}"
if [ -f "$C/config.toml" ]; then
	mkdir -p codex/hooks
	cp "$C/AGENTS.md" codex/AGENTS.md
	[ -f "$C/hooks.json" ] && cp "$C/hooks.json" codex/hooks.json
	[ -d "$C/hooks" ] && cp "$C"/hooks/*.mjs codex/hooks/
	python3 -I - "$C/config.toml" "$HERE/codex/config.toml" "$HOME" <<'PY'
import re, sys, pathlib
src, out, home = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
lines = []
for line in src.read_text().splitlines():
    m = re.match(r'^(\s*)([A-Za-z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD)[A-Za-z0-9_]*)\s*=\s*"(.*)"\s*$', line, re.I)
    if m and not m.group(3).startswith("${"):
        line = '%s%s = "${%s}"' % (m.group(1), m.group(2), m.group(2).upper())
    line = re.sub(r'"[^"]*/bin/node"', '"__NODE__"', line) if re.match(r'^\s*command\s*=', line) else line
    lines.append(line.replace(home, "__HOME__"))
out.write_text("\n".join(lines) + "\n")
PY
fi

# Versions the installer reproduces.
pibolt=$(sed -n 's/^Pi-Bolt \([0-9.]*\) .*/\1/p' "$HOME/.pi-bolt/pi-bolt-darwin-arm64/pi-bolt.txt")
pi_version=$(cat "$A/install/current-version")
uh_rev=$(awk '{print $2}' "$A/uh-kernel/SOURCE")
brokan_rev=$(sed -n 's/^BROKAN_REV=//p' versions.env 2>/dev/null || true)
if [ -d "$HOME/PROJECTS/brokan/.git" ] && command -v brokan >/dev/null; then
	r=$(git -C "$HOME/PROJECTS/brokan" rev-parse HEAD)
	git -C "$HOME/PROJECTS/brokan" branch -r --contains "$r" | grep -q . && brokan_rev=$r
fi
cat >versions.env <<EOF
PI_VERSION=$pi_version
PIBOLT_VERSION=bolt-v$pibolt
PYTHON_VERSION=$("$KPY" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
UNHARNESSED_REPO=https://github.com/unharnessed-agent/Unharnessed
UNHARNESSED_REV=$uh_rev
BROKAN_REPO=https://github.com/ExcuseMeBro/brokan
BROKAN_REV=$brokan_rev
EOF

# Leak check: no credential value from the live machine may appear in the snapshot.
python3 -I - "$A" "$HERE" <<'PY'
import json, sys, pathlib
a, out = map(pathlib.Path, sys.argv[1:3])
secrets = set()
def walk(o, key=""):
    if isinstance(o, dict):
        for k, v in o.items(): walk(v, k)
    elif isinstance(o, list):
        for v in o: walk(v, key)
    elif isinstance(o, str) and len(o) >= 16 and not o.startswith(("http", "/", "${")) and " " not in o:
        secrets.add(o)
for name in ("auth.json", "mcp-auth.json", "antigravity-accounts.json"):
    p = a / name
    if p.exists():
        walk(json.loads(p.read_text()))
import os, re
codex = pathlib.Path(os.environ.get("CODEX_HOME") or pathlib.Path.home() / ".codex")
if (codex / "auth.json").exists():
    walk(json.loads((codex / "auth.json").read_text()))
if (codex / "config.toml").exists():
    for v in re.findall(r'^\s*[A-Za-z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD)[A-Za-z0-9_]*\s*=\s*"([^"]{12,})"', (codex / "config.toml").read_text(), re.M | re.I):
        if not v.startswith("${"): secrets.add(v)
m = json.loads((a / "mcp.json").read_text())
for srv in m.get("mcpServers", {}).values():
    for v in list((srv.get("env") or {}).values()) + list((srv.get("headers") or {}).values()):
        if isinstance(v, str) and len(v) >= 12 and not v.startswith("${"): secrets.add(v)
s = json.loads((a / "settings.json").read_text())
if s.get("deviceId"): secrets.add(s["deviceId"])
bad = []
for f in out.rglob("*"):
    if f.is_file() and ".git" not in f.parts:
        data = f.read_bytes()
        for sec in secrets:
            if sec.encode() in data:
                bad.append(str(f.relative_to(out)))
                break
if bad:
    sys.exit("refusing: live credential values found in " + ", ".join(sorted(set(bad))))
print(f"leak check ok ({len(secrets)} live credential values checked)")
PY
echo "snapshot: $(find agent extras codex -type f 2>/dev/null | wc -l | tr -d ' ') files, $(du -sh agent | cut -f1)"

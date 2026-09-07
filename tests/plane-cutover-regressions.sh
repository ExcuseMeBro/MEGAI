#!/usr/bin/env bash
# Final cutover regressions; isolated HOME, no credentials or network requests.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export PYTHONDONTWRITEBYTECODE=1
python3 - "$ROOT" "$TMP" <<'PY'
import contextlib
import io
import json
import os
import shutil
import sys
from pathlib import Path
root, tmp = (Path(value).resolve() for value in sys.argv[1:])
sys.path.insert(0, str(root/'lib'))
from plane_mcp_remote import regular, runtime_digest, sha256, bridge_manifest
from install_taskflow_policy import install

# The real deployment uses a root-owned system Node, not a fixture shell.
node = Path(shutil.which('node')).resolve()
regular(node, system=True)
assert node.stat().st_uid in (0, os.getuid())
unsafe = tmp/'unsafe-node'
unsafe.write_bytes(node.read_bytes()[:128])
unsafe.chmod(0o777)
with contextlib.redirect_stderr(io.StringIO()):
    try:
        regular(unsafe, system=True)
    except SystemExit:
        pass
    else:
        raise AssertionError('group/world-writable Node accepted')

home = tmp/'megai'
modules = home/'plane-bridge/mcp-remote-0.1.43/node_modules'
dist = modules/'mcp-remote/dist'
dist.mkdir(parents=True)
entry = dist/'proxy.js'
chunk = dist/'chunk.js'
entry.write_text("import './chunk.js';\n")
chunk.write_text('export const value = 1;\n')
(modules/'.bin').mkdir()
(modules/'.bin/mcp-remote').symlink_to('../mcp-remote/dist/proxy.js')
lock = modules.parent/'package-lock.json'
lock.write_text('{}\n')
manifest = {'version':2, 'package':'mcp-remote', 'package_version':'0.1.43',
            'node':str(node), 'entry':str(entry), 'lockfile':str(lock),
            'node_sha256':sha256(node), 'entry_sha256':sha256(entry),
            'lock_sha256':sha256(lock), 'runtime_sha256':runtime_digest(modules)}
receipt = home/'plane-bridge.json'
receipt.write_text(json.dumps(manifest))
receipt.chmod(0o600)
os.environ['MEGAI_HOME'] = str(home)
assert bridge_manifest()['node'] == node

def rejected():
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            bridge_manifest()
        except SystemExit:
            return
    raise AssertionError('modified runtime accepted')

chunk.write_text('export const value = 2;\n')
rejected()
chunk.write_text('export const value = 1;\n')
added = modules/'injected.js'
added.write_text('injected')
rejected()
added.unlink()
chunk.unlink()
rejected()
chunk.write_text('export const value = 1;\n')
link = modules/'.bin/mcp-remote'
link.unlink()
link.symlink_to(node)
rejected()
link.unlink()
link.symlink_to('../mcp-remote/dist/proxy.js')
assert bridge_manifest()['entry'] == entry

# A repeated install must not add blank lines or additional backup records.
policy = tmp/'codex/AGENTS.md'
policy.parent.mkdir()
tail = '\n\n# User-owned instructions\nKeep this exactly.\n'
policy.write_text('<!-- asana-workflow:begin -->\nlegacy\n<!-- asana-workflow:end -->\n'+tail)
backup = tmp/'backups'
source = root/'task-flow/CODEX.snippet.md'
install(policy, source, 'codex', backup)
first = policy.read_bytes()
backup_files = sorted(backup.rglob('*'))
for _ in range(3):
    install(policy, source, 'codex', backup)
    assert policy.read_bytes() == first
    assert sorted(backup.rglob('*')) == backup_files
assert policy.read_text().endswith(tail)
print('PASS system Node, complete runtime integrity, and policy idempotence')
PY

# Uninstall must remove both connectors before asset removal and abort on error.
mkdir -p "$TMP/home" "$TMP/install/lib"
cp "$ROOT/lib/ui.sh" "$ROOT/lib/state.sh" "$ROOT/lib/detect.sh" "$ROOT/lib/banner.sh" "$TMP/install/lib/"
printf '{"tools":{}}\n' >"$TMP/install/state.json"
cat >"$TMP/install/lib/plane_mcp.sh" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$CALL_LOG"
exit 1
SH
if printf 'y\n' | HOME="$TMP/home" MEGAI_HOME="$TMP/install" CALL_LOG="$TMP/remove-call" bash "$ROOT/bin/megai" uninstall >"$TMP/uninstall.log" 2>&1; then
  echo 'FAIL uninstall ignored connector removal failure'; exit 1
fi
grep -Fxq 'remove --client all' "$TMP/remove-call"
[ -f "$TMP/install/lib/plane_mcp.sh" ]
echo 'PASS uninstall removes all clients and preserves assets on failure'

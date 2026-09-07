#!/usr/bin/env bash
# Install the pinned bridge as an explicit, credential-free preflight.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
. "$MEGAI_HOME/lib/ui.sh"
TARGET="$MEGAI_HOME/plane-bridge/mcp-remote-0.1.43"
MANIFEST="$MEGAI_HOME/plane-bridge.json"

usage() { echo 'Usage: megai plane bridge install'; }
install_bridge() {
  command -v npm >/dev/null 2>&1 || die 'Plane bridge install requires npm'
  command -v node >/dev/null 2>&1 || die 'Plane bridge install requires node'
  command -v python3 >/dev/null 2>&1 || die 'Plane bridge install requires python3'
  [ ! -L "$MEGAI_HOME" ] || die 'refusing symlinked MEGAI_HOME'
  [ ! -L "$MEGAI_HOME/plane-bridge" ] || die 'refusing symlinked Plane bridge directory'
  mkdir -p "$MEGAI_HOME/plane-bridge"
  chmod 700 "$MEGAI_HOME/plane-bridge"
  [ ! -L "$TARGET" ] || die 'refusing symlinked Plane bridge target'
  env -u MEGAI_PLANE_AUTH -u MEGAI_PLANE_WORKSPACE npm install --prefix "$TARGET" --ignore-scripts --no-audit --no-fund --omit=dev 'mcp-remote@0.1.43'
  local node_bin entry lock package_json tmp
  node_bin="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$(command -v node)")"
  entry="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$TARGET/node_modules/mcp-remote/dist/proxy.js")"
  lock="$TARGET/package-lock.json"
  package_json="$TARGET/node_modules/mcp-remote/package.json"
  [ -f "$entry" ] && [ -f "$lock" ] && [ -f "$package_json" ] || die 'installed bridge is missing its entrypoint, package metadata, or lockfile'
  python3 - "$package_json" <<'PY'
import json, sys
with open(sys.argv[1], encoding='utf-8') as stream:
    if json.load(stream).get('version') != '0.1.43': raise SystemExit(1)
PY
  tmp="$(mktemp "$MANIFEST.XXXXXX")"
  python3 - "$tmp" "$node_bin" "$entry" "$lock" <<'PY'
import hashlib, json, os, sys
out, node, entry, lock = sys.argv[1:]
def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()
value = {
    'version': 1, 'package': 'mcp-remote', 'package_version': '0.1.43',
    'node': node, 'entry': entry, 'lockfile': lock,
    'entry_sha256': digest(entry), 'lock_sha256': digest(lock),
}
with open(out, 'w', encoding='utf-8') as stream: json.dump(value, stream, sort_keys=True); stream.write('\n')
os.chmod(out, 0o600)
PY
  mv -f "$tmp" "$MANIFEST"
  chmod 600 "$MANIFEST"
  ok "Plane bridge installed and receipt recorded (mcp-remote@0.1.43)"
}
case "${1:-}" in install) [ "$#" -eq 1 ] || die 'usage: plane bridge install'; install_bridge;; *) usage >&2; exit 1;; esac

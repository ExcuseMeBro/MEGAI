#!/usr/bin/env python3
"""Launch the pre-installed, receipt-verified mcp-remote bridge."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plane_mcp_headers import read_token, validate_workspace  # noqa: E402

PLANE_MCP_URL = "https://mcp.plane.so/http/api-key/mcp"
BRIDGE_VERSION = "0.1.43"
AUTH_ENV = "MEGAI_PLANE_AUTH"
WORKSPACE_ENV = "MEGAI_PLANE_WORKSPACE"


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def regular(path: Path, private: bool = False, system: bool = False) -> None:
    if path.is_symlink() or not path.is_file():
        fail(f"invalid Plane bridge artifact: {path}")
    info = path.stat()
    if info.st_uid not in ({0, os.getuid()} if system else {os.getuid()}):
        fail(f"Plane bridge artifact has an untrusted owner: {path}")
    if info.st_mode & 0o022:
        fail(f"Plane bridge artifact is group/world writable: {path}")
    if system and not os.access(path, os.X_OK):
        fail(f"Plane bridge system executable is not executable: {path}")
    if private and stat.S_IMODE(info.st_mode) & 0o077:
        fail(f"Plane bridge receipt is not private: {path}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def runtime_digest(root: Path) -> str:
    """Cover all installed dependencies and imported chunks, not just proxy.js."""
    root = root.resolve(strict=True)
    records = []
    for directory, dirs, files in os.walk(root, followlinks=False):
        parent = Path(directory)
        info = parent.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o022:
            fail(f"Unsafe Plane runtime directory: {parent}")
        for name in sorted(dirs + files):
            path = parent / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                # npm creates .bin links. Cover the link and require its target
                # to be a regular file within the separately hashed tree.
                resolved = path.resolve(strict=True)
                if not resolved.is_relative_to(root) or not resolved.is_file():
                    fail(f"Unsafe Plane runtime link: {path}")
                records.append((relative, "link", os.readlink(path)))
            elif path.is_dir():
                records.append((relative, "dir", ""))
            else:
                regular(path)
                records.append((relative, "file", sha256(path)))
    return hashlib.sha256(json.dumps(sorted(records), separators=(",", ":")).encode()).hexdigest()


def bridge_manifest() -> dict:
    home = Path(os.environ.get("MEGAI_HOME", Path.home() / ".megai")).expanduser()
    if not home.is_absolute() or home.is_symlink():
        fail("MEGAI_HOME is not an absolute, non-symlink directory")
    home = home.resolve()
    manifest_path = home / "plane-bridge.json"
    regular(manifest_path, private=True)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("version") != 2 or manifest.get("package") != "mcp-remote" or manifest.get("package_version") != BRIDGE_VERSION:
            raise ValueError("wrong bridge version")
        node_raw = Path(manifest["node"])
        entry_raw = Path(manifest["entry"])
        lock_raw = Path(manifest["lockfile"])
        if not node_raw.is_absolute() or not entry_raw.is_absolute() or not lock_raw.is_absolute():
            raise ValueError("bridge receipt paths must be absolute")
        node = node_raw.resolve()
        entry = entry_raw.resolve()
        lock = lock_raw.resolve()
        bridge_parent = home / "plane-bridge"
        install_root = bridge_parent / "mcp-remote-0.1.43"
        if bridge_parent.is_symlink() or install_root.is_symlink():
            raise ValueError("bridge installation contains a symlinked root")
        expected_root = install_root.resolve()
        expected_entry = install_root / "node_modules/mcp-remote/dist/proxy.js"
        expected_lock = install_root / "package-lock.json"
        if expected_root != install_root or expected_entry.resolve() != expected_entry or expected_lock.resolve() != expected_lock:
            raise ValueError("bridge installation path is not local and regular")
        if entry != expected_entry or lock != expected_lock:
            raise ValueError("bridge receipt is not bound to the pinned installation")
        regular(node, system=True)
        regular(entry)
        regular(lock)
        if (manifest["lock_sha256"] != sha256(lock)
                or manifest["entry_sha256"] != sha256(entry)
                or manifest["node_sha256"] != sha256(node)
                or manifest["runtime_sha256"] != runtime_digest(install_root / "node_modules")):
            raise ValueError("bridge receipt hash mismatch")
    except (KeyError, TypeError, ValueError, OSError, UnicodeError) as exc:
        fail(f"invalid Plane bridge receipt: {exc}")
    return {"node": node, "entry": entry}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--token-file", required=True)
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    validate_workspace(args.workspace)
    bridge = bridge_manifest()
    token = read_token(args.token_file)
    if args.check:
        return 0
    env = os.environ.copy()
    env[AUTH_ENV] = f"Bearer {token}"
    env[WORKSPACE_ENV] = args.workspace
    command = [
        str(bridge["node"]),
        str(bridge["entry"]),
        PLANE_MCP_URL,
        "--header",
        f"Authorization:${{{AUTH_ENV}}}",
        "--header",
        f"x-workspace-slug:${{{WORKSPACE_ENV}}}",
        "--silent",
    ]
    os.execve(str(bridge["node"]), command, env)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

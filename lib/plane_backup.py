#!/usr/bin/env python3
"""Private, target-bound configuration backups for the Plane connector."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import stat
import sys
import tempfile
import time
from pathlib import Path


def die(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def regular_private(path: Path, *, private: bool = True) -> None:
    if path.is_symlink() or not path.is_file():
        die(f"refusing non-regular backup path: {path}")
    info = path.stat()
    if info.st_uid != os.getuid():
        die(f"backup is not owned by current user: {path}")
    if private and stat.S_IMODE(info.st_mode) & 0o077:
        die(f"backup is not private: {path}")


def key(target: Path) -> str:
    return hashlib.sha256(str(target.expanduser().resolve()).encode()).hexdigest()


def root_dir(root: Path, target: Path) -> Path:
    if root.is_symlink() or root.parent.is_symlink():
        die(f"refusing symlinked backup root: {root}")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root_info = root.stat()
    if root_info.st_uid != os.getuid() or stat.S_IMODE(root_info.st_mode) & 0o077:
        die(f"backup root is not private: {root}")
    os.chmod(root, 0o700)
    directory = root / key(target)
    if directory.is_symlink():
        die(f"refusing symlinked target backup directory: {directory}")
    directory.mkdir(mode=0o700, exist_ok=True)
    info = directory.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        die(f"target backup directory is not private: {directory}")
    os.chmod(directory, 0o700)
    return directory


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def payload_is_valid(path: Path, kind: str) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
        if kind == "pi":
            value = json.loads(text)
            return isinstance(value, dict)
        import tomllib
        tomllib.loads(text)
        return True
    except (OSError, UnicodeError, ValueError):
        return False


def validate_payload(path: Path, kind: str) -> None:
    if not payload_is_valid(path, kind):
        die(f"invalid {kind} configuration backup: {path}")


def exclusive_copy(source: Path, directory: Path, prefix: str) -> Path:
    fd, name = tempfile.mkstemp(prefix=prefix, dir=directory)
    temporary = Path(name)
    try:
        with source.open("rb") as src, os.fdopen(fd, "wb") as dst:
            fd = -1
            shutil.copyfileobj(src, dst)
        os.chmod(temporary, 0o600)
        return temporary
    except BaseException:
        os.close(fd)
        temporary.unlink(missing_ok=True)
        raise


def save(args: argparse.Namespace) -> None:
    source = Path(args.source).expanduser()
    target = Path(args.target).expanduser().resolve()
    regular_private(source, private=False)
    validate_payload(source, args.kind)
    directory = root_dir(Path(args.root).expanduser(), target)
    stamp = f"{time.time_ns()}-{secrets.token_hex(6)}"
    payload = directory / f"{args.kind}-plane-mcp.config.bak.{stamp}"
    temporary = exclusive_copy(source, directory, f".tmp-{stamp}-")
    os.replace(temporary, payload)
    metadata = {
        "version": 1,
        "target": str(target),
        "kind": args.kind,
        "payload": payload.name,
        "sha256": digest(payload),
        "created_ns": time.time_ns(),
    }
    meta = directory / f"metadata.{stamp}.json"
    meta_tmp = exclusive_copy_text(directory, f".meta-{stamp}-", json.dumps(metadata, sort_keys=True) + "\n")
    os.replace(meta_tmp, meta)
    print(payload)


def exclusive_copy_text(directory: Path, prefix: str, content: str) -> Path:
    fd, name = tempfile.mkstemp(prefix=prefix, dir=directory, text=True)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            fd = -1
            stream.write(content)
        os.chmod(temporary, 0o600)
        return temporary
    except BaseException:
        os.close(fd)
        temporary.unlink(missing_ok=True)
        raise


def restore(args: argparse.Namespace) -> None:
    target = Path(args.target).expanduser().resolve()
    destination = Path(args.destination).expanduser()
    if destination.is_symlink():
        die(f"refusing symlinked restore target: {destination}")
    directory = root_dir(Path(args.root).expanduser(), target)
    candidates = []
    for meta in directory.glob("metadata.*.json"):
        try:
            regular_private(meta)
            item = json.loads(meta.read_text(encoding="utf-8"))
            payload = directory / item["payload"]
            regular_private(payload)
            if item["target"] != str(target) or item["kind"] != args.kind:
                continue
            if item["sha256"] != digest(payload):
                continue
            if not payload_is_valid(payload, args.kind):
                continue
            candidates.append((int(item["created_ns"]), payload))
        except (KeyError, TypeError, ValueError):
            continue
    if not candidates:
        die(f"no valid private {args.kind} backup bound to {target}")
    _, source = max(candidates)
    if destination.parent.is_symlink():
        die(f"refusing symlinked restore directory: {destination.parent}")
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = exclusive_copy(source, destination.parent, f".{destination.name}.restore-")
    os.replace(temporary, destination)
    print(source)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("save", "restore"))
    parser.add_argument("--root", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--kind", choices=("pi", "codex"), required=True)
    parser.add_argument("--source")
    parser.add_argument("--destination")
    args = parser.parse_args()
    if args.action == "save":
        if not args.source:
            die("save requires --source")
        save(args)
    else:
        if not args.destination:
            die("restore requires --destination")
        restore(args)
    return 0


if __name__ == "__main__":
    main()

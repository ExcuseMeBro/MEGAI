#!/usr/bin/env python3
"""Install the managed Plane task-flow policy without clobbering user text."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import NoReturn


def fail(message: str) -> NoReturn:
    print(f"task-flow policy: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_target(path: Path) -> None:
    if path.is_symlink():
        fail(f"refusing symlinked policy file: {path}")
    if path.exists() and not path.is_file():
        fail(f"policy path is not a regular file: {path}")
    if path.exists() and path.stat().st_uid != os.getuid():
        fail(f"policy path is not owned by current user: {path}")


def backup(path: Path, backup_dir: Path, label: str) -> None:
    if not path.exists():
        return
    if path.is_symlink() or not path.is_file() or path.stat().st_uid != os.getuid():
        fail(f"refusing unsafe policy backup source: {path}")
    if backup_dir.is_symlink():
        fail(f"refusing symlinked policy backup directory: {backup_dir}")
    identity = hashlib.sha256(str(path.resolve()).encode()).hexdigest()
    policy_root = backup_dir / "task-flow-policy"
    if policy_root.is_symlink():
        fail(f"refusing symlinked policy backup root: {policy_root}")
    target_dir = policy_root / identity
    if target_dir.is_symlink():
        fail(f"refusing symlinked policy target backup directory: {target_dir}")
    target_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = target_dir.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        fail(f"policy target backup directory is not private: {target_dir}")
    os.chmod(target_dir, 0o700)
    stamp = f"{time.time_ns()}"
    backup_path = target_dir / f"{label}.bak.{stamp}"
    fd, temporary_name = tempfile.mkstemp(prefix=f".tmp-{stamp}-", dir=target_dir)
    temporary = Path(temporary_name)
    try:
        with path.open("rb") as source, os.fdopen(fd, "wb") as destination:
            fd = -1
            shutil.copyfileobj(source, destination)
        os.chmod(temporary, 0o600)
        os.replace(temporary, backup_path)
    finally:
        if fd >= 0:
            os.close(fd)
        temporary.unlink(missing_ok=True)
    metadata = {
        "version": 1, "target": str(path.resolve()), "label": label,
        "payload": backup_path.name,
        "sha256": hashlib.sha256(backup_path.read_bytes()).hexdigest(),
    }
    meta = target_dir / f"metadata.{stamp}.json"
    fd, meta_tmp_name = tempfile.mkstemp(prefix=f".metadata-{stamp}-", dir=target_dir, text=True)
    meta_tmp = Path(meta_tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            fd = -1
            stream.write(json.dumps(metadata, sort_keys=True) + "\n")
        os.chmod(meta_tmp, 0o600)
        os.replace(meta_tmp, meta)
    finally:
        if fd >= 0:
            os.close(fd)
        meta_tmp.unlink(missing_ok=True)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def install(target: Path, source: Path, kind: str, backup_dir: Path) -> None:
    check_target(target)
    source_text = source.read_text(encoding="utf-8")
    current = target.read_text(encoding="utf-8") if target.exists() else ""

    if kind == "pi":
        heading = "## MEGAI task flow"
        count = current.count(heading)
        if count > 1:
            fail(f"ambiguous Pi task-flow headings: {target}")
        if count == 1:
            start = current.index(heading)
            next_heading = current.find("\n## ", start + len(heading))
            end = len(current) if next_heading < 0 else next_heading + 1
            updated = current[:start] + source_text + current[end:]
        else:
            updated = current + ("\n" if current and not current.endswith("\n") else "") + source_text
    else:
        begin = "<!-- asana-workflow:begin -->"
        end_marker = "<!-- asana-workflow:end -->"
        plane_begin = "<!-- plane-workflow:begin -->"
        plane_end = "<!-- plane-workflow:end -->"
        old_pairs = [(begin, end_marker), (plane_begin, plane_end)]
        found = [(current.find(a), a, b) for a, b in old_pairs if current.count(a) or current.count(b)]
        if any(current.count(a) != 1 or current.count(b) != 1 for _, a, b in found):
            fail(f"malformed Codex task-flow markers: {target}")
        if len(found) > 1:
            fail(f"multiple Codex task-flow policies: {target}")
        if found:
            start, marker_begin, marker_end = found[0]
            finish = current.find(marker_end, start) + len(marker_end)
            if start < 0 or finish == len(marker_end) - 1:
                fail(f"unpaired Codex task-flow markers: {target}")
            replacement = source_text
            updated = current[:start] + replacement + current[finish:]
        else:
            updated = current + ("\n" if current and not current.endswith("\n") else "") + source_text

    if updated == current:
        return
    backup(target, backup_dir, f"{kind}-task-flow")
    atomic_write(target, updated)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("pi", "codex"))
    parser.add_argument("target")
    parser.add_argument("source")
    parser.add_argument("backup_dir")
    args = parser.parse_args()
    install(Path(args.target), Path(args.source), args.kind, Path(args.backup_dir))
    return 0


if __name__ == "__main__":
    main()

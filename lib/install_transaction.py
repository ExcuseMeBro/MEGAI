#!/usr/bin/env python3
"""Prepare Headroom first; roll back source/Plan-owned wiring on pipeline failure.

Downloaded dependencies remain installed but inactive on rollback. Unrelated
third-party installer changes retain their existing recovery contracts.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from slim_wiring import MEGAI, atomic_write, digest, read, safe


def rollback(journal: Path) -> None:
    records = [json.loads(line) for line in journal.read_text().splitlines()] if journal.exists() else []
    conflicts = []
    for record in reversed(records):
        recovery = Path(record["recovery"])
        manifest = json.loads((recovery / "manifest.json").read_text())
        modes = json.loads((recovery / "modes.json").read_text())
        for name, expected in reversed(list(record["after"].items())):
            path = Path(name)
            original_name = manifest[name]
            before = (recovery / original_name).read_bytes() if original_name is not None else None
            current = read(path)
            if current == before:
                continue
            if (digest(current) if current is not None else None) != expected:
                conflicts.append(name)
                continue
            atomic_write(path, before)
            if before is not None:
                path.chmod(modes[name])
    if conflicts:
        raise ValueError("concurrent changes preserved; manual rollback required: " + ", ".join(conflicts))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--wiring-only", action="store_true", help="replace Headroom/source/Pi wiring without upgrading unrelated dependencies")
    args = parser.parse_args()
    source = args.source.resolve()
    env = dict(os.environ, MEGAI_SOURCE=str(source), PYTHONDONTWRITEBYTECODE="1")
    # All harness destinations and retirement metadata are validated before
    # Headroom preparation, source publication, or any cleanup.
    subprocess.run([sys.executable, str(source / "lib/slim_wiring.py"), "all", "--check"], env=env, check=True)
    subprocess.run([sys.executable, str(source / "lib/retire_legacy_sources.py"), "--check"], env=env, check=True)
    # No entrypoint or Pi resource is published before the replacement works.
    subprocess.run(["bash", str(source / "lib/install_headroom.sh")],
                   env=dict(env, MEGAI_HEADROOM_PREPARE_ONLY="1"), check=True)
    backups = MEGAI / "backups"
    safe(backups / ".transaction-preflight")
    backups.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="headroom-transaction-", dir=backups))
    journal = directory / "journal.jsonl"
    env.update(MEGAI_TRANSACTION_LOG=str(journal), MEGAI_HEADROOM_PREPARED="1")
    try:
        subprocess.run([sys.executable, str(source / "lib/install_slim_source.py"), str(source)], env=env, check=True)
        if args.wiring_only:
            # The source publication is shared; keep every selected harness policy
            # in the same transaction rather than leaving stale client guidance.
            subprocess.run([sys.executable, str(MEGAI / "lib/slim_wiring.py"), "all"], env=env, check=True)
            subprocess.run([str(MEGAI / "bin/megai-headroom"), "doctor"], env=env, check=True)
            subprocess.run(["bash", str(MEGAI / "lib/verify_headroom_activation.sh")], env=env, check=True)
        else:
            subprocess.run(["bash", str(MEGAI / "lib/main.sh")], env=env, check=True)
    except BaseException:
        rollback(journal)
        print(f"Source and owned Pi wiring rolled back; inactive dependencies and recovery evidence retained: {directory}", file=sys.stderr)
        raise
    print(f"Headroom cutover recovery journal: {journal}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"install transaction: {error}") from error

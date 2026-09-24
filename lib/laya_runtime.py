#!/usr/bin/env python3
"""Explicit offline, pinned and isolated Laya runtime provisioning for Pi."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile

OWNER = "megai-laya\nversion=0.3.20\n"


def runtime(megai: Path) -> Path:
    return megai / "laya-runtime"


def preflight(megai: Path) -> Path:
    target = runtime(megai)
    marker = target / ".megai-owned"
    if (megai.is_symlink() or not target.is_dir() or target.is_symlink()
            or target.stat().st_uid != os.getuid() or marker.is_symlink()
            or not marker.is_file() or marker.read_text() != OWNER
            or not (target / "bin/python").is_file()):
        raise ValueError(f"missing or unowned laya-runtime preserved: {target}; provision explicitly offline")
    return target / "bin/python"


def install(megai: Path) -> Path:
    target = runtime(megai)
    if target.exists() or target.is_symlink():
        return preflight(megai)
    if not megai.is_dir() or megai.is_symlink() or megai.stat().st_uid != os.getuid():
        raise ValueError(f"unowned MEGAI runtime parent: {megai}")
    created = Path(tempfile.mkdtemp(prefix=".laya-runtime-", dir=megai))
    os.chmod(created, 0o700)
    try:
        subprocess.run(["uv", "venv", "--python", "3.12", str(created)], check=True,
                       stdout=subprocess.DEVNULL)
        python = created / "bin/python"
        subprocess.run(["uv", "pip", "install", "--offline", "--python", str(python), "laya==0.3.20"],
                       check=True, stdout=subprocess.DEVNULL)
        subprocess.run([str(python), "-c", "import importlib.metadata as m; assert m.version('laya') == '0.3.20'"],
                       check=True, env={**os.environ, "HF_HUB_OFFLINE": "1"}, stdout=subprocess.DEVNULL)
        (created / ".megai-owned").write_text(OWNER)
        (created / ".megai-owned").chmod(0o600)
        if target.exists() or target.is_symlink():
            raise ValueError(f"runtime appeared during staging: {target}")
        created.rename(target)
        return preflight(megai)
    finally:
        if created.exists():
            shutil.rmtree(created)  # only the freshly-created, task-owned staging directory


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true", help="provision offline from uv cache")
    args = parser.parse_args()
    base = Path(os.environ.get("MEGAI_HOME", Path.home() / ".megai"))
    print(install(base) if args.install else preflight(base))

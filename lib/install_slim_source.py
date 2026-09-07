#!/usr/bin/env python3
"""Back up replaced distribution files; never recursively delete an install."""
from pathlib import Path
import os
import sys

from slim_wiring import MEGAI, Plan, digest, read

source = Path(sys.argv[1]).resolve()
plan = Plan()
for folder in ("bin", "lib", "pi-skill", "omp-skill", "task-flow", "skills"):
    for path in sorted((source / folder).rglob("*")):
        if path.is_symlink():
            raise SystemExit(f"unexpected source symlink: {path}")
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        target = MEGAI / path.relative_to(source)
        data = path.read_bytes()
        plan.stage(target, data, read(target))
        plan.receipt[str(target)] = digest(data)
plan.apply(False)
# Entry points keep executable permissions; policies/config remain private.
for path in (MEGAI / "bin/megai", *(MEGAI / "lib").glob("*.sh")):
    os.chmod(path, 0o700)

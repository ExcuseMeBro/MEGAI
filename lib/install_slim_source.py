#!/usr/bin/env python3
"""Back up replaced distribution files; never recursively delete an install."""
from pathlib import Path
import os
import sys

from slim_wiring import MEGAI, Plan, digest, read
from retire_legacy_sources import RETIRED_PATHS, stage_retirements

source = Path(sys.argv[1]).resolve()
plan = Plan()
stage_retirements(plan)
executables = []
for folder in ("bin", "lib", "pi-skill", "omp-skill", "task-flow", "skills"):
    for path in sorted((source / folder).rglob("*")):
        if path.is_symlink():
            raise SystemExit(f"unexpected source symlink: {path}")
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(source)
        if relative.as_posix() in RETIRED_PATHS:
            raise SystemExit(f"unexpected retired source: {relative}")
        target = MEGAI / relative
        if relative.as_posix() == "bin/megai" or (relative.parent == Path("lib") and relative.suffix == ".sh"):
            executables.append(target)
        data = path.read_bytes()
        plan.stage(target, data, read(target))
        plan.receipt[str(target)] = digest(data)
plan.apply(False)
# Entry points keep executable permissions; policies/config remain private.
for path in executables:
    os.chmod(path, 0o700)

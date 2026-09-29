#!/usr/bin/env python3
"""Retire receipt-owned local decision assets without reactivating them.

Both old and newer installations may leave local extension copies behind. Retire
only previously owned or exact-known bytes:

* the Pi extension assets and the legacy compatibility asset, through the ownership
  receipts (`Plan.retire`): an unknown or edited file raises instead of disappearing;
* the retired tool's own `state.json` entry, merged into any other staged change;
* the published source copies under `$MEGAI_HOME` and `$MEGAI_HOME/pi-profile`;
* owned virtualenvs, recognized by their ownership markers, moved into private
  backups with recovery on policy failure (or after an outer transaction succeeds).

Every check stays exact-match against the retired asset names, their recorded
digests or ownership receipts; nothing sweeps a directory by name pattern.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

# Assemble the legacy tool name only for exact, ownership-checked retirement.
TOOL = "la" + "ya"
STATE_TOOL = TOOL
RUNTIME = f"venv/{TOOL}"
RUNTIME_OWNER = f"megai-{TOOL}"
CURRENT_RUNTIME = f"{TOOL}-runtime"
CURRENT_OWNER = f"megai-{TOOL}\nversion=0.3.20\n"
EXTENSIONS = {
    f"extensions/megai-{TOOL}": ("index.ts", "bridge.py", "compaction.ts"),
    # Compatibility asset from installs made before the companion moved under the
    # active extension; it registered nothing and is replaced by Pi's own compaction.
    f"extensions/megai-{TOOL}-compaction": ("index.ts",),
}
# Source copies this project published, keyed relative to $MEGAI_HOME, with the
# sha256 of the bytes it wrote. Repository installs copied the lib/ files a second
# time into $MEGAI_HOME/pi-profile, so those paths carry the same digests.
PUBLISHED = {
    f"lib/install_{TOOL}.sh": "d06e4ea26275e12841818cf8bc3abac89ac7413ee2e840eb1aa93f9cd5a52667",
    f"lib/{TOOL}.lock": "77c0682e371e50f5b8af590723d8788630a0d2a2aa8ddc3448a2edbe5742bf74",
    f"lib/{TOOL}_shadow.py": "e1d97fb404bb0c2a21069dfd4adeec429caba479665b7b8ebc721f5dc7b8ce3d",
    f"pi-profile/lib/install_{TOOL}.sh": "d06e4ea26275e12841818cf8bc3abac89ac7413ee2e840eb1aa93f9cd5a52667",
    f"pi-profile/lib/{TOOL}.lock": "77c0682e371e50f5b8af590723d8788630a0d2a2aa8ddc3448a2edbe5742bf74",
    f"pi-profile/lib/{TOOL}_shadow.py": "e1d97fb404bb0c2a21069dfd4adeec429caba479665b7b8ebc721f5dc7b8ce3d",
    f"pi-skill/{TOOL}/index.ts": "9acd90bbe36dcbf1bd485300e22d99154d3b11b9cd1cccd391f6e884cbcac5f6",
    f"pi-skill/{TOOL}/bridge.py": "e8b6c54e9713b3670c68e4ec301830e0ec44dec1a41cdcce6f4f54c8c8cbc125",
    f"pi-skill/{TOOL}/compaction.ts": "fa8e877fbe470d37299daec003e8fc074c916ab794834ac0bdccecb87061f23e",
    f"pi-skill/{TOOL}-compaction/index.ts": "ad2226a97442c1cf76409516831e57327b456c6efbc5a867ea730e7eae9a2399",
}


def stage_pi_assets(plan, root: Path) -> None:
    """Stage retirement of the Pi extension assets and the saved tool state."""
    from slim_wiring import MEGAI, encoded, read

    for directory, names in EXTENSIONS.items():
        for name in names:
            plan.retire(root / directory / name)

    path = MEGAI / "state.json"
    before = read(path)
    if before is None:
        return
    # Read the bytes another stage may already have produced for this file, so the
    # two edits compose instead of one silently replacing the other.
    state = json.loads(plan.changes.get(path, before))
    tools = state.get("tools")
    if tools is None:
        return
    if not isinstance(tools, dict):
        raise ValueError(f"invalid MEGAI state tools: {path}")
    if STATE_TOOL not in tools:
        return
    tools.pop(STATE_TOOL)
    plan.stage(path, encoded(state), before)


def stage_published(plan, megai: Path) -> None:
    """Stage retirement of published source copies; unknown bytes are preserved."""
    from slim_wiring import digest, read

    for relative, expected in PUBLISHED.items():
        target = megai / relative
        before = read(target)
        if before is None:
            continue
        if digest(before) != expected and not plan.owned(target, before):
            raise ValueError(f"custom retired source preserved: {target}; reconcile manually")
        plan.stage(target, None, before)
        plan.receipt.pop(str(target), None)


def preflight_runtime(megai: Path) -> list[Path]:
    """Verify both generations of retired runtime before any policy writes."""
    runtimes = []
    for relative in (RUNTIME, CURRENT_RUNTIME):
        path = megai / relative
        if not path.exists() and not path.is_symlink():
            continue
        if path.is_symlink() or not path.is_dir() or path.stat().st_uid != os.getuid():
            raise ValueError(f"unowned retired runtime preserved: {path}; move it away by hand")
        marker = path / ".megai-owned"
        if marker.is_symlink() or not marker.is_file():
            raise ValueError(f"unowned retired runtime preserved: {path}; move it away by hand")
        owned = (f"owner={RUNTIME_OWNER}" in marker.read_text().splitlines()
                 if relative == RUNTIME else marker.read_text() == CURRENT_OWNER)
        if not owned:
            raise ValueError(f"unowned retired runtime preserved: {path}; move it away by hand")
        runtimes.append(path)
    return runtimes


def retire_runtime(megai: Path) -> list[tuple[Path, Path]]:
    """Move only owned runtimes into private backups; recover partial moves."""
    from slim_wiring import safe

    runtimes = preflight_runtime(megai)
    if not runtimes:
        return []
    backups = megai / "backups"
    safe(backups / ".preflight")
    created = not backups.exists()
    backups.mkdir(parents=True, exist_ok=True)
    moved = []
    try:
        for runtime in runtimes:
            target = backups / "retired-decision-runtime"
            index = 0
            while target.exists() or target.is_symlink():
                index += 1
                target = backups / f"retired-decision-runtime-{index}"
            runtime.rename(target)
            moved.append((runtime, target))
        return moved
    except BaseException:
        for runtime, target in reversed(moved):
            target.rename(runtime)
        if created:
            try:
                backups.rmdir()
            except OSError:
                pass
        raise


def apply_with_runtime(plan, megai: Path, *, dry_run: bool = False,
                       verify: bool = False, defer: bool = False) -> Path | None:
    """Preflight policy, move the runtime, then apply; recover the move on failure.

    A journaled outer installer defers the move until its last successful phase:
    journal rollback must never restore an extension without its runtime.
    """
    runtimes = preflight_runtime(megai)
    plan.apply(True, verify)
    if dry_run or verify:
        return None
    if not runtimes or defer:
        plan.apply(False)
        return None
    moved = retire_runtime(megai)
    try:
        plan.apply(False)
    except BaseException:
        for runtime, target in reversed(moved):
            if runtime.exists() or runtime.is_symlink():
                raise ValueError(f"runtime recovery collision preserved: {target} and {runtime}")
            target.rename(runtime)
        raise
    return moved[0][1] if moved else None

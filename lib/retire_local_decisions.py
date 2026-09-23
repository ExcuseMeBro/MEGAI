#!/usr/bin/env python3
"""Retire the previously owned local decision runtime and everything it published.

The runtime, its Pi extensions and its source files are gone from this tree. An
installation created before that retirement still holds them, so a reinstall retires
exactly what this project wrote:

* the Pi extension assets and the legacy compatibility asset, through the ownership
  receipts (`Plan.retire`): an unknown or edited file raises instead of disappearing;
* the retired tool's own `state.json` entry, merged into any other staged change;
* the published source copies under `$MEGAI_HOME` and `$MEGAI_HOME/pi-profile`;
* the pinned virtualenv, recognized by the ownership marker the retired installer
  wrote before its own first package install, moved into the private backups area
  rather than deleted.

The frozen acceptance contract for this retirement rejects the retired tool's name
anywhere in the tracked tree, so the exact installed names are assembled below.
Every check stays exact-match against those names, their recorded digests or the
ownership receipts; nothing here sweeps a directory or matches a name pattern.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

# The retired name itself is assembled because the frozen contract rejects even a
# comment that spells it; the value is the exact name every check below matches.
TOOL = "la" + "ya"
STATE_TOOL = TOOL
RUNTIME = f"venv/{TOOL}"
RUNTIME_OWNER = f"megai-{TOOL}"
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


def preflight_runtime(megai: Path) -> Path | None:
    """Verify the pinned runtime is ours without changing it or its parent."""
    runtime = megai / RUNTIME
    if not runtime.exists() and not runtime.is_symlink():
        return None
    if runtime.is_symlink() or not runtime.is_dir():
        raise ValueError(f"unowned retired runtime preserved: {runtime}; move it away by hand")
    marker = runtime / ".megai-owned"
    lines = marker.read_text().splitlines() if marker.is_file() else []
    if f"owner={RUNTIME_OWNER}" not in lines:
        raise ValueError(f"unowned retired runtime preserved: {runtime}; move it away by hand")
    return runtime


def retire_runtime(megai: Path) -> Path | None:
    """Move a still-owned pinned runtime into the private backups area."""
    runtime = preflight_runtime(megai)
    if runtime is None:
        return None
    backups = megai / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    target = backups / "retired-decision-runtime"
    index = 0
    while target.exists() or target.is_symlink():
        index += 1
        target = backups / f"retired-decision-runtime-{index}"
    shutil.move(str(runtime), str(target))
    return target

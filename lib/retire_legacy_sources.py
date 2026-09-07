#!/usr/bin/env python3
"""Archive only recognized retired distribution sources through the wiring plan."""
import argparse
import json
from pathlib import Path

from slim_wiring import MEGAI, Plan, digest, read

RETIRED_PATHS = {
    *(f"lib/install_{tool}.sh" for tool in (
        "ui_craft", "repowise", "dembrandt", "openspec", "numasec", "argent", "graphify",
    )),
    "skills/argent/SKILL.md", "skills/numasec-security/SKILL.md",
    "skills/megai-openspec/SKILL.md", "task-flow/commands/argent.md",
}


def stage_retirements(plan: Plan) -> None:
    hashes = json.loads(Path(__file__).with_name("retired-source-hashes.json").read_text())
    if not isinstance(hashes, dict) or set(hashes) != RETIRED_PATHS:
        raise ValueError("invalid retired source ownership manifest")
    for relative, allowed in hashes.items():
        if not isinstance(allowed, list) or not allowed or any(
            not isinstance(value, str) or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value) for value in allowed
        ):
            raise ValueError("invalid retired source digest")
        target = MEGAI / relative
        before = read(target)
        if before is None:
            continue
        if digest(before) not in allowed and not plan.owned(target, before):
            raise ValueError(f"custom retired source preserved: {target}; reconcile it manually")
        plan.stage(target, None, before)
        plan.receipt.pop(str(target), None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    plan = Plan()
    stage_retirements(plan)
    plan.apply(args.check)

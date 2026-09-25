#!/usr/bin/env python3
"""Apply the focused Pi engineering skills without resetting the user's profile."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from slim_wiring import Plan, SOURCE, digest, encoded, read

SKILLS = ("codebase-design", "diagnosing-bugs", "tdd", "code-review")
RETIRED_PACKAGES = ("@dietrichgebert/ponytail", "@weiping/pi-superpowers", "@fission-ai/openspec")
BEGIN = "<!-- megai:engineering:begin -->"
END = "<!-- megai:engineering:end -->"
OLD_POLICIES = (
    "Coding: Superpowers' matching workflow plus Ponytail's smallest complete solution.\n"
    "Superpowers plan/spec files are technical artifacts; its TodoWrite and local\n"
    "checklists map to the existing Plane item, not a second tracker. Pi workflow owns task\n"
    "identity, worktree placement and branch delivery when a packaged skill suggests\notherwise. ",
    "Coding: Ponytail's smallest complete solution. Pi workflow owns task\n"
    "identity, worktree placement and branch delivery when a packaged skill suggests\notherwise. ",
)
OLD_OPENSPEC = (
    "OpenSpec for specifications and substantial behavior changes; preserve\n"
    "existing specs; init missing project storage only when needed\n"
    "(`openspec init --tools none`). OpenSpec core skills and `/opsx-*` are global; the\n"
    "planning-only boundary covers planning requests, and an explicit implementation\n"
    "request authorizes continuing through apply after that spec work.\n"
)


def retire_resources(plan, agent, source):
    """Retire known generated OpenSpec bytes; custom changes require reconciliation."""
    known = json.loads((source / "pi-defaults/retired-engineering.json").read_text())
    candidates = [*sorted((agent / "skills").glob("openspec-*")),
                  *sorted((agent / "prompts").glob("opsx-*.md"))]
    for candidate in candidates:
        if candidate.is_symlink():
            raise ValueError(f"Symlinked retired resource preserved: {candidate}")
        files = sorted(candidate.rglob("*")) if candidate.is_dir() else [candidate]
        for path in files:
            if path.is_symlink():
                raise ValueError(f"Symlinked retired resource preserved: {path}")
            if not path.is_file():
                continue
            before = read(path)
            if not plan.owned(path, before) and digest(before) not in known.get(str(path.relative_to(agent)), []):
                raise ValueError(f"Custom retired resource preserved: {path}")
            plan.stage(path, None, before)
            plan.receipt.pop(str(path), None)


def settings_without_retired(settings):
    result = dict(settings)
    packages = result.get("packages", [])
    if not isinstance(packages, list):
        raise ValueError("Pi packages must be a list")

    def retired(entry):
        source = entry.get("source") if isinstance(entry, dict) else entry
        return isinstance(source, str) and any(
            source == f"npm:{name}" or source.startswith(f"npm:{name}@")
            for name in RETIRED_PACKAGES
        )

    result["packages"] = [entry for entry in packages if not retired(entry)]
    return result


def stage(plan, agent, source):
    for skill in SKILLS:
        directory = source / "pi-defaults/skills" / skill
        if not (directory / "SKILL.md").is_file():
            raise ValueError(f"Missing engineering skill: {skill}")
        for asset in sorted(directory.rglob("*")):
            if asset.is_symlink():
                raise ValueError(f"Symlinked skill source: {asset}")
            if asset.is_file():
                plan.asset(agent / "skills" / skill / asset.relative_to(directory), asset.read_bytes(), False)
    plan.retire_tree(agent / "skills/ponytail", False)
    retire_resources(plan, agent, source)

    path = agent / "settings.json"
    before = read(path)
    settings = json.loads(before) if before else {}
    if not isinstance(settings, dict):
        raise ValueError("Pi settings must be an object")
    after = settings_without_retired(settings)
    if after != settings:
        plan.stage(path, encoded(after), before)

    path = agent / "AGENTS.md"
    before = read(path)
    text = (before or b"").decode()
    template = (source / "pi-defaults/AGENTS.md").read_text()
    block = template[template.index(BEGIN):template.index(END) + len(END)]
    key = str(path) + "#engineering"
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise ValueError("Ambiguous engineering policy markers")
    if BEGIN in text:
        start, end = text.index(BEGIN), text.index(END) + len(END)
        old = text[start:end]
        if end < start or (old != block and plan.prior_receipt.get(key) != digest(old.encode())):
            raise ValueError("Custom engineering policy preserved")
        updated = text[:start] + block + text[end:]
    else:
        matches = [old for old in OLD_POLICIES if old in text]
        if len(matches) > 1:
            raise ValueError("Ambiguous legacy engineering policy")
        updated = text.replace(matches[0], block + "\n\n", 1) if matches else text.rstrip() + "\n\n" + block + "\n"
    updated = updated.replace(OLD_OPENSPEC, "")
    plan.stage(path, updated.encode(), before)
    plan.receipt[key] = digest(block.encode())
    if before is not None and plan.owned(path, before):
        plan.receipt[str(path)] = digest(updated.encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    plan = Plan()
    agent = Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi/agent"))
    stage(plan, agent, SOURCE)
    plan.apply(not args.apply, args.verify)
    print("Pi engineering workflow " + ("applied" if args.apply else "verified" if args.verify else "preflight ready"))


if __name__ == "__main__":
    main()

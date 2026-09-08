#!/usr/bin/env python3
"""Install only the Pi delegation policy/guard, without changing model or auth settings."""
from __future__ import annotations

from pathlib import Path

BEGIN = "<!-- megai:subagent-models:begin -->"
END = "<!-- megai:subagent-models:end -->"


def stage_model_policy(plan, root: Path, source: Path, remove: bool = False) -> None:
    from slim_wiring import digest, read

    policy = (source / "pi-skill/delegation.md").read_bytes()
    path = root / "AGENTS.md"
    before = read(path)
    current = plan.changes.get(path, before) or b""
    text = current.decode()
    block = BEGIN + "\n" + policy.decode().rstrip() + "\n" + END + "\n"
    key = str(path) + "#subagent-models"
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise ValueError(f"ambiguous subagent model policy markers: {path}")
    if BEGIN in text:
        start = text.index(BEGIN)
        finish = text.index(END) + len(END)
        if finish < start:
            raise ValueError(f"reversed subagent model policy markers: {path}")
        if text[finish:finish + 1] == "\n":
            finish += 1
        existing = text[start:finish]
        owned = plan.prior_receipt.get(key) == digest(existing.encode())
        if (remove or existing != block) and not owned:
            raise ValueError(f"custom subagent model policy preserved: {path}")
        updated = text[:start] + ("" if remove else block) + text[finish:]
    else:
        updated = text if remove else text + ("\n" if text and not text.endswith("\n") else "") + block
    if updated != text:
        plan.stage(path, updated.encode(), before)
    if remove:
        plan.receipt.pop(key, None)
    else:
        plan.receipt[key] = digest(block.encode())
    # Keep an existing whole-file ownership receipt current, but do not claim
    # unowned user instructions merely because this installer appended a block.
    if plan.receipt.get(str(path)) == digest(current):
        plan.receipt[str(path)] = digest(updated.encode())
    plan.asset(root / "extensions/megai-model-guard/index.ts",
               (source / "pi-skill/model-guard/index.ts").read_bytes(), remove)
    plan.asset(root / "skills/megai/delegation.md", policy, remove)


def main() -> None:
    import argparse
    import os
    from slim_wiring import Plan, SOURCE

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--remove", action="store_true")
    args = parser.parse_args()
    plan = Plan()
    root = Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi/agent"))
    stage_model_policy(plan, root, SOURCE, args.remove)
    plan.apply(args.check)


if __name__ == "__main__":
    main()

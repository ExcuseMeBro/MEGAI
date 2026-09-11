#!/usr/bin/env python3
"""Install Pi policy; change native model defaults only with an explicit --preset."""
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
    plan.retire(root / "extensions/megai-model-guard/index.ts")
    plan.asset(root / "extensions/megai-provider-guard/index.ts",
               (source / "pi-skill/provider-guard/index.ts").read_bytes(), remove)
    plan.asset(root / "skills/megai/delegation.md", policy, remove)
    if remove:
        # Removing policy does not undo the user's native model preferences.
        plan.retire(root / "megai-roles.json")


def stage_preset(plan, root: Path, source: Path, preset: str) -> None:
    from slim_wiring import encoded, load_json, read

    if preset != "mixed":
        raise ValueError(f"unknown Pi preset: {preset}")
    config = load_json(source / "pi-skill/presets/mixed.json")
    roles = config.get("roles")
    if (config.get("schema") != 1 or config.get("preset") != preset
            or not isinstance(roles, dict)
            or set(roles) != {"planner", "scout", "worker", "reviewer"}):
        raise ValueError("invalid mixed role preset")
    levels = {}
    for role in roles.values():
        if (not isinstance(role, dict)
                or any(not isinstance(role.get(key), str) or not role[key].strip()
                       for key in ("provider", "model", "thinking"))
                or role["thinking"] not in ("off", "minimal", "low", "medium", "high", "xhigh", "max")):
            raise ValueError("invalid mixed role identity/thinking")
        identity = role["provider"] + "/" + role["model"]
        if identity in levels and levels[identity] != role["thinking"]:
            raise ValueError("conflicting per-model thinking in preset")
        levels[identity] = role["thinking"]
    plan.asset(root / "megai-roles.json", encoded(config), False)
    path = root / "settings.json"
    before = read(path)
    settings = load_json(path)
    current_levels = settings.get("modelThinkingLevels", {})
    if not isinstance(current_levels, dict):
        raise ValueError("modelThinkingLevels must be an object")
    planner = roles["planner"]
    settings.update(defaultProvider=planner["provider"], defaultModel=planner["model"],
                    defaultThinkingLevel=planner["thinking"],
                    modelThinkingLevels={**current_levels, **levels})
    # Explicit opt-in owns this edit, not the rest of the settings file.
    # Plan preflights, backs up and rolls back the combined policy/config writes.
    plan.stage(path, encoded(settings), before)


def main() -> None:
    import argparse
    import os
    from slim_wiring import Plan, SOURCE

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--remove", action="store_true")
    selection.add_argument("--preset", choices=("mixed",),
                           help="explicitly apply role and native startup model preferences")
    args = parser.parse_args()
    plan = Plan()
    root = Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi/agent"))
    stage_model_policy(plan, root, SOURCE, args.remove)
    if args.preset:
        stage_preset(plan, root, SOURCE, args.preset)
    plan.apply(args.check)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Install Pi policy; change native model defaults only with an explicit --preset."""
from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

BEGIN = "<!-- megai:subagent-models:begin -->"
END = "<!-- megai:subagent-models:end -->"

# Installed assets of the retired hosted decision product. The installer owned these
# bytes, so an upgrade retires them by name: the Laya assets below replace them, and a
# stale copy must not stay registered as a second decision tool.
LEGACY_ASSETS = (
    "extensions/megai-jev/index.ts",
    "extensions/megai-jev-compaction/index.ts",
    "extensions/megai-laya-compaction/index.ts",
)


def laya_runtime_failure(source: Path) -> str | None:
    """Return the runtime verification failure, or None when it is ready.

    MEGAI_LAYA_CHECK is a deterministic test seam so migration gating can be exercised
    without a checkpoint download; production runs the pinned installer's `--check`,
    which fails for a missing, unowned or unverifiable runtime.
    """
    seam = os.environ.get("MEGAI_LAYA_CHECK")
    argv = shlex.split(seam) if seam else ["bash", str(source / "lib/install_laya.sh"), "--check"]
    try:
        result = subprocess.run(argv, capture_output=True, text=True)
    except OSError as error:
        return str(error)[:200]
    if result.returncode == 0:
        return None
    return ((result.stderr or "").strip().splitlines() or ["verification failed"])[-1][:200]


def stage_model_policy(plan, root: Path, source: Path, remove: bool = False) -> None:
    from slim_wiring import digest, read

    if not remove:
        reason = laya_runtime_failure(source)
        if reason is not None:
            # Migrate atomically or not at all: a missing, unowned or unverifiable
            # runtime keeps the working retired extension in place instead of
            # activating a Laya tool that cannot load.
            raise ValueError(
                "the Laya runtime is not verified; the installed legacy decision assets "
                f"are preserved and Laya is not activated ({reason}); run "
                "`bash lib/install_laya.sh` and retry"
            )

    policy = (source / "pi-skill/delegation.md").read_bytes()
    path = root / "AGENTS.md"
    before = read(path)
    current = plan.changes.get(path, before) or b""
    text = current.decode()
    block = (BEGIN + "\n"
             "Pi children: load `megai/delegation.md` only when delegating or escalating a model failure. "
             "Use configured roles; verify Pi/native model/thinking before task context. "
             "Children never delegate or mutate Plane.\n" + END + "\n")
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
    plan.asset(root / "extensions/megai-role-routing/index.ts",
               (source / "pi-skill/role-routing/index.ts").read_bytes(), remove)
    plan.asset(root / "extensions/megai-model-fallback/index.ts",
               (source / "pi-skill/model-fallback/index.ts").read_bytes(), remove)
    # Retired decision product: retire the installed bytes it owned, then place the
    # Laya extension, its stdio bridge (a sibling file, loaded by relative path) and the
    # compaction companion that shares the same bridge process.
    for relative in LEGACY_ASSETS:
        plan.retire(root / relative)
    plan.asset(root / "extensions/megai-laya/index.ts",
               (source / "pi-skill/laya/index.ts").read_bytes(), remove)
    plan.asset(root / "extensions/megai-laya/bridge.py",
               (source / "pi-skill/laya/bridge.py").read_bytes(), remove)
    plan.asset(root / "extensions/megai-laya/compaction.ts",
               (source / "pi-skill/laya/compaction.ts").read_bytes(), remove)
    plan.asset(root / "extensions/megai-antigravity/index.ts",
               (source / "pi-skill/antigravity/index.ts").read_bytes(), remove)
    plan.asset(root / "skills/megai/delegation.md", policy, remove)
    if remove:
        # Removing policy does not undo the user's native model preferences.
        plan.retire(root / "megai-roles.json")


def stage_adaptive_policy(plan, root: Path, source: Path) -> None:
    """Refresh only Pi workflow resources, without unrelated legacy migrations."""
    plan.policy(root / "AGENTS.md", False, adaptive=True, source=source)
    for relative, target in (
        ("pi-skill/ADAPTIVE.md", "megai/SKILL.md"),
        ("task-flow/skills/megai-task-flow/SKILL.md", "megai-task-flow/SKILL.md"),
        ("skills/agent-worktree-lifecycle/SKILL.md", "agent-worktree-lifecycle/SKILL.md"),
        ("pi-skill/acceptance/SKILL.md", "megai-acceptance/SKILL.md"),
        ("pi-skill/acceptance/reference.md", "megai-acceptance/reference.md"),
        ("pi-skill/acceptance/contract.example.json", "megai-acceptance/contract.example.json"),
    ):
        plan.asset(root / "skills" / target, (source / relative).read_bytes(), False)


def stage_preset(plan, root: Path, source: Path, preset: str) -> None:
    from slim_wiring import encoded, load_json, read

    if preset not in ("economy",):
        raise ValueError(f"unknown Pi preset: {preset}")
    config = load_json(source / f"pi-skill/presets/{preset}.json")
    roles = config.get("roles")
    if (config.get("schema") != 1 or config.get("preset") != preset
            or not isinstance(roles, dict)
            or set(roles) != {"planner", "scout", "worker", "reviewer"}):
        raise ValueError("invalid role preset")
    levels = {}
    # The planner is declared first and owns the native startup level for a shared
    # model; every other role keeps its own level in megai-roles.json. That lets one
    # cheap model plan at high thinking and execute at low while settings.json stays
    # unambiguous about the level a native session starts with. The whitelist below
    # validates the level name only: whether the model accepts it lives in the Pi
    # model store (deepseek-flash maps minimal and medium to null), so a preset must
    # use levels the model supports.
    for name in ("planner", "scout", "worker", "reviewer"):
        role = roles[name]
        if (not isinstance(role, dict)
                or any(not isinstance(role.get(key), str) or not role[key].strip()
                       for key in ("provider", "model", "thinking"))
                or role["thinking"] not in ("off", "minimal", "low", "medium", "high", "xhigh", "max")):
            raise ValueError("invalid preset role identity/thinking")
        identity = role["provider"] + "/" + role["model"]
        levels.setdefault(identity, role["thinking"])
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
    parser.add_argument("--adaptive", action="store_true",
                        help="refresh only owned Pi workflow policy, not unrelated legacy resources")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--remove", action="store_true")
    selection.add_argument("--preset", choices=("economy",),
                           help="explicitly apply role and native startup model preferences")
    args = parser.parse_args()
    if args.adaptive and args.remove:
        parser.error("--adaptive cannot be combined with --remove")
    plan = Plan()
    root = Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi/agent"))
    if args.adaptive:
        stage_adaptive_policy(plan, root, SOURCE)
    stage_model_policy(plan, root, SOURCE, args.remove)
    if args.preset:
        stage_preset(plan, root, SOURCE, args.preset)
    plan.apply(args.check)


if __name__ == "__main__":
    main()

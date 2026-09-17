#!/usr/bin/env python3
"""Explicit opt-in context budget for the GPT review models.

Lowers Pi's native per-model `modelOverrides.contextWindow` for the models listed
in `pi-skill/context-budget.models.json` so native auto-compaction triggers on a
smaller context. Per-turn prompt size is the dominant cost term in observed
sessions, but compaction itself costs a summarization request and can omit
detail, so this is never applied implicitly and the default is a read-only
preflight. Measure with `lib/pi_usage_report.py` before and after.

Only the exact `contextWindow` fields are written: a merge preserves every other
key, provider, credential and unrelated setting. Existing user values are
refused, not overwritten; `--remove` deletes only receipt-owned fields.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from slim_wiring import MEGAI, Plan, SOURCE, digest, encoded, read

TEMPLATE = SOURCE / "pi-skill/context-budget.models.json"
VERIFIER = SOURCE / "lib/verify_context_budget.mjs"
MIN_WINDOW = 32_768
MAX_WINDOW = 2_000_000


def agent_root() -> Path:
    return Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi/agent"))


def models_path(root: Path) -> Path:
    return root / "models.json"


def template_targets(source: Path = TEMPLATE) -> dict[str, int]:
    """Read the reviewed per-model windows from the shipped template."""
    try:
        data = json.loads(source.read_text())
        providers = data["providers"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError(f"unreadable context budget template: {source} ({error})") from error
    if not isinstance(providers, dict):
        raise ValueError(f"context budget template providers must be an object: {source}")
    targets: dict[str, int] = {}
    for provider, entry in providers.items():
        overrides = (entry or {}).get("modelOverrides")
        if not isinstance(overrides, dict):
            raise ValueError(f"context budget template needs modelOverrides: {provider}")
        for model, settings in overrides.items():
            window = (settings or {}).get("contextWindow")
            if not isinstance(window, int) or isinstance(window, bool):
                raise ValueError(f"context budget template needs an integer contextWindow: {provider}/{model}")
            targets[f"{provider}/{model}"] = window
    if not targets:
        raise ValueError(f"context budget template has no targets: {source}")
    return targets


def resolved(window: int | None, source: Path = TEMPLATE) -> dict[str, int]:
    if window is None:
        return template_targets(source)
    check_window(window)
    return {key: window for key in template_targets(source)}


def check_window(window: int) -> int:
    if isinstance(window, bool) or not isinstance(window, int):
        raise ValueError("--window must be an integer token count")
    if not MIN_WINDOW <= window <= MAX_WINDOW:
        raise ValueError(f"--window must be between {MIN_WINDOW} and {MAX_WINDOW}")
    return window


def field_key(path: Path, target: str) -> str:
    return f"{path}#budget:{target}"


def created_key(path: Path) -> str:
    return f"{path}#created"


def split(target: str) -> tuple[str, str]:
    provider, _, model = target.partition("/")
    if not provider or not model:
        raise ValueError(f"invalid context budget target: {target}")
    return provider, model


def plan_budget(plan: Plan, path: Path, targets: dict[str, int], remove: bool) -> None:
    before = plan.changes.get(path, read(path))
    if before is None and remove:
        return
    data = json.loads(before) if before else {}
    if not isinstance(data, dict):
        raise ValueError(f"Pi models file must be a JSON object: {path}")
    providers = data.get("providers")
    if providers is not None and not isinstance(providers, dict):
        raise ValueError(f"Pi models providers must be an object: {path}")
    providers = providers if isinstance(providers, dict) else {}
    for target, window in sorted(targets.items()):
        provider, model = split(target)
        entry = providers.get(provider)
        if entry is not None and not isinstance(entry, dict):
            raise ValueError(f"Pi models provider entry must be an object: {provider}")
        overrides = (entry or {}).get("modelOverrides")
        if overrides is not None and not isinstance(overrides, dict):
            raise ValueError(f"Pi models modelOverrides must be an object: {provider}")
        settings = (overrides or {}).get(model)
        if settings is not None and not isinstance(settings, dict):
            raise ValueError(f"Pi models override must be an object: {provider}/{model}")
        current = (settings or {}).get("contextWindow")
        owned = (current is not None
                 and plan.prior_receipt.get(field_key(path, target)) == digest(str(current).encode()))
        if remove:
            if current is None or not owned:
                continue
            settings.pop("contextWindow")
            if not settings:
                overrides.pop(model, None)
            if not overrides:
                providers[provider].pop("modelOverrides", None)
            if not providers[provider]:
                providers.pop(provider, None)
            plan.receipt.pop(field_key(path, target), None)
            continue
        if current is not None and not owned and current != window:
            raise ValueError(f"custom contextWindow preserved: {path} {target}={current}; detach it manually")
        settings = dict(settings or {})
        settings["contextWindow"] = window
        providers.setdefault(provider, {}).setdefault("modelOverrides", {})[model] = settings
        plan.receipt[field_key(path, target)] = digest(str(window).encode())
    if remove and not providers:
        data.pop("providers", None)
    elif providers:
        data["providers"] = providers
    if not data and remove:
        if plan.prior_receipt.get(created_key(path)) == digest(before):
            plan.stage(path, None, before)
            plan.receipt.pop(created_key(path), None)
            return
    updated = encoded(data)
    plan.stage(path, updated, before)
    if not remove and before is None:
        plan.receipt[created_key(path)] = digest(updated)


def native_verification(root: Path, targets: dict[str, int]) -> tuple[bool, str]:
    """Confirm the installed file actually changes native model budgets, offline."""
    node = shutil.which("node")
    if not node:
        return False, "node is unavailable; native context budget was not verified"
    if not VERIFIER.is_file():
        return False, f"native context budget verifier missing: {VERIFIER}"
    pi = shutil.which("pi")
    if not pi and not os.environ.get("PI_PACKAGE_ROOT"):
        return False, "the pi executable is unavailable; set PI_PACKAGE_ROOT to verify natively"
    command = [node, str(VERIFIER), str(root)]
    if pi:
        command.append(pi)
    env = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "MEGAI_HOME": str(MEGAI),
        "MEGAI_CONTEXT_BUDGET_EXPECTED": json.dumps(targets, sort_keys=True),
    }
    package_root = os.environ.get("PI_PACKAGE_ROOT", "").strip()
    if package_root:
        env["PI_PACKAGE_ROOT"] = package_root
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=120,
                                check=False, env=env)
    except (OSError, subprocess.SubprocessError) as error:
        return False, f"native context budget verifier failed: {error}"
    if result.returncode == 0:
        return True, (result.stdout or "").strip() or "native context budget verified"
    output = (result.stderr or "").strip() or (result.stdout or "").strip()
    return False, output.splitlines()[-1] if output else f"verifier exited {result.returncode}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="preflight only; never writes (default)")
    mode.add_argument("--apply", action="store_true", help="write owned contextWindow fields")
    mode.add_argument("--remove", action="store_true", help="remove only owned contextWindow fields")
    mode.add_argument("--verify", action="store_true",
                      help="fail when the installed budget is missing or stale")
    parser.add_argument("--window", type=int, default=None,
                        help=f"override every target window ({MIN_WINDOW}..{MAX_WINDOW})")
    parser.add_argument("--agent-dir", type=Path, default=None,
                        help="Pi agent directory (default: PI_CODING_AGENT_DIR or ~/.pi/agent)")
    args = parser.parse_args(argv)
    root = args.agent_dir or agent_root()
    path = models_path(root)
    targets = resolved(args.window)
    plan = Plan()
    plan_budget(plan, path, targets, args.remove)
    if args.remove:
        plan.apply(False)
        print("context budget removed: owned contextWindow fields only; unrelated settings preserved")
        return 0
    if args.apply:
        plan.apply(False)
        print("context budget installed for " + ", ".join(sorted(targets))
              + f"; run --verify for native confirmation ({path})")
        return 0
    if args.verify:
        try:
            plan.apply(True, True)
        except ValueError as error:
            raise ValueError(f"installed context budget is missing or stale; re-apply ({error})") from error
        active, detail = native_verification(root, targets)
        if not active:
            raise ValueError(f"context budget BLOCKED: native verification failed ({detail})")
        print("context budget verified by the native model loader: " + detail)
        return 0
    plan.apply(True)
    print("context budget preflight ready (no writes): "
          + ", ".join(f"{target}={window}" for target, window in sorted(targets.items()))
          + f"; run --apply then --verify ({path})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        raise SystemExit(f"context budget: {error}") from error

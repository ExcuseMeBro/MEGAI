#!/usr/bin/env python3
"""Explicit opt-in compact token profile for Pi.

Caveman/Ponytail core adapters, RTK discovery guidance and the Headroom style
handoff are staged through the existing slim-wiring Plan (receipts and private
backups). The default is a read-only preflight; --apply, --remove and --verify
write only owned assets and preserve unrelated Pi configuration, credentials,
models, roles and every MEGAI marker.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from slim_wiring import Plan, SOURCE, digest, encoded, read

PROFILE = "max"
BEGIN = "<!-- megai:token-profile:begin -->"
END = "<!-- megai:token-profile:end -->"
SIDECAR = "megai-token-profile.json"
HEADROOM_ADAPTER = "extensions/megai-headroom/index.ts"
SKILLS = ("caveman", "ponytail")


def agent_root() -> Path:
    return Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi/agent"))


def profile_block(source: Path) -> str:
    bootstrap = source / "pi-skill/token-profile/bootstrap.md"
    if not bootstrap.is_file():
        raise ValueError(f"missing token profile bootstrap: {bootstrap}")
    return BEGIN + "\n" + bootstrap.read_text().rstrip() + "\n" + END + "\n"


def stage_marker(plan: Plan, root: Path, block: str, remove: bool) -> None:
    """Own one marker block; never claim unrelated AGENTS.md text."""
    path = root / "AGENTS.md"
    before = read(path)
    current = plan.changes.get(path, before) or b""
    text = current.decode()
    key = str(path) + "#token-profile"
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise ValueError(f"ambiguous token profile markers: {path}")
    if BEGIN in text:
        start = text.index(BEGIN)
        finish = text.index(END) + len(END)
        if finish < start:
            raise ValueError(f"reversed token profile markers: {path}")
        if text[finish:finish + 1] == "\n":
            finish += 1
        existing = text[start:finish]
        owned = plan.prior_receipt.get(key) == digest(existing.encode())
        if (remove or existing != block) and not owned:
            raise ValueError(f"custom token profile policy preserved: {path}")
        updated = text[:start] + ("" if remove else block) + text[finish:]
    else:
        updated = text if remove else text + ("\n" if text and not text.endswith("\n") else "") + block
    if updated != text:
        plan.stage(path, updated.encode(), before)
    if remove:
        plan.receipt.pop(key, None)
    else:
        plan.receipt[key] = digest(block.encode())
    # Follow the subagent-model policy pattern: refresh an already-owned whole-file
    # receipt, but never adopt user instructions this installer did not write.
    if plan.receipt.get(str(path)) == digest(current):
        plan.receipt[str(path)] = digest(updated.encode())


def stage_profile(plan: Plan, root: Path, source: Path, remove: bool = False) -> None:
    """Stage the max profile into an existing Plan without applying it.

    Staging only lets a single Plan transaction publish canonical source, the
    matching Headroom adapter, the cores and the sidecar together, so an adapter
    copy can never leave the sidecar active against an old extension.
    """
    stage_marker(plan, root, profile_block(source), remove)
    base = source / "pi-skill/token-profile"
    for skill in SKILLS:
        for name in ("SKILL.md", "LICENSE.md"):
            asset = base / skill / name
            if not asset.is_file():
                raise ValueError(f"missing token profile asset: {asset}")
            plan.asset(root / "skills" / skill / name, asset.read_bytes(), remove)
    plan.asset(root / SIDECAR, encoded({"schema": 1, "profile": PROFILE}), remove)


def stage_adapter(plan: Plan, root: Path, source: Path) -> None:
    """Stage the Headroom adapter that reads the sidecar; never stage it alone."""
    adapter = source / "pi-skill/headroom/index.ts"
    if not adapter.is_file():
        raise ValueError(f"missing Headroom adapter source: {adapter}")
    plan.asset(root / HEADROOM_ADAPTER, adapter.read_bytes(), False)


def rtk_binary() -> str | None:
    configured = os.environ.get("RTK_BIN", "").strip()
    return configured or shutil.which("rtk")


def profile_gaps(root: Path) -> list[str]:
    """Best-effort activation gaps. User filters are always preserved.

    Explicit positive skill paths are additive in Pi, so only exclusions that match
    an installed core are reported. The native Pi loader remains authoritative.
    """
    path = root / "settings.json"
    if not path.exists():
        return []
    try:
        settings = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        return [f"Pi settings are unreadable; skill activation was not checked: {path} ({error})"]
    if not isinstance(settings, dict):
        return [f"Pi settings must be a JSON object; skill activation was not checked: {path}"]
    patterns = settings.get("skills")
    if not isinstance(patterns, list):
        return []
    gaps = []
    for skill in SKILLS:
        skill_file = str(root / "skills" / skill / "SKILL.md")
        for pattern in patterns:
            if not isinstance(pattern, str) or not pattern.startswith(("!", "-")):
                continue
            target = pattern[1:]
            if fnmatch.fnmatch(skill_file, target) or skill_file == target.rstrip("/*"):
                gaps.append(f"settings.json excludes the local {skill} core: {pattern}")
                break
    return gaps


def rtk_preflight() -> tuple[bool, str]:
    """Read-only RTK check. Every RTK invocation keeps telemetry disabled."""
    binary = rtk_binary()
    if not binary:
        return False, "RTK not found; install RTK or set RTK_BIN before enabling the token profile"
    path = Path(binary)
    if not (path.is_file() and os.access(path, os.X_OK)):
        return False, f"RTK_BIN is not an executable file: {binary}"
    try:
        result = subprocess.run([str(path), "--version"], capture_output=True, text=True,
                                timeout=10, check=False,
                                env={**os.environ, "RTK_TELEMETRY_DISABLED": "1"})
    except (OSError, subprocess.SubprocessError) as error:
        return False, f"RTK preflight failed: {error}"
    if result.returncode != 0:
        return False, f"RTK preflight exited {result.returncode}: {result.stderr.strip()[:200]}"
    return True, result.stdout.strip() or "rtk"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="preflight only; never writes (default)")
    mode.add_argument("--apply", action="store_true", help="write owned profile assets")
    mode.add_argument("--remove", action="store_true", help="remove only owned profile assets")
    mode.add_argument("--verify", action="store_true",
                      help="fail if the installed profile is missing or stale")
    args = parser.parse_args(argv)
    root = agent_root()
    rtk_ok, rtk_detail = (True, "skipped") if args.remove else rtk_preflight()
    if args.apply and not rtk_ok:
        raise ValueError(rtk_detail)
    gaps = [] if args.remove else profile_gaps(root)
    plan = Plan()
    stage_profile(plan, root, SOURCE, args.remove)
    if not args.remove:
        stage_adapter(plan, root, SOURCE)
    if args.remove:
        plan.apply(False)
        print("token profile removed: owned assets only; unrelated Pi configuration preserved")
        return 0
    for gap in gaps:
        print(f"token profile activation gap (filters preserved): {gap}", file=sys.stderr)
    if args.apply:
        plan.apply(False)
        if gaps:
            print(f"token profile {PROFILE} installed-with-gap; not fully activated (rtk: {rtk_detail})")
        else:
            print(f"token profile {PROFILE} applied (rtk: {rtk_detail})")
        return 0
    blockers = list(gaps)
    if not rtk_ok:
        blockers.append(rtk_detail)
    if args.verify:
        try:
            plan.apply(True, True)
        except ValueError as error:
            raise ValueError(f"installed token profile is missing or stale; re-apply ({error})") from error
        if blockers:
            raise ValueError("token profile BLOCKED: " + "; ".join(blockers))
        print(f"token profile {PROFILE} verified (rtk: {rtk_detail})")
        return 0
    plan.apply(True)
    if blockers:
        print(f"token profile {PROFILE} preflight BLOCKED: " + "; ".join(blockers))
        return 1
    print(f"token profile {PROFILE} preflight ready; rtk: {rtk_detail}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        raise SystemExit(f"token profile: {error}") from error

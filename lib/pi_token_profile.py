#!/usr/bin/env python3
"""Explicit opt-in compact token profile for Pi.

Caveman core adapter, RTK discovery guidance and the Headroom style
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

from slim_wiring import MEGAI, Plan, SOURCE, digest, encoded, read

PROFILE = "max"
BEGIN = "<!-- megai:token-profile:begin -->"
END = "<!-- megai:token-profile:end -->"
SIDECAR = "megai-token-profile.json"
HEADROOM_ADAPTER = "extensions/megai-headroom/index.ts"
SKILLS = ("caveman",)


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
    plan.retire_tree(root / "skills/ponytail", False)
    base = source / "pi-skill/token-profile"
    for skill in SKILLS:
        for name in ("SKILL.md", "LICENSE.md"):
            asset = base / skill / name
            if not asset.is_file():
                raise ValueError(f"missing token profile asset: {asset}")
            target = root / "skills" / skill / name
            if remove:
                # retire() clears a missing receipt and blocks unowned user edits.
                plan.retire(target)
            else:
                plan.asset(target, asset.read_bytes(), False)
    if remove:
        plan.retire(root / SIDECAR)
    else:
        plan.asset(root / SIDECAR, encoded({"schema": 1, "profile": PROFILE}), False)


def stage_adapter(plan: Plan, root: Path, source: Path) -> None:
    """Stage the Headroom adapter that reads the sidecar; never stage it alone."""
    adapter = source / "pi-skill/headroom/index.ts"
    if not adapter.is_file():
        raise ValueError(f"missing Headroom adapter source: {adapter}")
    plan.asset(root / HEADROOM_ADAPTER, adapter.read_bytes(), False)


def rtk_binary() -> str | None:
    configured = os.environ.get("RTK_BIN", "").strip()
    return configured or shutil.which("rtk")


def rtk_env() -> dict[str, str]:
    """Minimal RTK environment: no provider, preload or interpreter overrides."""
    env = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "RTK_TELEMETRY_DISABLED": "1",
    }
    for key in ("XDG_CONFIG_HOME", "XDG_DATA_HOME"):
        value = os.environ.get(key, "").strip()
        if value:
            env[key] = value
    return env


def _relative_posix(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _native_pattern_match(path: Path, pattern: str, base: Path) -> bool:
    """Mirror native Pi matchesAnyPattern for an auto-discovered resource."""
    normalized = pattern.replace("\\", "/")
    candidates = [_relative_posix(path, base), path.name, path.as_posix()]
    if path.name == "SKILL.md":
        parent = path.parent
        candidates += [_relative_posix(parent, base), parent.name, parent.as_posix()]
    return any(fnmatch.fnmatchcase(candidate, normalized) for candidate in candidates)


def _native_exact_match(path: Path, pattern: str, base: Path) -> bool:
    """Mirror native Pi matchesAnyExactPattern (`+`/`-` force overrides)."""
    normalized = pattern.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized in (_relative_posix(path, base), path.as_posix()):
        return True
    if path.name == "SKILL.md":
        parent = path.parent
        return normalized in (_relative_posix(parent, base), parent.as_posix())
    return False


def _native_enabled(path: Path, patterns: list, base: Path) -> bool:
    """Mirror native Pi isEnabledByOverrides, including `!`/`+`/`-` order."""
    overrides = [item for item in patterns if isinstance(item, str) and item[:1] in ("!", "+", "-")]
    excludes = [item[1:] for item in overrides if item.startswith("!")]
    force_includes = [item[1:] for item in overrides if item.startswith("+")]
    force_excludes = [item[1:] for item in overrides if item.startswith("-")]
    enabled = True
    if excludes and any(_native_pattern_match(path, item, base) for item in excludes):
        enabled = False
    if force_includes and any(_native_exact_match(path, item, base) for item in force_includes):
        enabled = True
    if force_excludes and any(_native_exact_match(path, item, base) for item in force_excludes):
        enabled = False
    return enabled


def profile_gaps(root: Path) -> list[str]:
    """Best-effort activation gaps mirroring native Pi override semantics.

    Plain positive paths are additive in Pi, so only `!`/`+`/`-` overrides are
    considered, in native order. The native loader stays authoritative and
    `--verify` runs it directly. Filters are never rewritten.
    """
    path = root / "settings.json"
    if not path.exists():
        return []
    try:
        settings = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        return [f"Pi settings are unreadable; activation was not checked: {path} ({error})"]
    if not isinstance(settings, dict):
        return [f"Pi settings must be a JSON object; activation was not checked: {path}"]
    gaps = []
    skills = settings.get("skills", [])
    if isinstance(skills, list):
        for skill in SKILLS:
            if not _native_enabled(root / "skills" / skill / "SKILL.md", skills, root):
                gaps.append(f"settings.json disables the local {skill} core")
    elif skills is not None:
        gaps.append(f"settings.json skills must be a list; activation was not checked: {path}")
    extensions = settings.get("extensions", [])
    if isinstance(extensions, list):
        adapter = root / HEADROOM_ADAPTER
        if adapter.exists() and not _native_enabled(adapter, extensions, root):
            gaps.append("settings.json disables the Headroom extension")
    elif extensions is not None:
        gaps.append(f"settings.json extensions must be a list; activation was not checked: {path}")
    return gaps


def native_activation(root: Path) -> tuple[bool, str]:
    """Run the existing native Pi activation verifier offline; no provider calls.

    Node loads user extensions, so it gets an explicit minimal environment instead
    of the caller's: no provider credentials, preload or interpreter overrides.
    """
    node = shutil.which("node")
    if not node:
        return False, "node is unavailable; native activation was not verified"
    verifier = SOURCE / "lib/verify_headroom_activation.mjs"
    if not verifier.is_file():
        return False, f"native activation verifier missing: {verifier}"
    command = [node, str(verifier)]
    pi = shutil.which("pi")
    if pi:
        command.append(pi)
    env = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "MEGAI_HOME": str(MEGAI),
        "PI_CODING_AGENT_DIR": str(root),
        "PI_OFFLINE": "1",
    }
    package_root = os.environ.get("PI_PACKAGE_ROOT", "").strip()
    if package_root:
        env["PI_PACKAGE_ROOT"] = package_root
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60,
                                check=False, env=env)
    except (OSError, subprocess.SubprocessError) as error:
        return False, f"native activation verifier failed: {error}"
    if result.returncode == 0:
        return True, (result.stdout or "").strip() or "native activation verified"
    output = (result.stderr or "").strip() or (result.stdout or "").strip()
    return False, output.splitlines()[-1] if output else f"native activation exited {result.returncode}"


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
                                timeout=10, check=False, env=rtk_env())
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
            print(f"token profile {PROFILE} installed (rtk: {rtk_detail}); run --verify for native activation")
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
        active, detail = native_activation(root)
        if not active:
            raise ValueError(f"token profile BLOCKED: native activation not verified ({detail})")
        print(f"token profile {PROFILE} verified by fresh native activation (rtk: {rtk_detail})")
        return 0
    plan.apply(True)
    if blockers:
        print(f"token profile {PROFILE} preflight BLOCKED: " + "; ".join(blockers))
        return 1
    print(f"token profile {PROFILE} preflight ready (best-effort; run --verify for native activation); rtk: {rtk_detail}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        raise SystemExit(f"token profile: {error}") from error

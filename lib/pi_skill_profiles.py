#!/usr/bin/env python3
"""Read-only native skill-profile snippets for Pi (opt-in; never writes).

A profile is the exact set of native `settings.json` `skills` exclusion patterns
that narrow known optional global design/mobile skills for one kind of work.
Global `!name` patterns narrow only auto-discovered user skill directories
(``~/.pi/agent/skills`` and ``~/.agents/skills``); project selections and
package filters keep their own rules, so trusted project resources are honored.
Core, safety and accessibility (a11y) skills are never listed here, and this
tool only prints a snippet to merge by hand: it never edits global configuration.

Adopting a profile by hand:

1. Snapshot ``settings.json`` privately (copy the file) before editing it.
2. Append only the profile exclusions that are not already present (see
   ``missing_exclusions``), keeping existing entries, their order, and every
   unrelated setting unchanged.
3. Record which entries were newly added.

Restoring: remove only those newly added entries. Never delete a pre-existing
identical ``!name`` the user already owned. Force one narrowed skill back with
``+<path>``.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

# Reviewed optional skills only. Never add a core/safety/a11y name here.
OPTIONAL_DESIGN = frozenset({
    "apply-aesthetic", "brandkit", "design-code", "design-component",
    "design-qa", "design-review", "design-tokens", "figma-integration",
    "governance", "image-to-code", "migrate-design-system", "redesign",
    "token-build", "ux-ui-prototype", "ux-writing",
})
OPTIONAL_MOBILE = frozenset({"appllama-app-design-skill"})

# Informational guard: these must never appear in a profile exclusion set.
PROTECTED = frozenset({
    "a11y-audit", "agent-worktree-lifecycle", "caveman", "code-review",
    "codebase-design", "diagnosing-bugs", "domain-modeling", "git-guardrails-claude-code",
    "grilling", "megai", "megai-acceptance", "megai-task-flow", "prototype",
    "research", "resolving-merge-conflicts", "tdd", "verify-and-stop",
    "writing-for-agents",
})

PROFILES: dict[str, tuple[str, ...]] = {
    "coding": tuple(sorted(OPTIONAL_DESIGN | OPTIONAL_MOBILE)),
    "design": tuple(sorted(OPTIONAL_MOBILE)),
    "mobile": tuple(sorted(OPTIONAL_DESIGN)),
}


def _validate() -> None:
    known = OPTIONAL_DESIGN | OPTIONAL_MOBILE
    for name, excluded in PROFILES.items():
        unknown = set(excluded) - known
        conflicts = set(excluded) & PROTECTED
        if unknown or conflicts:
            raise ValueError(f"invalid skill profile {name}: unknown={sorted(unknown)} protected={sorted(conflicts)}")


_validate()


def snippet(profile: str) -> list[str]:
    """Return the deterministic native exclusion patterns for a profile."""
    if profile not in PROFILES:
        raise ValueError(f"unknown skill profile: {profile} (have: {', '.join(sorted(PROFILES))})")
    return [f"!{name}" for name in PROFILES[profile]]


def missing_exclusions(profile: str, existing: list[str]) -> list[str]:
    """Profile exclusions not already present verbatim in ``existing``.

    Returns them in profile order so a by-hand merge can append only the new
    entries, keep the user's existing entries/order, and later remove only these.
    """
    if profile not in PROFILES:
        raise ValueError(f"unknown skill profile: {profile} (have: {', '.join(sorted(PROFILES))})")
    present = {item for item in existing if isinstance(item, str)}
    return [pattern for pattern in snippet(profile) if pattern not in present]


def explain(profile: str) -> str:
    if profile not in PROFILES:
        raise ValueError(f"unknown skill profile: {profile} (have: {', '.join(sorted(PROFILES))})")
    names = ", ".join(PROFILES[profile])
    return (
        f"Pi skill profile '{profile}' narrows these optional skills: {names}.\n"
        "Merge by hand; nothing is applied globally. Snapshot settings.json privately,\n"
        "then append only missing exclusions, preserving existing entries, their order\n"
        "and unrelated settings, and record which entries you added.\n"
        "Only auto-discovered user skills are narrowed; core, safety and accessibility (a11y)\n"
        "skills are never excluded, and project/package selections keep their own rules.\n"
        "Restore by removing only the entries you added, never a pre-existing identical\n"
        "'!name'. Force one back with '+<path>'."
    )


def default_skills_dirs() -> list[Path]:
    root = os.environ.get("PI_CODING_AGENT_DIR", str(Path.home() / ".pi/agent"))
    return [Path(root) / "skills", Path.home() / ".agents/skills"]


def scan_installed(profile: str, dirs: list[Path] | None = None) -> list[str]:
    """Read-only: which installed skill directories a profile would narrow."""
    excluded = set(PROFILES[profile]) if profile in PROFILES else None
    if excluded is None:
        raise ValueError(f"unknown skill profile: {profile} (have: {', '.join(sorted(PROFILES))})")
    matched: set[str] = set()
    for base in (dirs if dirs is not None else default_skills_dirs()):
        if not base.is_dir():
            continue
        for skill in base.rglob("SKILL.md"):
            if skill.parent.name in excluded:
                matched.add(skill.parent.name)
    return sorted(matched)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("profiles", help="list available profiles")
    for name in ("snippet", "explain", "scan"):
        command = sub.add_parser(name)
        command.add_argument("profile")
        if name == "scan":
            command.add_argument("--skills-dir", action="append", default=[],
                                 help="skill directory to inspect (repeatable; read-only)")
    args = parser.parse_args(argv)
    if args.command == "profiles":
        print(" ".join(sorted(PROFILES)))
        return 0
    if args.profile not in PROFILES:
        raise ValueError(f"unknown skill profile: {args.profile} (have: {', '.join(sorted(PROFILES))})")
    if args.command == "snippet":
        print(json.dumps({"skills": snippet(args.profile)}))
    elif args.command == "explain":
        print(explain(args.profile))
    else:
        dirs = [Path(item) for item in args.skills_dir] or None
        print(json.dumps({"profile": args.profile, "matched": scan_installed(args.profile, dirs)}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        raise SystemExit(f"pi skill profiles: {error}") from error

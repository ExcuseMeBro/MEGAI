#!/usr/bin/env python3
"""Install the task-resource helper and sync its policy block to agent configs."""
import stat
import sys
from pathlib import Path

BEGIN = "<!-- megai:task-resources:begin -->"
END = "<!-- megai:task-resources:end -->"
HELPER = Path(__file__).with_name("task_resources.py")
POLICY = Path(__file__).resolve().parents[1] / "docs/task-resources-policy.md"
TARGETS = (".pi/agent/AGENTS.md", ".codex/AGENTS.md", ".claude/CLAUDE.md")
REPO_TARGETS = Path(__file__).resolve().parents[1]


class Refused(RuntimeError):
    pass


def policy_block(policy_path=POLICY):
    text = Path(policy_path).read_text().strip()
    if not (text.startswith(BEGIN) and text.endswith(END)):
        raise Refused(f"{policy_path} must start with {BEGIN} and end with {END}")
    return text


def sync_block(target, block):
    """Replace (or append) the marked block; return True when bytes changed."""
    path = Path(target)
    original = path.read_text() if path.exists() else ""
    start = original.find(BEGIN)
    end = original.find(END)
    if start == -1 and end == -1:
        updated = original + ("" if original.endswith("\n") or not original else "\n") + block + "\n"
    elif start == -1 or end == -1 or end < start:
        raise Refused(f"Malformed {BEGIN}/{END} markers in {path}")
    else:
        updated = original[:start] + block + original[end + len(END):]
    if updated == original:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated)
    return True


def install(home=None, repo=None):
    home = Path(home or Path.home())
    repo = Path(repo or REPO_TARGETS)
    block = policy_block(repo / "docs/task-resources-policy.md")
    installed = home / ".local/bin/megai-task-resources"
    installed.parent.mkdir(parents=True, exist_ok=True)
    installed.write_bytes(HELPER.read_bytes())
    installed.chmod(installed.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    changed = [str(installed)]
    for target in (repo / "pi-defaults/AGENTS.md", *(home / name for name in TARGETS)):
        if sync_block(target, block):
            changed.append(str(target))
    return changed


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        changed = install(home=argv[0] if argv else None, repo=argv[1] if len(argv) > 1 else None)
    except (Refused, OSError) as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 2
    for path in changed:
        print(f"updated {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

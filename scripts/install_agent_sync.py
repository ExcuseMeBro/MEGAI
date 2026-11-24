#!/usr/bin/env python3
"""Install megai-agent-sync and its hook, then optionally run the sync.

    python3 scripts/install_agent_sync.py          # install only
    python3 scripts/install_agent_sync.py --sync   # install, then run megai-agent-sync

Installs `scripts/agent_sync.py` as `~/.local/bin/megai-agent-sync` and
`scripts/agent-hooks/test-guard.mjs` into `~/.local/share/megai-agent-hooks/`.
"""
import os
import stat
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
FILES = (
    (SCRIPTS / "agent_sync.py", ".local/bin/megai-agent-sync", True),
    (SCRIPTS / "agent-hooks/test-guard.mjs", ".local/share/megai-agent-hooks/test-guard.mjs", False),
)


def install(home=None):
    home = Path(home or Path.home())
    changed = []
    for src, rel, executable in FILES:
        dst = home / rel
        data = src.read_bytes()
        if dst.is_file() and dst.read_bytes() == data:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(dst.name + ".install.tmp")
        tmp.write_bytes(data)
        if executable:
            tmp.chmod(tmp.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        os.replace(tmp, dst)
        changed.append(str(dst))
    return changed


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    sync = "--sync" in argv
    rest = [a for a in argv if a != "--sync"]
    home = Path(rest[0]) if rest else Path.home()
    try:
        changed = install(home)
    except OSError as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 2
    for path in changed:
        print(f"updated {path}")
    if not changed:
        print("megai-agent-sync already installed")
    if sync:
        return subprocess.run([sys.executable, str(home / ".local/bin/megai-agent-sync")], check=False).returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())

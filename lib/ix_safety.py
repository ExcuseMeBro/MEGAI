#!/usr/bin/env python3
"""Reapply narrow, version-shape-checked Ix safety fixes after upstream installs."""
import os
from pathlib import Path
import shutil
import stat
import tempfile

WORKSPACE_BEFORE = '''def find_workspace_root(cwd: str | None) -> Path:
    start = Path(cwd or os.getcwd()).resolve()
    for candidate in (start, *start.parents):
        if (candidate / ".codex" / "hooks.json").exists():
            return candidate
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return start
'''
WORKSPACE_AFTER = '''def find_workspace_root(cwd: str | None) -> Path:
    start = Path(cwd or os.getcwd()).resolve()
    # MEGAI: a global home/.codex/hooks.json must not shadow project Git roots.
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    for candidate in (start, *start.parents):
        if (candidate / ".codex" / "hooks.json").exists():
            return candidate
    return start
'''
LAUNCH_BEFORE = 'exec node "$SCRIPT_DIR/cli/dist/cli/main.js" "$@"\n'
LAUNCH_AFTER = '''# MEGAI: Stop hooks issue bare "ix map"; never scan home or / implicitly.
if [ "$#" -eq 1 ] && [ "$1" = "map" ]; then
    _ix_root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
        printf '%s\\n' 'ix: refusing unscoped map outside Git; specify a project/file path' >&2
        exit 64
    }
    _ix_home="$(cd "${HOME:-/}" 2>/dev/null && pwd -P)"
    if [ "$_ix_root" = / ] || [ "$_ix_root" = "$_ix_home" ]; then
        printf '%s\\n' 'ix: refusing implicit root/home map; specify a narrower project/file path' >&2
        exit 64
    fi
fi
exec node "$SCRIPT_DIR/cli/dist/cli/main.js" "$@"
'''


def patch_file(path, before, after, backups):
    """Preserve unknown/user-edited versions and symlinks; never patch heuristically."""
    if path.is_symlink():
        return 'unsupported symlink'
    if not path.exists():
        return 'not installed'
    content = path.read_text()
    if after in content:
        return 'already guarded'
    if content.count(before) != 1:
        return 'unsupported content'
    backups.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, backup = tempfile.mkstemp(prefix=path.name + '.', suffix='.bak', dir=backups)
    os.close(fd)
    shutil.copyfile(path, backup)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(content.replace(before, after, 1))
        os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return 'guarded'


def main():
    home = Path.home()
    ix = Path(os.environ.get('IX_HOME', home / '.ix'))
    megai = Path(os.environ.get('MEGAI_HOME', home / '.megai'))
    targets = [
        (ix / 'cli/ix', LAUNCH_BEFORE, LAUNCH_AFTER),
        (home / '.codex/hooks/common.py', WORKSPACE_BEFORE, WORKSPACE_AFTER),
        (ix / 'codex-plugin-source/.codex/hooks/common.py', WORKSPACE_BEFORE, WORKSPACE_AFTER),
    ]
    unsupported = False
    for path, before, after in targets:
        result = patch_file(path, before, after, megai / 'backups/ix-safety')
        print(f'Ix safety: {result}: {path}')
        unsupported |= result.startswith('unsupported')
    return int(unsupported)


if __name__ == '__main__':
    raise SystemExit(main())

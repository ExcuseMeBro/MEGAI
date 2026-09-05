#!/usr/bin/env python3
"""Explicit legacy Ix detachment. Preview by default; never delete runtime data.

Requires Python 3.11+. Does not run downloaded installers, Docker or plugin CLIs.
Unknown/custom registrations are preserved for manual review.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import tomllib

PLUGIN = 'ix-memory@ix-codex-plugin'
CLAUDE_PLUGIN = 'ix-memory@ix-claude-plugin'
HOOK_FILES = ('session_start', 'user_prompt_submit', 'pre_tool_use', 'post_tool_use', 'stop')
# Exact shipped content at MEGAI 2a616ee, not headers user edits might retain.
LEGACY_HASHES = {
    'install_ix.sh': '2f565289411936301e7d763a20450e8ed39290835e68bd4059126c7aca960dbd',
    'ix_safety.py': 'f49ae57d8da7b8ba4d2707cc5831a544e8d2745015ddfbafba30c4bdaaed23a0',
}


def hook_command(name):
    script = f'.codex/hooks/{name}.py'
    return (f'/bin/sh -lc \'d="$PWD"; while [ "$d" != "/" ]; do '
            f'if [ -f "$d/{script}" ]; then exec python3 "$d/{script}"; fi; '
            f'd=$(dirname "$d"); done; if [ -f "$HOME/{script}" ]; then '
            f'exec python3 "$HOME/{script}"; fi; exit 0\'')


def detach_hooks(data):
    commands = {hook_command(name) for name in HOOK_FILES}
    hooks = data.get('hooks', {})
    if not isinstance(hooks, dict):
        raise ValueError('hooks must be an object')
    for event, groups in list(hooks.items()):
        if not isinstance(groups, list):
            raise ValueError('hook event must be an array')
        kept_groups = []
        for group in groups:
            entries = group.get('hooks', [])
            if not isinstance(entries, list) or not all(isinstance(h, dict) for h in entries):
                raise ValueError('hook group must contain an array of objects')
            kept = [h for h in entries if not (
                h.get('type') == 'command' and h.get('command') in commands
                and 'commandWindows' not in h)]
            if kept == entries:
                kept_groups.append(group)
            elif kept:
                kept_groups.append({**group, 'hooks': kept})
        if kept_groups:
            hooks[event] = kept_groups
        elif groups:
            del hooks[event]


def table_path(header):
    """Parse quoted TOML table names, not substring-match headers."""
    data = tomllib.loads(header)
    keys = []
    while isinstance(data, dict) and len(data) == 1:
        key, data = next(iter(data.items()))
        keys.append(key)
    return tuple(keys)


def detach_toml(text, home):
    original = tomllib.loads(text)
    expected = copy.deepcopy(original)
    targets = []
    entry = expected.get('mcp_servers', {}).get('ix-memory')
    if entry is not None:
        if (entry.get('command') in ('python3', sys.executable)
                and entry.get('args') == [str(home / '.codex/mcp/server.py')]):
            del expected['mcp_servers']['ix-memory']
            targets.append(('mcp_servers', 'ix-memory'))
        else:
            print('Preserved custom Codex ix-memory MCP; inspect manually.', file=sys.stderr)
    if PLUGIN in expected.get('plugins', {}):
        del expected['plugins'][PLUGIN]
        targets.append(('plugins', PLUGIN))
    if not targets:
        return text
    out = []
    skip = False
    for line in text.splitlines(keepends=True):
        if re.match(r'^\s*\[', line):
            try:
                path = table_path(line)
                skip = any(path[:len(target)] == target for target in targets)
            except tomllib.TOMLDecodeError:
                # May be content inside a multiline value. Semantic comparison
                # below refuses an edit if unrelated values would change.
                pass
        if not skip:
            out.append(line)
    result = ''.join(out)
    actual = tomllib.loads(result)
    # Removing the last subtable can also remove its implicit empty parent.
    for key in ('mcp_servers', 'plugins'):
        if expected.get(key) == {} and key not in actual:
            del expected[key]
    if actual != expected:
        raise ValueError('unsupported TOML layout; no configuration changed')
    return result


def build_plan(home, megai):
    plan = []

    def read(path):
        # Do not follow a config or parent-directory symlink into another owner.
        for parent in (path, *path.parents):
            if parent.is_symlink():
                raise ValueError(f'refusing symlink: {parent}')
        if not path.exists():
            return None
        if not path.is_file():
            raise ValueError(f'not a regular file: {path}')
        return path.read_bytes()

    configs = [home / '.codex/hooks.json', home / '.claude/settings.json',
               home / '.claude/plugins/installed_plugins.json',
               home / '.claude/plugins/known_marketplaces.json', megai / 'state.json',
               home / '.agents/plugins/marketplace.json']
    for path in configs:
        raw = read(path)
        if raw is None:
            continue
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError(f'expected JSON object: {path}')
        before = copy.deepcopy(data)
        if path == configs[0]:
            detach_hooks(data)
        elif path == configs[1]:
            for field, key in (('enabledPlugins', CLAUDE_PLUGIN),
                               ('extraKnownMarketplaces', 'ix-claude-plugin')):
                data.get(field, {}).pop(key, None)
        elif path == configs[2]:
            data.get('plugins', {}).pop(CLAUDE_PLUGIN, None)
        elif path == configs[3]:
            data.pop('ix-claude-plugin', None)
        elif path == configs[4]:
            data.get('tools', {}).pop('ix', None)
        else:
            plugins = data.get('plugins', [])
            if not isinstance(plugins, list) or not all(isinstance(p, dict) for p in plugins):
                raise ValueError('marketplace plugins must be an array of objects')
            kept = [p for p in plugins if not (
                p.get('name') == 'ix-memory' and p.get('source') == {
                    'source': 'local', 'path': './.codex/plugins/ix-memory'})]
            if any(p.get('name') == 'ix-memory' for p in kept):
                print('Preserved custom Ix marketplace entry; inspect manually.', file=sys.stderr)
            if kept != plugins:
                data['plugins'] = kept
        if data != before:
            plan.append((path, raw, (json.dumps(data, indent=2) + '\n').encode()))

    path = home / '.codex/config.toml'
    raw = read(path)
    if raw is not None:
        updated = detach_toml(raw.decode(), home).encode()
        if updated != raw:
            plan.append((path, raw, updated))

    # Only obsolete MEGAI installer artifacts with exact known content.
    for name, digest in LEGACY_HASHES.items():
        path = megai / 'lib' / name
        raw = read(path)
        if raw is not None:
            if hashlib.sha256(raw).hexdigest() == digest:
                plan.append((path, raw, None))
            else:
                print(f'Preserved unrecognized legacy file: {path}', file=sys.stderr)
    # MEGAI created this symlink; never delete a replacement executable.
    path = megai / 'bin/ix'
    for parent in path.parents:
        if parent.is_symlink():
            raise ValueError(f'refusing symlink: {parent}')
    if path.is_symlink():
        if os.readlink(path) == str(home / '.local/bin/ix'):
            plan.append((path, os.readlink(path), None))
        else:
            print(f'Preserved custom symlink: {path}', file=sys.stderr)
    elif path.exists():
        print(f'Preserved custom executable: {path}', file=sys.stderr)
    return plan


def apply_plan(plan, megai):
    if not plan:
        return
    backup_root = megai / 'backups/ix-retirement'
    for parent in (backup_root, *backup_root.parents):
        if parent.is_symlink():
            raise ValueError(f'refusing symlink: {parent}')
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup = Path(tempfile.mkdtemp(prefix='run-', dir=backup_root))
    manifest = []
    def unchanged(path, raw):
        if isinstance(raw, str):
            valid = path.is_symlink() and os.readlink(path) == raw
        else:
            valid = not path.is_symlink() and path.read_bytes() == raw
        if not valid:
            raise ValueError(f'file changed after preflight: {path}')

    # Snapshot every original before changing any file. Backups may hold secrets.
    for index, (path, raw, updated) in enumerate(plan):
        unchanged(path, raw)
        dest = backup / str(index)
        shutil.copy2(path, dest, follow_symlinks=False)
        if not dest.is_symlink():
            dest.chmod(0o600)
        manifest.append({'path': str(path), 'backup': str(dest),
                         'action': 'remove' if updated is None else 'update'})
    (backup / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Backup: {backup}')
    for path, raw, updated in plan:
        unchanged(path, raw)
        if updated is None:
            path.unlink()
            continue
        fd, tmp = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as output:
                output.write(updated)
                output.flush()
                os.fsync(output.fileno())
            os.chmod(tmp, stat.S_IMODE(path.stat().st_mode))
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='back up and apply the previewed retirement')
    args = parser.parse_args()
    home = Path(os.environ['HOME']).absolute()
    megai = Path(os.environ.get('MEGAI_HOME', home / '.megai')).absolute()
    try:
        plan = build_plan(home, megai)
        for path, _, updated in plan:
            print(f'{"Remove" if updated is None else "Update"}: {path}')
        if args.apply:
            apply_plan(plan, megai)
        print(f'{len(plan)} change(s){" applied" if args.apply else " planned (use --apply)"}.')
        print('Runtime/plugin files, custom hooks, other projects and Docker data are not removed; see README retirement steps.')
    except (OSError, ValueError, TypeError, AttributeError) as error:
        print(f'Retirement failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

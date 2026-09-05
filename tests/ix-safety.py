#!/usr/bin/env python3
"""Exercise actual hook-function/shim shapes without launching the Ix backend."""
import ast
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ix_safety', ROOT / 'lib/ix_safety.py')
safety = importlib.util.module_from_spec(spec)
spec.loader.exec_module(safety)


def workspace_function(source):
    tree = ast.parse(source)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'find_workspace_root')
    namespace = {'Path': Path, 'os': os}
    exec(compile(ast.Module(body=[function], type_ignores=[]), 'ix-common.py', 'exec'), namespace)
    return namespace['find_workspace_root']


with tempfile.TemporaryDirectory() as temporary:
    base = Path(temporary).resolve()
    home = base / 'home'
    repo = home / 'project with spaces'
    (home / '.codex').mkdir(parents=True)
    (home / '.codex/hooks.json').write_text('{}')
    repo.mkdir()
    subprocess.run(['git', 'init', '-q', str(repo)], check=True, env={**os.environ, 'HOME': str(home)})
    nested = repo / 'src'
    nested.mkdir()
    common = base / 'common.py'
    common.write_text(safety.WORKSPACE_BEFORE + '\n# unrelated user text\n')
    assert workspace_function(common.read_text())(str(nested)) == home, 'baseline must reproduce wrong root'
    backups = base / 'backups'
    assert safety.patch_file(common, safety.WORKSPACE_BEFORE, safety.WORKSPACE_AFTER, backups) == 'guarded'
    assert workspace_function(common.read_text())(str(nested)) == repo
    assert '# unrelated user text' in common.read_text()
    worktree = home / 'worktree'
    worktree.mkdir()
    (worktree / '.git').write_text('gitdir: /not-used-by-this-root-lookup')
    assert workspace_function(common.read_text())(str(worktree)) == worktree
    plain = base / 'plain'
    plain.mkdir()
    assert workspace_function(common.read_text())(str(plain)) == plain

    fake_bin = base / 'bin'
    fake_bin.mkdir()
    calls = base / 'node.args'
    node = fake_bin / 'node'
    node.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$NODE_CALLS"\n')
    node.chmod(0o755)
    launcher = base / 'ix'
    launcher.write_text('#!/bin/sh\nSCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"\n' + safety.LAUNCH_BEFORE)
    launcher.chmod(0o755)
    env = {**os.environ, 'HOME': str(home), 'PATH': str(fake_bin) + ':/usr/bin:/bin', 'NODE_CALLS': str(calls)}

    def run(cwd, args, expected):
        calls.unlink(missing_ok=True)
        result = subprocess.run([str(launcher), *args], cwd=cwd, env=env, text=True, capture_output=True)
        assert result.returncode == expected, (cwd, args, result.returncode, result.stderr)
        assert calls.exists() == (expected == 0), 'unsafe scope must stop before Node starts'
        return calls.read_text().splitlines() if calls.exists() else []

    run(home, ['map'], 0)  # reproduces original unsafe launch, with a fake Node
    assert safety.patch_file(launcher, safety.LAUNCH_BEFORE, safety.LAUNCH_AFTER, backups) == 'guarded'
    run(home, ['map'], 64)
    run(Path('/'), ['map'], 64)
    run(plain, ['map'], 64)
    run(repo, ['map'], 0)
    run(nested, ['map'], 0)
    explicit = str(repo / 'file with spaces.ts')
    assert run(home, ['map', explicit], 0)[1:] == ['map', explicit]
    assert run(home, ['--version'], 0)[1:] == ['--version']
    subprocess.run(['git', 'init', '-q', str(home)], check=True, env=env)
    run(home, ['map'], 64)  # a dotfiles Git repo is still too broad for implicit refresh

    count = len(list(backups.iterdir()))
    assert safety.patch_file(launcher, safety.LAUNCH_BEFORE, safety.LAUNCH_AFTER, backups) == 'already guarded'
    assert len(list(backups.iterdir())) == count
    assert launcher.stat().st_mode & 0o777 == 0o755
    custom = base / 'custom.py'
    custom.write_text('user-owned unfamiliar code\n')
    assert safety.patch_file(custom, safety.WORKSPACE_BEFORE, safety.WORKSPACE_AFTER, backups) == 'unsupported content'
    assert custom.read_text() == 'user-owned unfamiliar code\n'
    link = base / 'linked-launcher'
    link.symlink_to(launcher)
    assert safety.patch_file(link, safety.LAUNCH_BEFORE, safety.LAUNCH_AFTER, backups) == 'unsupported symlink'

print('Ix safety: red/green root resolution, pre-Node scope rejection, valid calls, backups/idempotence/preservation PASS')

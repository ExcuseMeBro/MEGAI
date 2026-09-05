#!/usr/bin/env python3
"""Offline retirement/ownership regressions; never touch the real HOME or Docker."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'lib/retire_ix.py'
STOP = '/bin/sh -lc \'d="$PWD"; while [ "$d" != "/" ]; do if [ -f "$d/.codex/hooks/stop.py" ]; then exec python3 "$d/.codex/hooks/stop.py"; fi; d=$(dirname "$d"); done; if [ -f "$HOME/.codex/hooks/stop.py" ]; then exec python3 "$HOME/.codex/hooks/stop.py"; fi; exit 0\''
KEEP = {'type': 'command', 'command': 'paseo hooks codex Stop'}


class Retirement(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve() / 'home'
        self.megai = self.home / '.megai'
        self.env = {**os.environ, 'HOME': str(self.home), 'MEGAI_HOME': str(self.megai)}
        self.put('.codex/hooks.json', json.dumps({'hooks': {
            'Stop': [{'matcher': '', 'hooks': [KEEP, {'type': 'command', 'command': STOP}]}],
            'SessionStart': [{'hooks': [{'command': 'custom ix command'}]}],
            'Empty': []}}))
        self.put('.codex/config.toml', f'''# Preserve user comment
model = "keep"
[mcp_servers.keep]
command = "keep"
[mcp_servers."ix-memory"]
command = "python3"
args = [{json.dumps(str(self.home / '.codex/mcp/server.py'))}]
[mcp_servers."ix-memory".env]
IX_ONLY = "1"
[plugins."ix-memory@ix-codex-plugin"]
enabled = true
[plugins.other]
enabled = true
''')
        self.put('.claude/settings.json', json.dumps({
            'hooks': {'Stop': [{'hooks': [KEEP]}]},
            'enabledPlugins': {'ix-memory@ix-claude-plugin': True, 'keep': True},
            'extraKnownMarketplaces': {'ix-claude-plugin': {'source': 'ix'}, 'keep': {}}}))
        self.put('.claude/plugins/installed_plugins.json', json.dumps({
            'version': 2, 'plugins': {'ix-memory@ix-claude-plugin': [], 'keep': []}}))
        self.put('.claude/plugins/known_marketplaces.json', '{"ix-claude-plugin":{},"keep":{}}')
        self.put('.agents/plugins/marketplace.json', json.dumps({'name': 'mixed', 'plugins': [
            {'name': 'ix-memory', 'source': {'source': 'local', 'path': './.codex/plugins/ix-memory'}},
            {'name': 'keep', 'source': {'path': 'user-owned'}}]}))
        self.put('.megai/state.json', '{"tools":{"ix":{},"codedb":{"bin":"codedb"},"zvec-grep":{"bin":"zg"}},"projects":{"keep":{}}}')
        self.put('.megai/lib/install_ix.sh', '# Ix — persistent codebase map and system-memory CLI.\n')
        self.put('.megai/lib/ix_safety.py', '# Reapply narrow, version-shape-checked Ix safety fixes\n')
        self.put('.local/bin/ix', '#!/bin/sh\nexec ~/.ix/cli/ix "$@"\n')
        self.put('.ix/data', 'graph data must remain')
        self.put('.megai/bin/keep', 'unchanged')
        (self.megai / 'bin/ix').symlink_to(self.home / '.local/bin/ix')

    def put(self, path, text):
        target = self.home / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        return target

    def run_helper(self, apply=True, success=True):
        result = subprocess.run([sys.executable, str(HELPER), *(['--apply'] if apply else [])],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0 if success else 1, result.stdout + result.stderr)
        return result

    def snapshot(self):
        return {str(p.relative_to(self.home)): ('link:' + os.readlink(p) if p.is_symlink() else p.read_bytes())
                for p in self.home.rglob('*') if p.is_file() or p.is_symlink()}

    def test_preview_apply_preservation_backup_retry(self):
        before = self.snapshot()
        self.run_helper(apply=False)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.megai / 'backups').exists())
        config = self.home / '.codex/config.toml'
        config.chmod(0o600)
        self.run_helper()
        hooks = json.loads((self.home / '.codex/hooks.json').read_text())['hooks']
        self.assertEqual(hooks['Stop'], [{'matcher': '', 'hooks': [KEEP]}])
        self.assertEqual(hooks['SessionStart'], [{'hooks': [{'command': 'custom ix command'}]}])
        self.assertEqual(hooks['Empty'], [])
        data = tomllib.loads(config.read_text())
        self.assertEqual(data, {'model': 'keep', 'mcp_servers': {'keep': {'command': 'keep'}},
                                'plugins': {'other': {'enabled': True}}})
        self.assertTrue(config.read_text().startswith('# Preserve user comment'))
        self.assertEqual(stat.S_IMODE(config.stat().st_mode), 0o600)
        claude = json.loads((self.home / '.claude/settings.json').read_text())
        self.assertEqual(claude['enabledPlugins'], {'keep': True})
        self.assertEqual(claude['extraKnownMarketplaces'], {'keep': {}})
        self.assertEqual(claude['hooks'], {'Stop': [{'hooks': [KEEP]}]})
        marketplace = json.loads((self.home / '.agents/plugins/marketplace.json').read_text())
        self.assertEqual(marketplace, {'name': 'mixed', 'plugins': [{'name': 'keep', 'source': {'path': 'user-owned'}}]})
        state = json.loads((self.megai / 'state.json').read_text())
        self.assertEqual(set(state['tools']), {'codedb', 'zvec-grep'})
        self.assertEqual(state['projects'], {'keep': {}})
        self.assertFalse((self.megai / 'bin/ix').is_symlink())
        # A copied header is not evidence of ownership: these fixtures differ
        # from the exact shipped originals and must survive.
        self.assertTrue((self.megai / 'lib/install_ix.sh').exists())
        self.assertTrue((self.megai / 'lib/ix_safety.py').exists())
        self.assertEqual((self.home / '.ix/data').read_text(), 'graph data must remain')
        self.assertTrue((self.home / '.local/bin/ix').exists())
        manifests = list((self.megai / 'backups/ix-retirement').glob('*/manifest.json'))
        self.assertEqual(len(manifests), 1)
        self.assertEqual(stat.S_IMODE(manifests[0].parent.stat().st_mode), 0o700)
        for entry in json.loads(manifests[0].read_text()):
            dest = Path(entry['backup'])
            key = str(Path(entry['path']).relative_to(self.home))
            self.assertEqual('link:' + os.readlink(dest) if dest.is_symlink() else dest.read_bytes(), before[key])
            if not dest.is_symlink():
                self.assertEqual(stat.S_IMODE(dest.stat().st_mode), 0o600)
        after = self.snapshot()
        self.assertIn('0 change(s)', self.run_helper().stdout)
        self.assertEqual(self.snapshot(), after)

    def test_malformed_or_wrong_shape_never_partially_writes(self):
        for name, text in (('.codex/config.toml', '[broken'),
                           ('.megai/state.json', '{broken'),
                           ('.megai/state.json', '[]'),
                           ('.megai/state.json', '{"tools":[]}')):
            with self.subTest(name=name, text=text):
                target = self.home / name
                original = target.read_text()
                target.write_text(text)
                before = self.snapshot()
                self.run_helper(success=False)
                self.assertEqual(self.snapshot(), before)
                target.write_text(original)

    def test_custom_entries_and_files_are_preserved(self):
        self.put('.codex/config.toml', '[mcp_servers.ix-memory]\ncommand = "custom"\nargs = []\n')
        self.put('.megai/lib/install_ix.sh', '# user replacement\n')
        link = self.megai / 'bin/ix'
        link.unlink()
        self.put('.megai/bin/ix', 'custom binary')
        result = self.run_helper()
        self.assertIn('Preserved custom', result.stderr)
        self.assertEqual((self.megai / 'bin/ix').read_text(), 'custom binary')
        self.assertEqual((self.megai / 'lib/install_ix.sh').read_text(), '# user replacement\n')
        self.assertIn('command = "custom"', (self.home / '.codex/config.toml').read_text())

    def test_exact_content_fingerprint_not_header(self):
        spec = importlib.util.spec_from_file_location('retire_ix', HELPER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        target = self.megai / 'lib/install_ix.sh'
        shipped = target.read_bytes()
        # Exercise the same fingerprint path on a bounded stand-in rather than
        # retaining the removed installer as another runnable repo fixture.
        module.LEGACY_HASHES = {'install_ix.sh': hashlib.sha256(shipped).hexdigest()}
        plan = module.build_plan(self.home, self.megai)
        self.assertIn((target, shipped, None), plan)
        target.write_bytes(shipped + b'echo user-added behavior\n')
        plan = module.build_plan(self.home, self.megai)
        self.assertNotIn(target, [entry[0] for entry in plan])
        target.write_bytes(shipped)
        module.apply_plan(module.build_plan(self.home, self.megai), self.megai)
        self.assertFalse(target.exists())

    def test_custom_marketplace_warns(self):
        target = self.put('.agents/plugins/marketplace.json', json.dumps({'plugins': [
            {'name': 'ix-memory', 'source': {'source': 'local', 'path': './custom'}}]}))
        before = target.read_bytes()
        result = self.run_helper()
        self.assertIn('Preserved custom Ix marketplace entry', result.stderr)
        self.assertEqual(target.read_bytes(), before)

    def test_custom_windows_hook_is_preserved(self):
        custom = {'type': 'command', 'command': STOP, 'commandWindows': 'user-owned'}
        self.put('.codex/hooks.json', json.dumps({'hooks': {'Stop': [{'hooks': [custom]}]}}))
        self.run_helper()
        hooks = json.loads((self.home / '.codex/hooks.json').read_text())
        self.assertEqual(hooks, {'hooks': {'Stop': [{'hooks': [custom]}]}})

    def test_symlink_config_is_refused(self):
        target = self.home / '.codex/hooks.json'
        moved = self.home / 'user-hooks.json'
        target.rename(moved)
        target.symlink_to(moved)
        before = self.snapshot()
        self.run_helper(success=False)
        self.assertEqual(self.snapshot(), before)

    def test_multiline_toml_ambiguity_is_refused(self):
        target = self.home / '.codex/config.toml'
        target.write_text('note = """\n[mcp_servers.ix-memory]\nnot a table\n"""\n' + target.read_text())
        before = self.snapshot()
        self.run_helper(success=False)
        self.assertEqual(self.snapshot(), before)

    def test_active_surfaces_no_longer_use_ix(self):
        for name in ('lib/install_ix.sh', 'lib/ix_safety.py'):
            self.assertFalse((ROOT / name).exists())
        for name in ('bin/megai', 'lib/main.sh', 'pi-skill/SKILL.md', 'omp-skill/SKILL.md'):
            self.assertIsNone(re.search(r'\bix\b|install_ix|ix_safety', (ROOT / name).read_text(), re.I), name)
        main = (ROOT / 'lib/main.sh').read_text()
        total = int(re.search(r'TOTAL=(\d+)', main)[1])
        self.assertEqual([int(n) for n in re.findall(r'^step (\d+) ', main, re.M)], list(range(1, total + 1)))
        self.assertIn('install_codedb.sh', main)
        self.assertIn('install_zvec_grep.sh', main)
        skill = (ROOT / 'pi-skill/SKILL.md').read_text()
        for required in ('codedb', 'zvec-grep', '`rg`', 'native file tools', 'exact replacements'):
            self.assertIn(required, skill)


if __name__ == '__main__':
    unittest.main()

"""Offline migration behavior: preservation, conflict refusal and repeatability."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class Engineering(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.agent = self.home / ".pi/agent"
        self.agent.mkdir(parents=True)
        self.shared = self.home / ".megai"
        self.shared.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), MEGAI_HOME=str(self.shared),
                        MEGAI_SOURCE=str(ROOT), PI_CODING_AGENT_DIR=str(self.agent),
                        PYTHONDONTWRITEBYTECODE="1")

    def run_migration(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "lib/pi_engineering.py"), *args],
                              env=self.env, capture_output=True, text=True)

    def snapshot(self):
        return {str(p.relative_to(self.home)): p.read_bytes()
                for p in self.home.rglob("*") if p.is_file() and not p.is_symlink()}

    def test_migration_preserves_preferences_and_is_repeatable(self):
        settings = {"defaultProvider": "custom", "defaultModel": "chosen", "defaultThinkingLevel": "high",
                    "skills": ["!user-choice"], "extensions": ["custom.ts"],
                    "packages": ["npm:@fission-ai/openspec@1.13.0", {"source": "npm:@dietrichgebert/ponytail@4.9.0"},
                                 "npm:@weiping/pi-superpowers@5.1.0", "npm:@dietrichgebert/ponytail-extra", "npm:custom"]}
        (self.agent / "settings.json").write_text(json.dumps(settings))
        (self.agent / "auth.json").write_text('synthetic secret stays byte-identical')
        (self.agent / "AGENTS.md").write_text("User policy stays.\n")
        before = self.snapshot()
        self.assertEqual(self.run_migration().returncode, 0)
        self.assertEqual(before, self.snapshot(), "preflight cannot write")
        result = self.run_migration("--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads((self.agent / "settings.json").read_text())
        self.assertEqual(actual, {**settings, "packages": ["npm:@dietrichgebert/ponytail-extra", "npm:custom"]})
        self.assertEqual((self.agent / "auth.json").read_bytes(), before['.pi/agent/auth.json'])
        self.assertTrue((self.agent / "AGENTS.md").read_text().startswith("User policy stays."))
        for name in ("codebase-design", "diagnosing-bugs", "tdd", "code-review"):
            self.assertTrue((self.agent / "skills" / name / "SKILL.md").is_file())
        after = self.snapshot()
        self.assertEqual(self.run_migration("--apply").returncode, 0)
        self.assertEqual(after, self.snapshot())
        self.assertEqual(self.run_migration("--verify").returncode, 0)
        self.assertTrue(list((self.shared / "backups").glob("*/manifest.json")))

    def test_custom_skill_blocks_all_writes(self):
        path = self.agent / "skills/tdd/SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text("My custom skill")
        before = self.snapshot()
        self.assertNotEqual(self.run_migration("--apply").returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_reinstall_rejects_custom_skill_before_installing_packages(self):
        spec = importlib.util.spec_from_file_location("defaults_install", ROOT / "pi-defaults/install.py")
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        (self.agent / "defaults").mkdir()
        (self.agent / "defaults/manifest.json").write_text('{"schema":1}')
        custom = self.agent / "skills/tdd/SKILL.md"
        custom.parent.mkdir(parents=True)
        custom.write_text("User-owned TDD")
        before = self.snapshot()
        calls = []

        def run(*args, **kwargs):
            calls.append(tuple(str(a) for a in args))
            if len(args) > 1 and str(args[1]).endswith("pi_engineering.py"):
                subprocess.run([str(a) for a in args], check=True, capture_output=True, **kwargs)

        with patch.dict(os.environ, self.env), patch.object(installer, "run", side_effect=run), \
                patch.object(installer.shutil, "which", return_value="/usr/bin/true"):
            with self.assertRaises(subprocess.CalledProcessError):
                installer.install()
        self.assertEqual(before, self.snapshot())
        self.assertFalse(any(call[0] in ("npm", "bun") for call in calls))

    def test_owned_retired_resources_are_removed_custom_resources_are_preserved(self):
        path = self.agent / "skills/openspec-propose/SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text("Custom OpenSpec")
        before = self.snapshot()
        self.assertNotEqual(self.run_migration("--apply").returncode, 0)
        self.assertEqual(before, self.snapshot())
        (self.shared / "slim-wiring.json").write_text(json.dumps({str(path): hashlib.sha256(path.read_bytes()).hexdigest()}))
        result = self.run_migration("--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(path.exists())

    def test_malformed_settings_and_symlink_retirement_refuse_without_writes(self):
        (self.agent / "settings.json").write_text("[]")
        before = self.snapshot()
        self.assertNotEqual(self.run_migration("--apply").returncode, 0)
        self.assertEqual(before, self.snapshot())
        (self.agent / "settings.json").unlink()
        (self.agent / "skills").mkdir()
        (self.agent / "skills/openspec-propose").symlink_to(self.shared, target_is_directory=True)
        before = self.snapshot()
        self.assertNotEqual(self.run_migration("--apply").returncode, 0)
        self.assertEqual(before, self.snapshot())


if __name__ == "__main__":
    unittest.main()

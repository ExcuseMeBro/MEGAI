#!/usr/bin/env python3
"""Exercise scoped worker installation through the public CLI in disposable homes."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
ASSETS = ("index.ts", "bridge.mjs", "README.md")


class LocalWorkerInstaller(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pi-local-worker-install-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.shared = self.home / ".megai"
        self.shared.mkdir()
        self.agent = self.home / "agent"
        self.agent.mkdir()
        self.source = self.home / "source"
        self.assets = self.source / "pi-defaults/extensions/megai-local-worker"
        shutil.copytree(REPO / "pi-defaults/extensions/megai-local-worker", self.assets)
        self.target = self.agent / "extensions/megai-local-worker"
        self.before = {}
        for relative in ("settings.json", "auth.json", "models.json", "mcp.json", "sessions/active.jsonl", "extensions/other/index.ts"):
            path = self.agent / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"operator-owned:{relative}\n")
            self.before[path] = path.read_bytes()
        self.receipt = self.shared / "slim-wiring.json"
        self.receipt.write_text('{"other-owned":"preserved"}\n')

    def run_installer(self, *args, expected=0):
        env = {**os.environ, "HOME": str(self.home), "MEGAI_HOME": str(self.shared),
               "MEGAI_SOURCE": str(self.source), "PI_CODING_AGENT_DIR": str(self.agent)}
        env.pop("MEGAI_TRANSACTION_LOG", None)
        result = subprocess.run(["python3", "-B", str(REPO / "lib/pi_local_worker.py"), *args],
                                env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        for path, content in self.before.items():
            self.assertEqual(path.read_bytes(), content)
        return result

    def test_scoped_install_private_backup_and_idempotent_exact_check(self):
        before = self.receipt.read_bytes()
        self.run_installer()
        self.assertFalse(self.target.exists())
        self.run_installer("--apply")
        for name in ASSETS:
            data = (self.target / name).read_bytes()
            self.assertEqual(data, (self.assets / name).read_bytes())
            self.assertEqual(json.loads(self.receipt.read_text())[str(self.target / name)], hashlib.sha256(data).hexdigest())
        self.assertEqual(json.loads(self.receipt.read_text())["other-owned"], "preserved")
        backups = list((self.shared / "backups").iterdir())
        self.assertEqual(len(backups), 1)
        manifest = json.loads((backups[0] / "manifest.json").read_text())
        self.assertEqual((backups[0] / manifest[str(self.receipt)]).read_bytes(), before)
        self.assertEqual((backups[0].stat().st_mode & 0o077), 0)
        self.run_installer("--check")
        self.run_installer("--apply")
        self.assertEqual(list((self.shared / "backups").iterdir()), backups)
        self.assertFalse((self.shared / "local-workers").exists(), "installer cannot start or initialize workers")

    def test_owned_upgrade_backs_up_exact_prior_bytes(self):
        self.run_installer("--apply")
        old = (self.assets / "README.md").read_bytes()
        (self.assets / "README.md").write_bytes(old + b"\nReviewed change.\n")
        self.run_installer("--check", expected=1)
        self.run_installer("--apply")
        retained = []
        for path in (self.shared / "backups").glob("*/manifest.json"):
            manifest = json.loads(path.read_text())
            if manifest.get(str(self.target / "README.md")):
                retained.append((path.parent / manifest[str(self.target / "README.md")]).read_bytes())
        self.assertEqual(retained, [old])

    def test_custom_unknown_and_symlink_collisions_preserved_without_partial_writes(self):
        self.target.mkdir(parents=True)
        (self.target / "bridge.mjs").write_text("custom")
        before = self.receipt.read_bytes()
        self.run_installer("--apply", expected=1)
        self.assertFalse((self.target / "index.ts").exists())
        self.assertEqual(self.receipt.read_bytes(), before)
        (self.target / "bridge.mjs").unlink()
        (self.target / "unknown.ts").write_text("custom")
        self.run_installer("--apply", expected=1)
        self.assertFalse((self.target / "index.ts").exists())
        (self.target / "unknown.ts").unlink()
        self.target.rmdir()
        outside = self.home / "outside"
        outside.mkdir()
        self.target.symlink_to(outside, target_is_directory=True)
        self.run_installer("--apply", expected=1)
        self.assertEqual(list(outside.iterdir()), [])

    def test_busy_or_malformed_ownership_refuses(self):
        lock = self.shared / "durable-install.lock"
        lock.mkdir()
        self.run_installer("--apply", expected=1)
        self.assertFalse(self.target.exists())
        lock.rmdir()
        self.receipt.write_text("[]")
        self.run_installer("--apply", expected=1)
        self.assertEqual(self.receipt.read_text(), "[]")


if __name__ == "__main__":
    unittest.main()

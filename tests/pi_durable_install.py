#!/usr/bin/env python3
"""Public scoped installer acceptance, using disposable operator configuration."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class ScopedInstaller(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pi-durable-install-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.agent = self.home / ".pi/agent"
        self.shared = self.home / ".megai"
        self.shared.mkdir()
        self.agent.mkdir(parents=True)
        self.source = self.home / "source"
        self.assets = self.source / "pi-defaults/extensions/megai-durable-workflow"
        shutil.copytree(REPO / "pi-defaults/extensions/megai-durable-workflow", self.assets)
        self.target = self.agent / "extensions/megai-durable-workflow"
        for relative in (
            "settings.json", "models.json", "auth.json", "mcp.json", "megai-roles.json",
            "sessions/existing.jsonl", "extensions/fsearch/index.ts",
            "extensions/megai-discovery/index.ts", "extensions/megai-headroom/index.ts",
        ):
            path = self.agent / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"operator-owned:{relative}\n".encode())
        self.receipt = self.shared / "slim-wiring.json"
        self.receipt.write_text('{"unrelated-owner":"keep-me"}\n')
        self.before = {str(p): p.read_bytes() for p in self.agent.rglob("*") if p.is_file()}

    def run_installer(self, *args, expected=0):
        env = {**os.environ, "HOME": str(self.home), "MEGAI_HOME": str(self.shared),
               "MEGAI_SOURCE": str(self.source), "PI_CODING_AGENT_DIR": str(self.agent)}
        env.pop("MEGAI_TRANSACTION_LOG", None)
        result = subprocess.run(
            ["python3", "-B", str(REPO / "lib/pi_durable_workflow.py"), *args],
            env=env, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def assert_operator_bytes(self):
        for path, original in self.before.items():
            self.assertEqual(Path(path).read_bytes(), original, path)

    def test_scoped_install_preserves_config_and_backups_and_is_idempotent(self):
        receipt_before = self.receipt.read_bytes()
        self.run_installer()
        self.assertFalse(self.target.exists())
        self.run_installer("--apply")
        self.assert_operator_bytes()
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual(receipt["unrelated-owner"], "keep-me")
        for name in ("index.ts", "store.mjs", "README.md"):
            content = (self.target / name).read_bytes()
            self.assertEqual(content, (self.assets / name).read_bytes())
            self.assertEqual(receipt[str(self.target / name)], hashlib.sha256(content).hexdigest())
        backups = list((self.shared / "backups").iterdir())
        self.assertEqual(len(backups), 1)
        manifest = json.loads((backups[0] / "manifest.json").read_text())
        self.assertEqual((backups[0] / manifest[str(self.receipt)]).read_bytes(), receipt_before)
        self.run_installer("--check")
        self.run_installer("--apply")
        self.assertEqual(list((self.shared / "backups").iterdir()), backups)
        self.assert_operator_bytes()

    def test_owned_upgrade_keeps_exact_private_backup(self):
        self.run_installer("--apply")
        old = (self.target / "README.md").read_bytes()
        (self.assets / "README.md").write_bytes(old + b"\nReviewed upgrade.\n")
        self.run_installer("--check", expected=1)
        self.run_installer("--apply")
        manifests = [p for p in (self.shared / "backups").glob("*/manifest.json")]
        records = [(p, json.loads(p.read_text())) for p in manifests]
        matching = [(p, m[str(self.target / "README.md")]) for p, m in records
                    if m.get(str(self.target / "README.md")) is not None]
        self.assertEqual(len(matching), 1)
        self.assertEqual((matching[0][0].parent / matching[0][1]).read_bytes(), old)
        self.assert_operator_bytes()

    def test_custom_collision_refuses_without_partial_writes(self):
        self.target.mkdir(parents=True)
        (self.target / "store.mjs").write_text("custom module")
        before = self.receipt.read_bytes()
        result = self.run_installer("--apply", expected=1)
        self.assertIn("custom/legacy asset preserved", result.stderr)
        self.assertFalse((self.target / "index.ts").exists())
        self.assertEqual(self.receipt.read_bytes(), before)
        self.assert_operator_bytes()

    def test_symlink_destination_is_refused(self):
        outside = self.home / "outside"
        outside.mkdir()
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.symlink_to(outside, target_is_directory=True)
        self.run_installer("--apply", expected=1)
        self.assertEqual(list(outside.iterdir()), [])
        self.assert_operator_bytes()

    def test_unknown_assets_busy_install_and_corrupt_receipt_are_refused(self):
        self.target.mkdir(parents=True)
        (self.target / "unknown.ts").write_text("keep")
        self.run_installer("--apply", expected=1)
        self.assertFalse((self.target / "index.ts").exists())
        (self.target / "unknown.ts").unlink()
        (self.shared / "durable-install.lock").mkdir()
        self.run_installer("--apply", expected=1)
        self.assertFalse((self.target / "index.ts").exists())
        (self.shared / "durable-install.lock").rmdir()
        self.receipt.write_text("[]")
        self.run_installer("--apply", expected=1)
        self.assertEqual(self.receipt.read_text(), "[]")
        self.assert_operator_bytes()


if __name__ == "__main__":
    unittest.main()

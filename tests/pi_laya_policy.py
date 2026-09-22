#!/usr/bin/env python3
"""Ownership-aware wiring for the local decision extension.

The installed extension must be the Laya one, its stdio bridge must sit next to it
(the extension loads the bridge by relative path), and the bytes the installer owned
from the retired hosted decision product must be retired on upgrade. The retired names
are read from the installer itself, so the strict active-scope guard can forbid them
everywhere else, including in this file.
"""
from __future__ import annotations

import hashlib
import json
import sys
import unittest

from slim_distribution import ROOT, Slim

sys.path.insert(0, str(ROOT / "lib"))
from pi_model_policy import LEGACY_ASSETS

ASSETS = (
    ("extensions/megai-laya/index.ts", "pi-skill/laya/index.ts"),
    ("extensions/megai-laya/bridge.py", "pi-skill/laya/bridge.py"),
    ("extensions/megai-laya/compaction.ts", "pi-skill/laya/compaction.ts"),
)


class LayaPolicy(Slim):
    def test_installed_extension_bridge_and_compaction_are_the_laya_bytes(self):
        self.wire()
        agent = self.home / ".pi/agent"
        for installed, source in ASSETS:
            with self.subTest(asset=installed):
                self.assertEqual((agent / installed).read_bytes(),
                                 (self.megai / source).read_bytes())
        before = self.snapshot()
        self.wire()
        self.assertEqual(self.snapshot(), before, "wiring must be idempotent")

    def test_owned_retired_assets_are_removed_on_upgrade(self):
        self.wire()
        agent = self.home / ".pi/agent"
        self.assertTrue(LEGACY_ASSETS, "the installer must name the retired assets it owns")
        receipts = self.megai / "slim-wiring.json"
        receipt = json.loads(receipts.read_text())
        for relative in LEGACY_ASSETS:
            target = agent / relative
            self.write(target, "retired hosted decision tool\n")
            receipt[str(target)] = hashlib.sha256(target.read_bytes()).hexdigest()
        receipts.write_text(json.dumps(receipt))
        self.wire()
        for relative in LEGACY_ASSETS:
            with self.subTest(asset=relative):
                self.assertFalse((agent / relative).exists(), "owned retired bytes must be retired")

    def test_a_user_owned_retired_asset_is_preserved(self):
        self.wire()
        target = self.home / ".pi/agent" / LEGACY_ASSETS[0]
        self.write(target, "user-owned decision tool\n")
        before = self.snapshot()
        self.assertIn("unowned retired asset preserved", self.wire(ok=False).stderr)
        self.assertEqual(self.snapshot(), before)

    def test_removal_takes_the_extension_the_bridge_and_the_companion(self):
        self.wire()
        self.wire("--remove")
        for installed, _ in ASSETS:
            with self.subTest(asset=installed):
                self.assertFalse((self.home / ".pi/agent" / installed).exists())

    def test_preflight_writes_nothing(self):
        before = self.snapshot()
        self.wire("--check")
        self.assertEqual(self.snapshot(), before)

    def test_the_install_flow_prepares_the_runtime_with_its_own_installer(self):
        installer = (ROOT / "pi-defaults/install.py").read_text()
        self.assertIn("lib/install_laya.sh", installer,
                      "the real install flow must prepare the pinned local runtime")

    def test_migration_is_gated_on_a_verified_owned_runtime(self):
        # Installed legacy decision bytes are the migration the gate protects: a Laya
        # runtime that fails checkpoint verification must not retire them or activate Laya.
        agent = self.home / ".pi/agent"
        receipt_path = self.megai / "slim-wiring.json"
        receipt = {}
        for relative in LEGACY_ASSETS:
            target = agent / relative
            self.write(target, "owned hosted decision tool\n")
            receipt[str(target)] = hashlib.sha256(target.read_bytes()).hexdigest()
        receipt_path.write_text(json.dumps(receipt))
        self.write(self.megai / "venv/laya/.megai-owned",
                   "owner=megai-laya\nstate=installed\n")
        self.stub("laya-check-fail", 'printf "laya: checkpoints failed\\n" >&2\nexit 1\n')
        self.stub("laya-check-ok", "exit 0\n")
        before = self.snapshot()
        result = self.wire(ok=False, env=dict(self.env, MEGAI_LAYA_CHECK="laya-check-fail"))
        self.assertIn("legacy decision assets are preserved", result.stderr)
        self.assertIn("Laya is not activated", result.stderr)
        self.assertEqual(self.snapshot(), before, "a gated migration must write nothing")
        for relative in LEGACY_ASSETS:
            self.assertTrue((agent / relative).is_file(), "owned legacy assets must be preserved")
        self.assertFalse((agent / "extensions/megai-laya/index.ts").exists())
        # The same transaction retires the legacy bytes and activates Laya once the
        # runtime verifies.
        self.wire(env=dict(self.env, MEGAI_LAYA_CHECK="laya-check-ok"))
        for relative in LEGACY_ASSETS:
            self.assertFalse((agent / relative).exists())
        self.assertTrue((agent / "extensions/megai-laya/index.ts").is_file())

    def test_removal_still_works_under_a_failing_runtime_gate(self):
        self.wire()
        self.write(self.megai / "venv/laya/.megai-owned",
                   "owner=megai-laya\nstate=installed\n")
        self.stub("laya-check-fail", "exit 1\n")
        self.wire("--remove", env=dict(self.env, MEGAI_LAYA_CHECK="laya-check-fail"))
        self.assertFalse((self.home / ".pi/agent/extensions/megai-laya/index.ts").exists())

    def owned_legacy(self, agent):
        receipt = {}
        for relative in LEGACY_ASSETS:
            target = agent / relative
            self.write(target, "owned hosted decision tool\n")
            receipt[str(target)] = hashlib.sha256(target.read_bytes()).hexdigest()
        (self.megai / "slim-wiring.json").write_text(json.dumps(receipt))

    def test_a_missing_runtime_fails_preflight_without_writes(self):
        # No runtime at all must still gate activation: previously the absent marker
        # skipped verification and the retirement proceeded unverified.
        agent = self.home / ".pi/agent"
        self.owned_legacy(agent)
        self.stub("laya-check-missing", 'printf "laya: no owned runtime\\n" >&2\nexit 1\n')
        before = self.snapshot()
        result = self.wire(ok=False, env=dict(self.env, MEGAI_LAYA_CHECK="laya-check-missing"))
        self.assertIn("legacy decision assets are preserved", result.stderr)
        self.assertEqual(self.snapshot(), before, "a missing runtime must write nothing")
        for relative in LEGACY_ASSETS:
            self.assertTrue((agent / relative).is_file())
        self.assertFalse((agent / "extensions/megai-laya/index.ts").exists())

    def test_an_unowned_runtime_fails_preflight_without_writes(self):
        agent = self.home / ".pi/agent"
        self.owned_legacy(agent)
        foreign = self.write(self.megai / "venv/laya/foreign", "someone else's environment\n")
        self.stub("laya-check-unowned", 'printf "laya: not owned by MEGAI\\n" >&2\nexit 1\n')
        before = self.snapshot()
        result = self.wire(ok=False, env=dict(self.env, MEGAI_LAYA_CHECK="laya-check-unowned"))
        self.assertIn("Laya is not activated", result.stderr)
        self.assertEqual(self.snapshot(), before, "an unowned runtime must write nothing")
        self.assertEqual(foreign.read_text(), "someone else's environment\n")
        self.assertFalse((agent / "extensions/megai-laya/index.ts").exists())


def load_tests(loader, tests, pattern):
    # LayaPolicy inherits the distribution cases; do not run the imported Slim twice.
    return loader.loadTestsFromTestCase(LayaPolicy)


if __name__ == "__main__":
    unittest.main()

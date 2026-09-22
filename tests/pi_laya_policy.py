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
from pathlib import Path

from slim_distribution import ROOT, Slim

sys.path.insert(0, str(ROOT / "lib"))
from pi_model_policy import LEGACY_ASSETS

ASSETS = (
    ("extensions/megai-laya/index.ts", "pi-skill/laya/index.ts"),
    ("extensions/megai-laya/bridge.py", "pi-skill/laya/bridge.py"),
    ("extensions/megai-laya-compaction/index.ts", "pi-skill/laya-compaction/index.ts"),
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


def load_tests(loader, tests, pattern):
    # LayaPolicy inherits the distribution cases; do not run the imported Slim twice.
    return loader.loadTestsFromTestCase(LayaPolicy)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Ownership-aware wiring for the local decision extension.

The installed extension must be the Laya one and its stdio bridge must sit next to
it (the extension loads the bridge by relative path). The installer places only Laya
assets; the retired hosted decision product no longer exists anywhere in the tree.
"""
from __future__ import annotations

import unittest

from slim_distribution import ROOT, Slim

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

    def test_activation_is_gated_on_a_verified_owned_runtime(self):
        # A Laya runtime that fails verification must not activate the decision tool.
        self.write(self.megai / "venv/laya/.megai-owned",
                   "owner=megai-laya\nstate=installed\n")
        self.stub("laya-check-fail", 'printf "laya: checkpoints failed\\n" >&2\nexit 1\n')
        self.stub("laya-check-ok", "exit 0\n")
        before = self.snapshot()
        result = self.wire(ok=False, env=dict(self.env, MEGAI_LAYA_CHECK="laya-check-fail"))
        self.assertIn("Laya is not activated", result.stderr)
        self.assertEqual(self.snapshot(), before, "a gated activation must write nothing")
        self.assertFalse((self.home / ".pi/agent/extensions/megai-laya/index.ts").exists())
        # The same transaction activates Laya once the runtime verifies.
        self.wire(env=dict(self.env, MEGAI_LAYA_CHECK="laya-check-ok"))
        self.assertTrue((self.home / ".pi/agent/extensions/megai-laya/index.ts").is_file())

    def test_removal_still_works_under_a_failing_runtime_gate(self):
        self.wire()
        self.write(self.megai / "venv/laya/.megai-owned",
                   "owner=megai-laya\nstate=installed\n")
        self.stub("laya-check-fail", "exit 1\n")
        self.wire("--remove", env=dict(self.env, MEGAI_LAYA_CHECK="laya-check-fail"))
        self.assertFalse((self.home / ".pi/agent/extensions/megai-laya/index.ts").exists())

    def test_a_missing_runtime_fails_preflight_without_writes(self):
        self.stub("laya-check-missing", 'printf "laya: no owned runtime\\n" >&2\nexit 1\n')
        before = self.snapshot()
        result = self.wire(ok=False, env=dict(self.env, MEGAI_LAYA_CHECK="laya-check-missing"))
        self.assertIn("Laya is not activated", result.stderr)
        self.assertEqual(self.snapshot(), before, "a missing runtime must write nothing")
        self.assertFalse((self.home / ".pi/agent/extensions/megai-laya/index.ts").exists())

    def test_an_unowned_runtime_fails_preflight_without_writes(self):
        foreign = self.write(self.megai / "venv/laya/foreign", "someone else's environment\n")
        self.stub("laya-check-unowned", 'printf "laya: not owned by MEGAI\\n" >&2\nexit 1\n')
        before = self.snapshot()
        result = self.wire(ok=False, env=dict(self.env, MEGAI_LAYA_CHECK="laya-check-unowned"))
        self.assertIn("Laya is not activated", result.stderr)
        self.assertEqual(self.snapshot(), before, "an unowned runtime must write nothing")
        self.assertEqual(foreign.read_text(), "someone else's environment\n")
        self.assertFalse((self.home / ".pi/agent/extensions/megai-laya/index.ts").exists())


def load_tests(loader, tests, pattern):
    # LayaPolicy inherits the distribution cases; do not run the imported Slim twice.
    return loader.loadTestsFromTestCase(LayaPolicy)


if __name__ == "__main__":
    unittest.main()

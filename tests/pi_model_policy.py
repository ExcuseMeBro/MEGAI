#!/usr/bin/env python3
"""Offline model-policy wiring; real HOME and credentials remain untouched."""
import json
import sys
import unittest

from slim_distribution import Slim


class ModelPolicy(Slim):
    def test_model_guard_installed_and_removed(self):
        self.wire()
        agent = self.home / ".pi/agent"
        policy = (agent / "AGENTS.md").read_text()
        self.assertIn("no model allowlist", policy)
        self.assertFalse((agent / "extensions/megai-model-guard/index.ts").exists())
        self.assertTrue((agent / "extensions/megai-provider-guard/index.ts").is_file())
        before = self.snapshot()
        self.wire()
        self.assertEqual(self.snapshot(), before)
        self.wire("--remove")
        self.assertNotIn("megai:subagent-models:begin", (agent / "AGENTS.md").read_text())
        self.assertFalse((agent / "extensions/megai-model-guard/index.ts").exists())
        self.assertFalse((agent / "extensions/megai-provider-guard/index.ts").exists())

    def test_owned_legacy_guard_retired_on_upgrade(self):
        import hashlib

        self.wire()
        agent = self.home / ".pi/agent"
        guard = agent / "extensions/megai-model-guard/index.ts"
        self.write(guard, "legacy model guard")
        receipt_path = self.megai / "slim-wiring.json"
        receipt = json.loads(receipt_path.read_text())
        receipt[str(guard)] = hashlib.sha256(guard.read_bytes()).hexdigest()
        receipt_path.write_text(json.dumps(receipt))
        command = (sys.executable, str(self.megai / "lib/pi_model_policy.py"))
        before = self.snapshot()
        self.run_cmd(*command, "--check")
        self.assertEqual(self.snapshot(), before)
        self.run_cmd(*command)
        self.assertFalse(guard.exists())
        self.assertNotIn(str(guard), json.loads(receipt_path.read_text()))
        self.assertTrue((agent / "extensions/megai-provider-guard/index.ts").is_file())
        after = self.snapshot()
        self.run_cmd(*command)
        self.assertEqual(self.snapshot(), after)

    def test_source_publication_retires_owned_guard_source(self):
        import hashlib
        from slim_distribution import ROOT

        guard = self.megai / "pi-skill/model-guard/index.ts"
        self.write(guard, "legacy source guard")
        receipt_path = self.megai / "slim-wiring.json"
        receipt_path.write_text(json.dumps({str(guard): hashlib.sha256(guard.read_bytes()).hexdigest()}))
        self.run_cmd(sys.executable, str(self.megai / "lib/install_slim_source.py"), str(ROOT))
        self.assertFalse(guard.exists())
        self.assertNotIn(str(guard), json.loads(receipt_path.read_text()))
        backups = self.megai / "backups"
        self.assertTrue(any(p.is_file() and p.read_bytes() == b"legacy source guard" for p in backups.rglob("*")))

    def test_timebox_and_escalation_policy_reaches_both_entrypoints(self):
        self.wire()
        agent = self.home / ".pi/agent"
        source = (self.megai / "pi-skill/delegation.md").read_text()
        installed = (agent / "skills/megai/delegation.md").read_text()
        self.assertEqual(installed, source)
        self.assertIn(source.rstrip(), (agent / "AGENTS.md").read_text())
        for rule in (
            "5 minutes (300 seconds)",
            "including model/tool waits",
            "same-model retry loop",
            "suitable, available alternative",
            "at most two escalation transitions per slice",
            "Confirm the old writer has stopped",
            "not a runtime watchdog",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, installed)

    def test_standalone_preserves_local_resources(self):
        agent = self.home / ".pi/agent"
        settings = '{"defaultModel":"keep","packages":["custom"],"extensions":["!*"]}'
        self.write(agent / "settings.json", settings)
        self.write(agent / "auth.json", '{"synthetic":"untouched"}')
        self.write(agent / "AGENTS.md", "Local Pi-only instructions stay.\n")
        command = (sys.executable, str(self.megai / "lib/pi_model_policy.py"))
        before = self.snapshot()
        self.run_cmd(*command, "--check")
        self.assertEqual(self.snapshot(), before)
        self.run_cmd(*command)
        self.assertEqual((agent / "settings.json").read_text(), settings)
        self.assertEqual((agent / "auth.json").read_text(), '{"synthetic":"untouched"}')
        self.assertTrue((agent / "AGENTS.md").read_text().startswith("Local Pi-only instructions stay.\n"))
        after = self.snapshot()
        self.run_cmd(*command)
        self.assertEqual(self.snapshot(), after)
        self.run_cmd(*command, "--remove")
        self.assertEqual((agent / "AGENTS.md").read_text(), "Local Pi-only instructions stay.\n")

    def test_custom_provider_guard_fails_without_writes(self):
        agent = self.home / ".pi/agent"
        self.write(agent / "extensions/megai-provider-guard/index.ts", "user code")
        before = self.snapshot()
        self.wire(ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_custom_guard_or_policy_fails_without_writes(self):
        agent = self.home / ".pi/agent"
        self.write(agent / "extensions/megai-model-guard/index.ts", "user code")
        before = self.snapshot()
        self.wire(ok=False)
        self.assertEqual(self.snapshot(), before)
        (agent / "extensions/megai-model-guard/index.ts").unlink()
        self.write(agent / "AGENTS.md", "<!-- megai:subagent-models:begin -->\ncustom\n<!-- megai:subagent-models:end -->\n")
        before = self.snapshot()
        self.wire(ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_standalone_does_not_adopt_user_edits_or_remove_unowned_block(self):
        self.wire()
        agent = self.home / ".pi/agent/AGENTS.md"
        agent.write_text(agent.read_text() + "User addition.\n")
        receipt_path = self.megai / "slim-wiring.json"
        receipt = json.loads(receipt_path.read_text())
        old_hash = receipt[str(agent)]
        command = (sys.executable, str(self.megai / "lib/pi_model_policy.py"))
        self.run_cmd(*command)
        self.assertEqual(json.loads(receipt_path.read_text())[str(agent)], old_hash)
        receipt.pop(str(agent) + "#subagent-models")
        receipt_path.write_text(json.dumps(receipt))
        before = self.snapshot()
        self.run_cmd(*command, "--remove", ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_combined_upgrade_keeps_both_policy_changes(self):
        self.wire()
        source = self.megai / "pi-skill/delegation.md"
        source.write_text(source.read_text() + "\nTest updated routing.\n")
        wiring = self.megai / "lib/slim_wiring.py"
        wiring.write_text(wiring.read_text().replace("Raw acceptance tests", "Updated raw acceptance tests"))
        self.wire()
        instructions = (self.home / ".pi/agent/AGENTS.md").read_text()
        self.assertIn("Updated raw acceptance tests", instructions)
        self.assertIn("Test updated routing.", instructions)
        self.assertEqual(instructions.count("megai:subagent-models:begin"), 1)
        receipt = json.loads((self.megai / "slim-wiring.json").read_text())
        self.assertIn(str(self.home / ".pi/agent/AGENTS.md") + "#subagent-models", receipt)
        self.wire("--verify")


if __name__ == "__main__":
    unittest.main()

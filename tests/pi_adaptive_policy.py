#!/usr/bin/env python3
"""Offline adaptive-policy/explicit economy wiring contracts; no provider calls."""
import hashlib
import json
import sys
import unittest

from slim_distribution import ROOT, Slim


class Adaptive(Slim):
    def test_small_bootstrap_and_on_demand_policy(self):
        self.wire()
        agent = self.home / ".pi/agent"
        bootstrap = (agent / "AGENTS.md").read_text()
        self.assertLess(len(bootstrap), 1900)
        self.assertIn("megai/delegation.md", bootstrap)
        self.assertNotIn("## Verified launch", bootstrap)
        policy = (agent / "skills/megai/SKILL.md").read_text()
        self.assertEqual(policy, (ROOT / "pi-skill/ADAPTIVE.md").read_text())
        for rule in ("Routine", "Guarded", "Parent implements directly", "self-review",
                     "No mandatory subagent", "contract hash or acceptance CLI",
                     "Security/auth/permissions", "sensitive data", "payments",
                     "migrations", "concurrency/shared state", "multi-repo delivery",
                     "safety/acceptance/installer policy", "source-current PASS",
                     "Urgency never downgrades", "failing reproduction",
                     "Missing optional tools", "GPT", "economy"):
            self.assertIn(rule.lower(), policy.lower())
        for name in (".claude", ".agents", ".omp/agent"):
            shared = (self.home / name / "skills/megai/SKILL.md").read_text()
            self.assertEqual(shared, (ROOT / "pi-skill/SKILL.md").read_text())
        self.assertNotIn("MEGAI adaptive", (self.home / ".claude/CLAUDE.md").read_text())

    def test_owned_legacy_bootstrap_upgrade_is_idempotent(self):
        self.wire()
        agent = self.home / ".pi/agent/AGENTS.md"
        old = ("# User rules\nPreserve me.\n"
               "<!-- megai:slim:begin -->\nLegacy heavyweight policy\n<!-- megai:slim:end -->\n")
        old_models = ("<!-- megai:subagent-models:begin -->\n"
                      + (ROOT / "pi-skill/delegation.md").read_text().rstrip()
                      + "\n<!-- megai:subagent-models:end -->\n")
        agent.write_text(old + old_models)
        receipt_path = self.megai / "slim-wiring.json"
        receipt = json.loads(receipt_path.read_text())
        receipt[str(agent)] = hashlib.sha256(agent.read_bytes()).hexdigest()
        receipt[str(agent) + "#subagent-models"] = hashlib.sha256(old_models.encode()).hexdigest()
        receipt_path.write_text(json.dumps(receipt))
        self.wire()
        self.assertTrue(agent.read_text().startswith("# User rules\nPreserve me.\n"))
        self.assertNotIn("Legacy heavyweight", agent.read_text())
        self.assertNotIn("## Verified launch", agent.read_text())
        before = self.snapshot()
        self.wire()
        self.wire("--verify")
        self.assertEqual(before, self.snapshot())
        self.assertTrue(any(p.is_file() and p.read_bytes() == (old + old_models).encode()
                            for p in (self.megai / "backups").rglob("*")))

    def test_unowned_policy_change_blocks_without_writes(self):
        self.wire()
        agent = self.home / ".pi/agent/AGENTS.md"
        agent.write_text(agent.read_text().replace("MEGAI adaptive", "Custom adaptive"))
        before = self.snapshot()
        self.wire(ok=False)
        self.assertEqual(before, self.snapshot())

    def test_economy_is_explicit_and_preserves_native_resources(self):
        agent = self.home / ".pi/agent"
        settings = {"defaultProvider": "openai-codex", "defaultModel": "gpt-6-astra",
                    "defaultThinkingLevel": "high", "packages": ["custom-package"],
                    "extensions": ["!*"], "modelThinkingLevels": {"custom/model": "low"}}
        self.write(agent / "settings.json", json.dumps(settings))
        self.write(agent / "auth.json", '{"synthetic":"preserve"}')
        self.wire()
        wired = json.loads((agent / "settings.json").read_text())
        for key in settings:
            self.assertEqual(wired[key], settings[key])
        command = (sys.executable, "-B", str(self.megai / "lib/pi_model_policy.py"),
                   "--preset", "economy")
        before = self.snapshot()
        self.run_cmd(*command, "--check")
        self.assertEqual(before, self.snapshot())
        self.run_cmd(*command)
        selected = json.loads((agent / "settings.json").read_text())
        self.assertEqual(selected["defaultProvider"], "minimax")
        self.assertEqual(selected["defaultModel"], "MiniMax-M3")
        self.assertEqual(selected["defaultThinkingLevel"], "high")
        self.assertEqual(selected["modelThinkingLevels"]["custom/model"], "low")
        for key in ("packages", "extensions"):
            self.assertEqual(selected[key], settings[key])
        self.assertEqual((agent / "auth.json").read_text(), '{"synthetic":"preserve"}')
        roles = json.loads((agent / "megai-roles.json").read_text())
        for role in ("planner", "scout", "worker"):
            self.assertEqual(roles["roles"][role]["provider"], "minimax")
        self.assertEqual(roles["roles"]["reviewer"]["provider"], "openai-codex")
        before = self.snapshot()
        self.run_cmd(*command)
        self.assertEqual(before, self.snapshot())
        self.wire()
        self.assertEqual(json.loads((agent / "settings.json").read_text()), selected)

    def test_focused_refresh_preserves_unrelated_legacy_store(self):
        self.wire()
        legacy = self.write(self.home / ".agentmemory/private.json", '{"synthetic":"keep"}')
        command = (sys.executable, "-B", str(self.megai / "lib/pi_model_policy.py"),
                   "--adaptive", "--preset", "economy")
        before = self.snapshot()
        self.run_cmd(*command, "--check")
        self.assertEqual(before, self.snapshot())
        self.run_cmd(*command)
        self.assertEqual(legacy.read_text(), '{"synthetic":"keep"}')
        agent = self.home / ".pi/agent"
        self.assertEqual((agent / "skills/megai/SKILL.md").read_bytes(),
                         (ROOT / "pi-skill/ADAPTIVE.md").read_bytes())
        before = self.snapshot()
        self.run_cmd(*command)
        self.assertEqual(before, self.snapshot())
        self.run_cmd(*command, "--remove", ok=False)
        self.assertEqual(before, self.snapshot())

    def test_focused_refresh_preflights_all_policy_collisions(self):
        self.wire()
        target = self.home / ".pi/agent/skills/megai-acceptance/SKILL.md"
        target.write_text("Custom acceptance rules\n")
        before = self.snapshot()
        self.run_cmd(sys.executable, "-B", str(self.megai / "lib/pi_model_policy.py"),
                     "--adaptive", "--preset", "economy", ok=False)
        self.assertEqual(before, self.snapshot())

    def test_all_reachable_workflows_respect_mode(self):
        paths = ("pi-skill/acceptance/SKILL.md", "pi-skill/acceptance/reference.md",
                 "pi-skill/delegation.md", "pi-skill/integration-queue.md",
                 "skills/agent-worktree-lifecycle/SKILL.md",
                 "task-flow/skills/megai-task-flow/SKILL.md")
        for path in paths:
            with self.subTest(path=path):
                text = (ROOT / path).read_text().lower()
                self.assertIn("routine", text)
                self.assertIn("guarded", text)


def load_tests(loader, tests, pattern):
    # Reuse sandbox helpers, not the entire inherited distribution suite twice.
    return unittest.TestSuite(Adaptive(name) for name in Adaptive.__dict__ if name.startswith("test_"))


if __name__ == "__main__":
    unittest.main()

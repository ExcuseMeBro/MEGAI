#!/usr/bin/env python3
"""Offline adaptive-policy/explicit economy wiring contracts; no provider calls."""
import hashlib
import json
import re
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

    def test_three_step_routing_preserves_guarded_boundaries(self):
        policy = (ROOT / "pi-skill/ADAPTIVE.md").read_text()
        self.assertEqual(re.findall(r"^\d+\. \*\*(.+?)\*\*", policy, re.MULTILINE),
                         ["Locate and edit.", "Verify once.", "Deliver and stop."])
        for clause in ("Classify the actual effect, not the filename or number of files",
                       "routine when they leave safety behavior unchanged",
                       "Changing approval, permissions,",
                       "validation, data handling, acceptance requirements or installer ownership checks is",
                       "guarded even when expressed only as instructions",
                       "one independent reviewer", "existing raw evidence",
                       "each needed check once per candidate", "concrete unresolved risk",
                       "never turn a failed gate into a routine PASS"):
            self.assertIn(clause, policy)
        acceptance = (ROOT / "pi-skill/acceptance/SKILL.md").read_text()
        self.assertIn("including instruction-only changes to approval or", acceptance)
        self.assertIn("validation requirements", acceptance)
        self.assertIn("Editorial preferences are nonblocking", acceptance)
        self.assertIn("source-current PASS", acceptance)
        bootstrap = (ROOT / "pi-skill/bootstrap.md").read_text()
        self.assertIn("Routine work is three steps", bootstrap)
        self.assertIn("main/push need separate approval", bootstrap)
        self.assertIn("only approved main pushes need GitHub release notes", bootstrap)
        self.assertIn("Forgejo is required only for ADAM and its component repositories",
                      " ".join(bootstrap.split()))

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
        self.assertEqual(selected["defaultProvider"], "deepseek")
        self.assertEqual(selected["defaultModel"], "deepseek-flash")
        self.assertEqual(selected["defaultThinkingLevel"], "high")
        self.assertEqual(selected["modelThinkingLevels"]["custom/model"], "low")
        for key in ("packages", "extensions"):
            self.assertEqual(selected[key], settings[key])
        self.assertEqual((agent / "auth.json").read_text(), '{"synthetic":"preserve"}')
        roles = json.loads((agent / "megai-roles.json").read_text())
        self.assertEqual(roles["roles"]["planner"], {
            "provider": "deepseek", "model": "deepseek-flash", "thinking": "high",
        })
        for role in ("scout", "worker"):
            self.assertEqual(roles["roles"][role], {
                "provider": "deepseek", "model": "deepseek-flash", "thinking": "low",
            })
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

    def test_explicit_adaptive_source_is_not_global_source(self):
        candidate = self.root / "candidate"
        import shutil

        for folder in ("pi-skill", "skills", "task-flow"):
            shutil.copytree(ROOT / folder, candidate / folder)
        bootstrap = candidate / "pi-skill/bootstrap.md"
        bootstrap.write_text(bootstrap.read_text() + "\nExplicit candidate marker.\n")
        # The installed/global source is deliberately missing this new asset.
        (self.megai / "pi-skill/bootstrap.md").unlink()
        script = ("import sys; from pathlib import Path; "
                  "sys.path.insert(0, sys.argv[1]); "
                  "from slim_wiring import Plan; "
                  "from pi_model_policy import stage_adaptive_policy; "
                  "p=Plan(); stage_adaptive_policy(p, Path(sys.argv[2]), Path(sys.argv[3])); "
                  "p.apply(False)")
        self.run_cmd(sys.executable, "-B", "-c", script, str(self.megai / "lib"),
                     str(self.home / ".pi/agent"), str(candidate))
        installed = (self.home / ".pi/agent/AGENTS.md").read_text()
        self.assertIn("Explicit candidate marker.", installed)
        self.assertFalse((self.megai / "pi-skill/bootstrap.md").exists())

    def test_lifecycle_does_not_reintroduce_routine_independent_review(self):
        text = " ".join((ROOT / "skills/agent-worktree-lifecycle/SKILL.md").read_text().split())
        self.assertNotIn("Preserve independent review and actual acceptance", text)
        self.assertNotIn("never substitutes for independent current acceptance", text)
        self.assertIn("Preserve mode-appropriate review and actual acceptance", text)
        self.assertIn("routine Pi uses focused tests and parent self-review", text)
        self.assertIn("guarded Pi (including multi-repo delivery) requires the independent formal gate", text)

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

    def test_jev_reaches_every_decision_step(self):
        policy = (ROOT / "pi-skill/ADAPTIVE.md").read_text().lower()
        self.assertIn("### typesafe jev at every decision step", policy)
        for step in ("triage", "task flow", "isolation", "delegation", "verification",
                     "loop control", "first-pass judge", "delivery and handoff"):
            self.assertIn(step, policy)
        self.assertIn("one call per decision boundary", policy)
        self.assertIn("never replaces a check", policy)
        for path in ("pi-defaults/skills/pi-workflow/SKILL.md",
                     "task-flow/skills/megai-task-flow/SKILL.md",
                     "pi-skill/acceptance/SKILL.md", "pi-skill/delegation.md",
                     "skills/agent-worktree-lifecycle/SKILL.md"):
            with self.subTest(path=path):
                self.assertIn("`jev`", (ROOT / path).read_text().lower())
        self.assertIn("`jev`", (ROOT / "pi-defaults/AGENTS.md").read_text().lower())
        tool = (ROOT / "pi-skill/jev/index.ts").read_text()
        self.assertIn("every workflow step decision", tool)
        self.assertIn("one call per decision boundary", tool)


def load_tests(loader, tests, pattern):
    # Reuse sandbox helpers, not the entire inherited distribution suite twice.
    return unittest.TestSuite(Adaptive(name) for name in Adaptive.__dict__ if name.startswith("test_"))


if __name__ == "__main__":
    unittest.main()

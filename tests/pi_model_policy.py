#!/usr/bin/env python3
"""Offline model-policy wiring; real HOME and credentials remain untouched."""
import json
import shutil
import sys
import unittest

from pi_laya_bridge import BridgeTests
from slim_distribution import ROOT, Slim


class ModelPolicy(Slim):
    def test_missing_laya_runtime_blocks_profile_install_without_writes(self):
        shutil.rmtree(self.megai / "laya-runtime")
        before = self.snapshot()
        result = self.wire(ok=False)
        self.assertIn("laya-runtime", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_unowned_laya_runtime_blocks_profile_install_without_writes(self):
        (self.megai / "laya-runtime/.megai-owned").write_text("operator runtime\n")
        before = self.snapshot()
        result = self.wire(ok=False)
        self.assertIn("unowned laya-runtime", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_installs_laya_without_hosted_jev_or_browser(self):
        self.wire()
        agent = self.home / ".pi/agent"
        for name in ("index.ts", "bridge.py", "compaction.ts"):
            self.assertEqual((agent / "extensions/megai-laya" / name).read_bytes(),
                             (ROOT / "pi-skill/laya" / name).read_bytes())
        for path in ("extensions/megai-jev/index.ts", "extensions/megai-jev-compaction/index.ts",
                     "skills/jev-browser/SKILL.md"):
            self.assertFalse((agent / path).exists(), path)
        self.wire("--verify")
        self.wire("--remove")
        self.assertFalse((agent / "extensions/megai-laya/index.ts").exists())

    def test_retires_only_receipt_owned_jev_assets_and_preserves_conflicts(self):
        import hashlib

        self.wire()
        agent = self.home / ".pi/agent"
        old = agent / "extensions/megai-jev/index.ts"
        self.write(old, "archived hosted extension\n")
        receipt_file = self.megai / "slim-wiring.json"
        receipt = json.loads(receipt_file.read_text())
        receipt[str(old)] = hashlib.sha256(old.read_bytes()).hexdigest()
        receipt_file.write_text(json.dumps(receipt))
        self.wire()
        self.assertFalse(old.exists())
        self.write(old, "operator-owned extension\n")
        before = self.snapshot()
        self.assertIn("unowned retired asset", self.wire(ok=False).stderr)
        self.assertEqual(self.snapshot(), before)

    def test_model_guard_installed_and_removed(self):
        self.wire()
        agent = self.home / ".pi/agent"
        policy = (agent / "AGENTS.md").read_text()
        self.assertIn("no model allowlist", policy)
        self.assertFalse((agent / "extensions/megai-model-guard/index.ts").exists())
        self.assertTrue((agent / "extensions/megai-provider-guard/index.ts").is_file())
        self.assertTrue((agent / "extensions/megai-role-routing/index.ts").is_file())
        self.assertTrue((agent / "extensions/megai-model-fallback/index.ts").is_file())
        self.assertTrue((agent / "extensions/megai-antigravity/index.ts").is_file())
        before = self.snapshot()
        self.wire()
        self.assertEqual(self.snapshot(), before)
        self.wire("--remove")
        self.assertNotIn("megai:subagent-models:begin", (agent / "AGENTS.md").read_text())
        self.assertFalse((agent / "extensions/megai-model-guard/index.ts").exists())
        self.assertFalse((agent / "extensions/megai-provider-guard/index.ts").exists())
        self.assertFalse((agent / "extensions/megai-role-routing/index.ts").exists())
        self.assertFalse((agent / "extensions/megai-model-fallback/index.ts").exists())
        self.assertFalse((agent / "extensions/megai-antigravity/index.ts").exists())

    def test_role_routing_asset_installs_idempotently_and_preserves_collision(self):
        self.wire()
        agent = self.home / ".pi/agent"
        target = agent / "extensions/megai-role-routing/index.ts"
        self.assertEqual(target.read_bytes(), (self.megai / "pi-skill/role-routing/index.ts").read_bytes())
        fallback = agent / "extensions/megai-model-fallback/index.ts"
        self.assertEqual(fallback.read_bytes(), (self.megai / "pi-skill/model-fallback/index.ts").read_bytes())
        pool = agent / "extensions/megai-antigravity/index.ts"
        self.assertEqual(pool.read_bytes(), (self.megai / "pi-skill/antigravity/index.ts").read_bytes())
        before = self.snapshot()
        self.wire()
        self.assertEqual(self.snapshot(), before)
        self.wire("--verify")
        self.wire("--remove")
        self.assertFalse(target.exists())
        self.write(target, "user-owned role routing")
        before = self.snapshot()
        self.assertIn("custom/legacy asset preserved", self.wire(ok=False).stderr)
        self.assertEqual(self.snapshot(), before)

    def test_reinstall_retires_previously_owned_decision_assets(self):
        """A reinstall removes what earlier installs owned, and nothing else.

        The retired tool's extension files and its saved tool state are seeded here the
        way an earlier install left them: owned bytes with a receipt. The run retires
        them, keeps unrelated state and leaves Pi's own resources in place.
        """
        import hashlib

        sys.path.insert(0, str(self.megai / "lib"))
        from retire_local_decisions import EXTENSIONS, PUBLISHED, RUNTIME, RUNTIME_OWNER, STATE_TOOL, TOOL

        self.wire()
        agent = self.home / ".pi/agent"
        seeded = [agent / directory / name
                  for directory, names in EXTENSIONS.items() for name in names]
        for path in seeded:
            self.write(path, "previously owned asset\n")
        receipt_path = self.megai / "slim-wiring.json"
        receipt = json.loads(receipt_path.read_text())
        for path in seeded:
            receipt[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        published = self.write(self.megai / next(iter(PUBLISHED)), "previously owned source\n")
        receipt[str(published)] = hashlib.sha256(published.read_bytes()).hexdigest()
        receipt_path.write_text(json.dumps(receipt))
        runtime = self.megai / RUNTIME
        self.write(runtime / ".megai-owned", f"owner={RUNTIME_OWNER}\n")
        self.write(runtime / "bin/python", "old runtime\n")
        state_path = self.megai / "state.json"
        state = json.loads(state_path.read_text())
        state["tools"][STATE_TOOL] = {"bin": str(self.megai / RUNTIME / "bin/python")}
        state_path.write_text(json.dumps(state))

        self.wire()
        for path in seeded:
            if "extensions/megai-laya/" in str(path):
                self.assertEqual(path.read_bytes(), (ROOT / "pi-skill/laya" / path.name).read_bytes())
            else:
                self.assertFalse(path.exists())
        receipt = json.loads(receipt_path.read_text())
        for path in seeded:
            if "extensions/megai-laya/" in str(path):
                self.assertIn(str(path), receipt)
            else:
                self.assertNotIn(str(path), receipt)
        state = json.loads(state_path.read_text())
        self.assertNotIn(STATE_TOOL, state["tools"])
        self.assertFalse(published.exists())
        self.assertFalse(runtime.exists())
        self.assertEqual(len(list((self.megai / "backups").glob("retired-decision-runtime*"))), 1)
        self.assertEqual(state["keep"], {"value": 42})
        for name in ("megai-provider-guard", "megai-role-routing", "megai-model-fallback",
                     "megai-antigravity"):
            self.assertTrue((agent / "extensions" / name / "index.ts").is_file(), name)
        self.assertNotIn(TOOL, (agent / "AGENTS.md").read_text().lower())

    def test_reinstall_preserves_an_unowned_decision_asset(self):
        """An operator file at a retired path keeps its bytes and fails the install."""
        sys.path.insert(0, str(self.megai / "lib"))
        from retire_local_decisions import EXTENSIONS

        self.wire()
        target = self.home / ".pi/agent" / next(iter(EXTENSIONS)) / "index.ts"
        self.write(target, "user-owned decision tool")
        before = self.snapshot()
        self.assertIn("unowned retired asset preserved", self.wire(ok=False).stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(target.read_text(), "user-owned decision tool")

    def test_reinstall_moves_an_owned_runtime_aside(self):
        sys.path.insert(0, str(self.megai / "lib"))
        from retire_local_decisions import RUNTIME, RUNTIME_OWNER, TOOL

        runtime = self.megai / RUNTIME
        self.write(runtime / ".megai-owned", f"owner={RUNTIME_OWNER}\nstate=installed\n")
        self.write(runtime / "bin/python", "stub\n")
        command = (sys.executable, str(self.megai / "lib/pi_model_policy.py"))
        before = self.snapshot()
        self.run_cmd(*command, "--check")
        self.assertEqual(self.snapshot(), before)
        self.run_cmd(*command)
        self.assertFalse(runtime.exists())
        moved = sorted((self.megai / "backups").glob("retired-decision-runtime*"))
        self.assertEqual(len(moved), 1)
        self.assertTrue((moved[0] / ".megai-owned").is_file())
        self.assertNotIn(TOOL, (self.home / ".pi/agent/AGENTS.md").read_text().lower())

    def test_reinstall_reports_an_unowned_runtime_without_touching_it(self):
        sys.path.insert(0, str(self.megai / "lib"))
        from retire_local_decisions import RUNTIME

        runtime = self.megai / RUNTIME
        self.write(runtime / "keep.txt", "user data\n")
        before = self.snapshot()
        command = (sys.executable, str(self.megai / "lib/pi_model_policy.py"))
        self.assertIn("unowned retired runtime preserved",
                      self.run_cmd(*command, ok=False).stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual((runtime / "keep.txt").read_text(), "user data\n")

    def test_runtime_move_failure_preserves_directory_and_policy_transaction(self):
        """A failed move cannot publish a partial Pi profile or state retirement."""
        sys.path.insert(0, str(self.megai / "lib"))
        from retire_local_decisions import RUNTIME, RUNTIME_OWNER, STATE_TOOL

        self.wire()
        agent = self.home / ".pi/agent"
        runtime = self.megai / RUNTIME
        self.write(runtime / ".megai-owned", f"owner={RUNTIME_OWNER}\n")
        self.write(runtime / "bin/python", "previous runtime\n")
        state_path = self.megai / "state.json"
        state = json.loads(state_path.read_text())
        state["tools"][STATE_TOOL] = {"installed": True}
        state_path.write_text(json.dumps(state))
        source_policy = self.megai / "pi-skill/delegation.md"
        source_policy.write_text(source_policy.read_text() + "\nupdated policy\n")
        checked = [agent / "AGENTS.md", agent / "skills/megai/delegation.md",
                   self.megai / "slim-wiring.json", state_path]
        originals = {path: path.read_bytes() for path in checked}
        before = self.snapshot()
        directories = {str(path.relative_to(self.root)) for path in self.root.rglob("*") if path.is_dir()}
        script = ("import sys\nfrom unittest.mock import patch\n"
                  "sys.path.insert(0, sys.argv[1])\nsys.argv = ['pi_model_policy.py']\n"
                  "from pi_model_policy import main\n"
                  "with patch('retire_local_decisions.retire_runtime', "
                  "side_effect=OSError('injected runtime move failure')):\n"
                  "    main()\n")
        result = self.run_cmd(sys.executable, "-B", "-c", script, str(self.megai / "lib"), ok=False)
        self.assertIn("injected runtime move failure", result.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual({str(path.relative_to(self.root)) for path in self.root.rglob("*") if path.is_dir()}, directories)
        self.assertTrue(runtime.is_dir())
        for path, value in originals.items():
            self.assertEqual(path.read_bytes(), value, str(path))

    def test_policy_write_failure_restores_moved_runtime(self):
        """An error after an atomic move must put the original runtime back."""
        sys.path.insert(0, str(self.megai / "lib"))
        from retire_local_decisions import RUNTIME, RUNTIME_OWNER

        self.wire()
        runtime = self.megai / RUNTIME
        self.write(runtime / ".megai-owned", f"owner={RUNTIME_OWNER}\n")
        self.write(runtime / "bin/python", "previous runtime\n")
        before = self.snapshot()
        script = ("import sys\nfrom unittest.mock import patch\n"
                  "sys.path.insert(0, sys.argv[1])\nsys.argv = ['pi_model_policy.py']\n"
                  "from slim_wiring import Plan\nfrom pi_model_policy import main\n"
                  "original = Plan.apply\n"
                  "def fail_after_move(self, dry_run, verify=False):\n"
                  "    if not dry_run: raise OSError('injected policy publish failure')\n"
                  "    return original(self, dry_run, verify)\n"
                  "with patch.object(Plan, 'apply', fail_after_move):\n    main()\n")
        result = self.run_cmd(sys.executable, "-B", "-c", script, str(self.megai / "lib"), ok=False)
        self.assertIn("injected policy publish failure", result.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(runtime.is_dir())
        self.assertFalse(list((self.megai / "backups").glob("retired-decision-runtime*")))

    def test_local_compaction_only_deduplicates_and_falls_back_to_native(self):
        """Local decisions do not discard unique history or replace Pi permissions."""
        self.wire()
        agent = self.home / ".pi/agent"
        source = (agent / "extensions/megai-laya/compaction.ts").read_text()
        self.assertIn("duplicate", source)
        self.assertIn("if (!duplicateCount", source)
        policy = " ".join((agent / "skills/megai/SKILL.md").read_text().split()).lower()
        self.assertIn("pi's native summarizer", policy)
        self.assertIn("cannot block tools", policy)

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
        sys.path.insert(0, str(self.megai / "lib"))
        from retire_local_decisions import PUBLISHED

        published = self.write(self.megai / next(iter(PUBLISHED)), "previously owned source\n")
        receipt_path = self.megai / "slim-wiring.json"
        receipt_path.write_text(json.dumps({str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                                            for path in (guard, published)}))
        self.run_cmd(sys.executable, str(self.megai / "lib/install_slim_source.py"), str(ROOT))
        self.assertFalse(guard.exists())
        self.assertFalse(published.exists())
        self.assertNotIn(str(guard), json.loads(receipt_path.read_text()))
        self.assertNotIn(str(published), json.loads(receipt_path.read_text()))
        backups = self.megai / "backups"
        self.assertTrue(any(p.is_file() and p.read_bytes() == b"legacy source guard" for p in backups.rglob("*")))

    def test_execution_and_escalation_policy_reaches_both_entrypoints(self):
        self.wire()
        agent = self.home / ".pi/agent"
        source = (self.megai / "pi-skill/delegation.md").read_text()
        installed = (agent / "skills/megai/delegation.md").read_text()
        self.assertEqual(installed, source)
        bootstrap = (agent / "AGENTS.md").read_text()
        self.assertNotIn(source.rstrip(), bootstrap)
        self.assertIn("megai/delegation.md", bootstrap)
        for rule in (
            "not according to a fixed duration",
            "Continue while making progress toward acceptance",
            "same-model retry loop",
            "suitable, available alternative",
            "at most two escalation transitions per blocker",
            "Confirm the old writer has stopped",
            "rather than killing or replaying a mutation",
            "One context handoff per task, ideally zero",
            "gathers its\n  own evidence in its own trace",
            "Judge the run end to end",
            "Cost is per delivered change, not per agent token",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, installed)

    def test_no_fixed_duration_in_reachable_policies(self):
        from slim_distribution import ROOT

        self.wire()
        relative_paths = (
            "pi-skill/SKILL.md", "pi-skill/delegation.md",
            "pi-skill/acceptance/SKILL.md", "pi-skill/acceptance/reference.md",
            "pi-skill/integration-queue.md", "skills/model-composition/routing.md",
            "skills/appllama-app-design-skill/SKILL.md",
        )
        paths = [ROOT / name for name in relative_paths]
        paths += [self.megai / name for name in relative_paths]
        agent = self.home / ".pi/agent"
        paths += [agent / "AGENTS.md"]
        for name in ("megai/SKILL.md", "megai/delegation.md", "megai-acceptance/SKILL.md",
                     "megai-acceptance/reference.md", "appllama-app-design-skill/SKILL.md"):
            paths.append(agent / "skills" / name)
        for path in paths:
            with self.subTest(path=path):
                self.assertNotRegex(path.read_text().lower(),
                                    r"five[ -]minute|5 minutes|300 seconds|slice clock|slice budget")
        self.assertIn("five-minute hard runtime", (ROOT / "skills/smart-development-orchestrator/SKILL.md").read_text())
        self.assertIn("Keep a lease alive", (ROOT / "pi-skill/integration-queue.md").read_text())

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
        bootstrap = self.megai / "pi-skill/bootstrap.md"
        bootstrap.write_text(bootstrap.read_text().replace("Raw acceptance tests", "Updated raw acceptance tests"))
        self.wire()
        instructions = (self.home / ".pi/agent/AGENTS.md").read_text()
        self.assertIn("Updated raw acceptance tests", instructions)
        self.assertNotIn("Test updated routing.", instructions)
        self.assertIn("Test updated routing.",
                      (self.home / ".pi/agent/skills/megai/delegation.md").read_text())
        self.assertEqual(instructions.count("megai:subagent-models:begin"), 1)
        receipt = json.loads((self.megai / "slim-wiring.json").read_text())
        self.assertIn(str(self.home / ".pi/agent/AGENTS.md") + "#subagent-models", receipt)
        self.wire("--verify")


def load_tests(loader, tests, pattern):
    # ModelPolicy inherits the distribution cases; do not run imported Slim twice.
    return unittest.TestSuite((loader.loadTestsFromTestCase(ModelPolicy),
                               loader.loadTestsFromTestCase(BridgeTests)))


if __name__ == "__main__":
    unittest.main()

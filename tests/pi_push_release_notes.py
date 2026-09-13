#!/usr/bin/env python3
"""Offline contracts for the per-push dual-forge release-notes policy."""
import json
import sys
import unittest

from slim_distribution import ROOT, Slim

LIFECYCLE = ROOT / "skills/agent-worktree-lifecycle/SKILL.md"


class ReleaseNotes(Slim):
    def install(self, *extra, ok=True):
        command = (sys.executable, "-B", str(self.megai / "lib/pi_model_policy.py"),
                   "--adaptive", *extra)
        return self.run_cmd(*command, ok=ok, env=self.env)

    def test_canonical_policy_is_reachable_from_installed_bootstrap(self):
        self.install()
        agent = self.home / ".pi/agent"
        bootstrap = (agent / "AGENTS.md").read_text()
        self.assertLess(len(bootstrap), 1900)
        self.assertIn("release notes on both GitHub and Forgejo", bootstrap)
        self.assertIn("agent-worktree-lifecycle", bootstrap)
        installed = agent / "skills/agent-worktree-lifecycle/SKILL.md"
        self.assertEqual(installed.read_bytes(), LIFECYCLE.read_bytes())
        self.assertIn("## Release notes for every approved push (Pi)", installed.read_text())

    def test_lifecycle_policy_covers_the_per_push_contract(self):
        text = " ".join(LIFECYCLE.read_text().split())
        for clause in (
            "## Release notes for every approved push (Pi)",
            "Pi delivery policy",
            "For Pi, every approved push",
            "it is not main-only",
            "both configured forges (GitHub and Forgejo)",
            "existing target repo identity/remote",
            "then draft the notes",
            "missing, unmapped or unauthorized required forge is BLOCKED",
            "never treat it as success",
            "invent a project/remote or expose private code to a new host",
            "queue reservation is not push approval",
            "existing main/push approval boundary is unchanged",
            "GitHub/Forgejo **Release**",
            "release bodies, not merely commit or PR text",
            "old/new full SHA and ref",
            "actual verified pushed range",
            "explicitly selected baseline or a clearly identified initial-history scope",
            "never assume `HEAD^`",
            "skips a new release but still reconciles any previously pending note",
            "`pi`, `dev` and `task/...`",
            "**prerelease**",
            "never latest",
            "agreed release convention",
            "never guess or increment a semantic version",
            "deterministic collision-safe snapshot tag",
            "`push/<hash-of-full-ref>/<full-new-commit-SHA>`",
            "pinned to that commit identically on both forges",
            "Look up an existing release by tag before creating",
            "conflicting tag identity is BLOCKED",
            "capture an operation identity per ref",
            "Verify the remote ref first",
            "read back the exact target commit",
            "peeled commit must equal the intended immutable commit",
            "only a branch/ref target may move",
            "one deterministic operation identity per push",
            "reconciled by tag lookup before any retry",
            "changes, fixes, breaking migration, actual tests, risks and safe source links",
            "Never copy secrets, PII or private tracker content",
            "reconciles read-only",
            "preserve the journal and queue",
            "keep any published success on one forge",
            "report push success separately from release failure",
            "never roll back a successful push",
            "resume only the missing forge",
            ("without re-pushing successful refs, duplicating releases "
             "or overwriting human-written text"),
            "agent instruction, not enforcement",
            "installs no git hook",
            "manual pushes outside this workflow are not intercepted",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, text)

    def test_focused_install_parity_idempotence_backup_and_user_state(self):
        agent = self.home / ".pi/agent"
        user_policy = "# User policy\nKeep my custom instructions.\n"
        self.write(agent / "AGENTS.md", user_policy)
        settings = {"defaultProvider": "user-provider", "defaultModel": "user-model",
                    "defaultThinkingLevel": "low", "packages": ["custom-package"],
                    "extensions": ["user-extension"], "userSetting": {"keep": True}}
        self.write(agent / "settings.json", json.dumps(settings))
        auth = self.write(agent / "auth.json", '{"fixture":"preserve"}\n')
        before = self.snapshot()
        self.install("--check")
        self.assertEqual(before, self.snapshot())
        self.install()
        installed = (agent / "AGENTS.md").read_text()
        self.assertTrue(installed.startswith(user_policy))
        self.assertIn("<!-- megai:slim:begin -->", installed)
        self.assertIn("release notes on both GitHub and Forgejo", installed)
        self.assertEqual((agent / "skills/agent-worktree-lifecycle/SKILL.md").read_bytes(),
                         LIFECYCLE.read_bytes())
        self.assertEqual((agent / "skills/megai-task-flow/SKILL.md").read_bytes(),
                         (ROOT / "task-flow/skills/megai-task-flow/SKILL.md").read_bytes())
        wired = json.loads((agent / "settings.json").read_text())
        for key, value in settings.items():
            self.assertEqual(wired[key], value)
        self.assertEqual(auth.read_text(), '{"fixture":"preserve"}\n')
        self.assertTrue(any(path.is_file() and path.read_bytes() == user_policy.encode()
                            for path in (self.megai / "backups").rglob("*")))
        stable = self.snapshot()
        self.install()
        self.install()
        self.assertEqual(stable, self.snapshot())

    def test_focused_install_refuses_unowned_asset_collision(self):
        target = self.home / ".pi/agent/skills/agent-worktree-lifecycle/SKILL.md"
        self.write(target, "user-owned lifecycle policy\n")
        before = self.snapshot()
        result = self.install(ok=False)
        self.assertIn("custom/legacy asset preserved", result.stderr)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(target.read_text(), "user-owned lifecycle policy\n")


def load_tests(loader, tests, pattern):
    # Reuse sandbox helpers, not the entire inherited distribution suite twice.
    return unittest.TestSuite(ReleaseNotes(name) for name in ReleaseNotes.__dict__
                              if name.startswith("test_"))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Offline contracts for per-push GitHub notes and ADAM-only Forgejo notes."""
import hashlib
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
        self.assertIn("every approved push needs GitHub release notes", bootstrap)
        self.assertIn("Forgejo is required only for ADAM and its component repositories",
                      " ".join(bootstrap.split()))
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
            "GitHub for every project, plus Forgejo only for ADAM and its component repositories",
            "verified existing umbrella project identity and documented repository mapping",
            "`ADAM full` in Plane",
            "component repositories and linked worktrees inherit that identity",
            "Never infer ADAM membership from a branch name, checkout basename or remote alias",
            "Ambiguous identity is BLOCKED before selecting destinations",
            "Non-ADAM projects (including SPMAPP and MEGAI) use GitHub only under this rule",
            "missing Forgejo does not block them",
            "Do not preflight, create or register Forgejo resources for non-ADAM projects",
            "This scope rule grants no new push destination",
            "preflight only the required destinations",
            "existing target repo identity/remote",
            "then draft the notes",
            "missing, unmapped or unauthorized required forge is BLOCKED",
            "never treat it as success",
            "invent a project/remote or expose private code to a new host",
            "queue reservation is not push approval",
            "existing main/push approval boundary is unchanged",
            "Publish a **Release** for the same pinned commit on every required destination",
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
            "The branch snapshot tag is `push/<ref-digest>/<full-new-commit-SHA>`",
            ("`ref-digest` is the full 64 lowercase hex SHA-256 of the exact fully "
             "qualified ref name's UTF-8 bytes"),
            "with no newline, truncation or normalization",
            "Look up an existing release by tag before creating",
            "conflicting tag identity is BLOCKED",
            "one persisted push journal ID",
            "created before any mutation and reused on every retry",
            "one deterministic per-ref publication identity",
            "exact fully qualified ref plus its intended peeled commit",
            "the snapshot tag above for a branch, or the already-approved tag for a tag push",
            "Reuse that same per-ref identity on all required destinations and every retry",
            "never mint a fresh ID for missing-side recovery",
            "Verify the remote ref first",
            "read back the exact target commit",
            "peeled commit must equal the intended immutable commit",
            "only a branch/ref target may move",
            "reconciled by tag lookup before any retry",
            "changes, fixes, breaking migration, actual tests, risks and safe source links",
            "Never copy secrets, PII or private tracker content",
            "reconciles read-only",
            "preserve the journal and queue",
            "keep any published success on one forge",
            "report push success separately from release failure",
            "never roll back a successful push",
            "resume only the missing required destination",
            ("without re-pushing successful refs, duplicating releases "
             "or overwriting human-written text"),
            "agent instruction, not enforcement",
            "installs no git hook",
            "manual pushes outside this workflow are not intercepted",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, text)

    def test_snapshot_tag_digest_is_canonical_and_golden(self):
        policy = " ".join(LIFECYCLE.read_text().split())
        golden = "a4ff746fc8339e348c9018b8e701f2b4a547b36e6409099b9e4ac9c894e749df"
        digest = hashlib.sha256(b"refs/heads/pi").hexdigest()
        self.assertEqual(digest, golden)
        self.assertRegex(digest, r"\A[0-9a-f]{64}\Z")
        self.assertIn("`refs/heads/pi` -> `" + golden + "`", policy)
        self.assertIn("push/<ref-digest>/<full-new-commit-SHA>", policy)

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
        self.assertIn("every approved push needs GitHub release notes", installed)
        self.assertIn("Forgejo is required only for ADAM and its component repositories",
                      " ".join(installed.split()))
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

#!/usr/bin/env python3
"""Dependency-free Pi policy/CLI checks, with optional installed-profile read-back."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RETIRED = "pa" + "seo"
ACTIVE = (
    "README.md", "bin/megai", "lib/integration_queue.py", "lib/slim_wiring.py",
    "pi-defaults/AGENTS.md", "pi-defaults/install.py", "pi-defaults/workflow.py",
    "pi-defaults/skills/pi-workflow/SKILL.md", "pi-defaults/skills/code-review/SKILL.md",
    "pi-defaults/prompts/factory.md", "pi-defaults/prompts/mdev.md",
    "pi-defaults/projects/ADAM.md", "pi-skill/bootstrap.md",
    "pi-skill/delegation.md", "pi-skill/integration-queue.md",
    "pi-skill/workspace-guard/identity.mjs", "pi-skill/acceptance/reference.md",
    "skills/agent-worktree-lifecycle/SKILL.md", "task-flow/skills/megai-task-flow/SKILL.md",
    "task-flow/skills/task-flow/SKILL.md",
)
INSTALLED = (
    "AGENTS.md", "workflow.py", "verify.mjs", "skills/pi-workflow/SKILL.md",
    "skills/code-review/SKILL.md", "prompts/factory.md", "prompts/mdev.md",
    "projects/ADAM.md",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*argv, cwd=None):
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=10)


class RetiredDependency(unittest.TestCase):
    def test_active_pi_assets_have_no_external_workspace_dependency(self):
        for name in ACTIVE:
            with self.subTest(name=name):
                path = ROOT / name
                self.assertTrue(path.is_file(), name)
                self.assertNotIn(RETIRED, path.read_text().lower(), name)
        self.assertFalse((ROOT / "pi-skill/workspace-guard/index.ts").exists())
        profile = ROOT / "pi-defaults/workflow.py"
        self.assertNotIn("status", run(sys.executable, "-B", str(profile), "--help").stdout.split("{", 1)[1].split("}", 1)[0])

    def test_workflow_context_resolves_linked_git_worktree_without_registry(self):
        with tempfile.TemporaryDirectory(prefix="pi-retired-identity-") as folder:
            root = Path(folder)
            repo = (root / "repo").resolve()
            repo.mkdir()
            for args in (("init", "-b", "dev"), ("config", "user.name", "Fixture"),
                         ("config", "user.email", "fixture@example.invalid")):
                self.assertEqual(run("git", *args, cwd=repo).returncode, 0)
            (repo / "file").write_text("first\n")
            self.assertEqual(run("git", "add", "file", cwd=repo).returncode, 0)
            self.assertEqual(run("git", "commit", "-m", "base", cwd=repo).returncode, 0)
            linked = root / "task"
            self.assertEqual(run("git", "worktree", "add", "-b", "task/change", str(linked), cwd=repo).returncode, 0)
            result = run(sys.executable, "-B", str(ROOT / "pi-defaults/workflow.py"),
                         "context", "--cwd", str(linked))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(json.loads(result.stdout)["repository"]).resolve(), repo)
            identity = run("node", str(ROOT / "pi-skill/workspace-guard/identity.mjs"),
                           "--root", str(linked))
            self.assertEqual(identity.returncode, 0, identity.stderr)
            self.assertEqual(Path(json.loads(identity.stdout)["root"]).resolve(), repo)

    def test_corrupt_git_metadata_does_not_fall_back_to_directory_identity(self):
        with tempfile.TemporaryDirectory(prefix="pi-identity-corrupt-") as folder:
            path = Path(folder)
            (path / ".git").write_text("gitdir: /no/such/gitdir\n")
            config = path / ".pi"
            config.mkdir()
            (config / "project.json").write_text('{"layout":"mono","repositories":["."]}')
            result = run("node", str(ROOT / "pi-skill/workspace-guard/identity.mjs"),
                         "--root", str(path))
            self.assertEqual(result.returncode, 2)
            self.assertIn("Git metadata exists", result.stderr)

    def test_umbrella_does_not_adopt_foreign_symlinked_repository(self):
        with tempfile.TemporaryDirectory(prefix="pi-identity-foreign-") as folder:
            root = Path(folder)
            umbrella = root / "umbrella"
            config = umbrella / ".pi"
            config.mkdir(parents=True)
            foreign = root / "foreign"
            foreign.mkdir()
            (umbrella / "foreign").symlink_to(foreign, target_is_directory=True)
            (config / "project.json").write_text('{"layout":"multi","repositories":["foreign"]}')
            result = run("node", str(ROOT / "pi-skill/workspace-guard/identity.mjs"),
                         "--root", str(umbrella))
            self.assertEqual(result.returncode, 2)
            self.assertIn("symlink escapes", result.stderr)

    def test_installed_defaults(self):
        defaults = Path.home() / ".pi/agent/defaults"
        for name in INSTALLED:
            with self.subTest(name=name):
                source = ROOT / "pi-defaults" / name
                target = defaults / name
                self.assertTrue(target.is_file() and not target.is_symlink(), name)
                self.assertEqual(digest(target), digest(source), name)
        self.assertNotIn(RETIRED, (defaults / "AGENTS.md").read_text().lower())
        self.assertNotIn(RETIRED, (defaults / "workflow.py").read_text().lower())
        self.assertNotIn(RETIRED, (Path.home() / ".pi/agent/AGENTS.md").read_text().lower())

    def test_preserved_snapshot(self):
        expected = "d95b45b3d7ee9d1f85b1b38604c40d5f3cd1dd615e8b7fbed7740131f560283e"
        backup = Path.home() / ".megai/evidence/megai-171-pi-no-paseo/codedb.snapshot.user-approved"
        self.assertEqual(digest(backup), expected)
        self.assertEqual(digest(ROOT / "codedb.snapshot"), expected)
        main = run("git", "rev-parse", "--path-format=absolute", "--git-common-dir", cwd=ROOT)
        self.assertEqual(main.returncode, 0, main.stderr)
        primary = Path(main.stdout.strip()).parent
        self.assertEqual(run("git", "status", "--porcelain", cwd=primary).stdout, "")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--snapshot", action="store_true")
    args = parser.parse_args()
    names = ["test_installed_defaults"] if args.live else (["test_preserved_snapshot"] if args.snapshot else [
        "test_active_pi_assets_have_no_external_workspace_dependency",
        "test_workflow_context_resolves_linked_git_worktree_without_registry",
        "test_corrupt_git_metadata_does_not_fall_back_to_directory_identity",
        "test_umbrella_does_not_adopt_foreign_symlinked_repository",
    ])
    suite = unittest.TestSuite(RetiredDependency(name) for name in names)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)

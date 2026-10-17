"""Real disposable Git/queue integration tests; never use production queue/remotes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "lib/task_runner.py"
QUEUE = ROOT / "lib/integration_queue.py"


class TaskRunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.primary = self.root / "repo"
        self.worktree = self.root / "task"
        self.remote = self.root / "remote.git"
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(MEGAI_QUEUE_HOME=str(self.root / "queue"), PYTHONDONTWRITEBYTECODE="1",
                        GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
        self.task = str(uuid.uuid4())
        self.project = str(uuid.uuid4())
        self.run_command(["git", "init", "--bare", str(self.remote)])
        self.run_command(["git", "init", "-b", "dev", str(self.primary)])
        self.git("config", "user.name", "Task Test")
        self.git("config", "user.email", "task@example.invalid")
        (self.primary / "base.txt").write_text("base\n")
        self.git("add", "base.txt")
        self.git("commit", "-m", "base")
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "-u", "origin", "dev")
        self.base = self.git("rev-parse", "HEAD")
        self.directory = self.primary / ".git/megai-tasks" / self.task

    def run_command(self, command, expected=0, cwd=None):
        result = subprocess.run(command, cwd=cwd, env=self.env, text=True,
                                capture_output=True, timeout=60)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result.stdout.strip()

    def git(self, *words, path=None):
        return self.run_command(["git", "-C", str(path or self.primary), *words])

    def cli(self, action, *words, expected=0):
        result = subprocess.run([sys.executable, "-B", str(RUNNER), action,
                                 "--root", str(self.primary), "--task", self.task, *words],
                                env=self.env, text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def start(self):
        self.cli("start", "--project", self.project, "--worktree", str(self.worktree), "--plane-current")

    def candidate(self):
        (self.worktree / "change.txt").write_text("task\n")
        self.git("add", "change.txt", path=self.worktree)
        self.git("commit", "-m", "task change", path=self.worktree)
        self.sha = self.git("rev-parse", "HEAD", path=self.worktree)

    def verify(self, command="git diff --exit-code && test -f change.txt"):
        return self.cli("verify", "--check", command)

    def prepared(self):
        self.start()
        self.candidate()
        self.verify()

    def deliver(self, expected=0, sha=None):
        return self.cli("deliver", "--plane-current", "--targets-idle", "--reviewed-sha", sha or self.sha, expected=expected)

    def queue_rows(self):
        output = self.run_command([sys.executable, "-B", str(QUEUE), "status"])
        return json.loads(output)

    def test_happy_delivery_and_no_cleanup(self):
        self.prepared()
        self.cli("ready")
        delivery = json.loads(self.deliver().stdout)
        self.assertEqual(delivery["state"], "verified")
        self.assertEqual(delivery["observed_remote"], self.sha)
        self.assertEqual(self.git("rev-parse", "dev"), self.sha)
        self.assertEqual(self.run_command(["git", "--git-dir", str(self.remote), "rev-parse", "dev"]), self.sha)
        self.assertTrue(self.worktree.is_dir())
        self.assertEqual(self.queue_rows()[0]["state"], "completed")
        self.deliver(expected=2)  # no replay

    def test_primary_dirty_does_not_block_implementation_or_checks(self):
        (self.primary / "foreign.txt").write_text("preserve me")
        self.prepared()
        self.cli("ready", expected=2)
        self.deliver(expected=2)
        self.assertEqual((self.primary / "foreign.txt").read_text(), "preserve me")
        self.assertFalse((self.directory / "delivery.json").exists())

    def test_dirty_task_blocks_verification(self):
        self.start()
        self.candidate()
        (self.worktree / "change.txt").write_text("dirty")
        self.cli("verify", "--check", "true", expected=2)

    def test_timed_out_check_kills_child_writers(self):
        self.prepared()
        self.cli("verify", "--timeout", "1", "--check",
                 "(sleep 2; echo orphan >> change.txt) & wait", expected=2)
        time.sleep(1.5)
        self.assertEqual((self.worktree / "change.txt").read_text(), "task\n")
        self.cli("ready", expected=2)

    def test_start_refuses_nested_foreign_worktree(self):
        other = self.root / "other-task"
        self.git("worktree", "add", "-b", "foreign-task", str(other), "dev")
        self.cli("start", "--project", self.project, "--worktree", str(other / "nested"),
                 "--plane-current", expected=2)
        self.assertFalse((other / "nested").exists())

    def test_failed_check_invalidates_old_success(self):
        self.prepared()
        self.cli("verify", "--check", "false", expected=2)
        self.cli("ready", expected=2)
        self.assertFalse(json.loads((self.directory / "verification.json").read_text())["passed"])

    def test_stale_candidate_blocks(self):
        self.prepared()
        self.git("commit", "--allow-empty", "-m", "new candidate", path=self.worktree)
        self.cli("ready", expected=2)
        self.deliver(expected=2)

    def test_explicit_authority_and_idle_attestations_required(self):
        self.prepared()
        self.cli("deliver", "--reviewed-sha", self.sha, expected=2)
        self.cli("deliver", "--plane-current", "--reviewed-sha", self.sha, expected=2)
        self.assertFalse((self.directory / "delivery.json").exists())

    def test_busy_primary_blocks_delivery(self):
        self.prepared()
        marker = self.primary / ".git/CHERRY_PICK_HEAD"
        marker.write_text(self.base)
        self.deliver(expected=2)
        self.assertTrue(marker.exists())

    def test_ignored_collision_blocks_local_merge(self):
        self.prepared()
        (self.primary / ".git/info/exclude").write_text("change.txt\n")
        (self.primary / "change.txt").write_text("private ignored data\n")
        self.deliver(expected=2)
        self.assertEqual((self.primary / "change.txt").read_text(), "private ignored data\n")
        self.assertEqual(self.git("rev-parse", "dev"), self.base)
        self.assertEqual(self.queue_rows()[0]["state"], "held")

    def test_readiness_has_no_queue_or_network_writes(self):
        self.prepared()
        self.remote.rename(self.root / "offline.git")
        self.cli("ready")
        self.assertFalse((self.root / "queue").exists())

    def test_task_branch_switch_invalidates_ownership(self):
        self.prepared()
        self.git("switch", "-c", "unknown-writer", path=self.worktree)
        self.cli("ready", expected=2)
        self.deliver(expected=2)

    def test_exact_review_required(self):
        self.prepared()
        self.deliver(expected=2, sha=self.base)
        self.assertFalse((self.directory / "delivery.json").exists())

    def test_primary_branch_switch_blocks(self):
        self.prepared()
        self.git("switch", "-c", "foreign")
        self.deliver(expected=2)
        self.assertEqual(self.git("branch", "--show-current"), "foreign")

    def test_origin_push_url_mismatch_blocks(self):
        self.prepared()
        self.git("remote", "set-url", "--push", "origin", str(self.root / "other.git"))
        self.deliver(expected=2)
        self.assertEqual(self.git("rev-parse", "dev"), self.base)

    def test_remote_advance_blocks_without_integration(self):
        self.prepared()
        other = self.root / "other"
        self.run_command(["git", "clone", "-b", "dev", str(self.remote), str(other)])
        self.git("config", "user.name", "Other", path=other)
        self.git("config", "user.email", "other@example.invalid", path=other)
        self.git("commit", "--allow-empty", "-m", "foreign", path=other)
        self.git("push", "origin", "dev", path=other)
        self.deliver(expected=2)
        self.assertEqual(self.git("rev-parse", "dev"), self.base)

    def test_divergence_blocks_without_rebase(self):
        self.prepared()
        self.git("commit", "--allow-empty", "-m", "parallel dev")
        self.git("push", "origin", "dev")
        self.cli("verify", "--check", "true", expected=2)
        self.deliver(expected=2)
        self.assertEqual(self.git("rev-parse", "HEAD", path=self.worktree), self.sha)

    def test_push_failure_holds_partial_delivery(self):
        self.prepared()
        hook = self.remote / "hooks/pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o700)
        self.deliver(expected=2)
        self.assertEqual(self.git("rev-parse", "dev"), self.sha)
        self.assertEqual(self.run_command(["git", "--git-dir", str(self.remote), "rev-parse", "dev"]), self.base)
        self.assertEqual(self.queue_rows()[0]["state"], "held")
        self.assertEqual(json.loads((self.directory / "delivery.json").read_text())["state"], "local-integrated")
        self.deliver(expected=2)

    def test_per_worktree_queue_home_is_rejected(self):
        self.prepared()
        self.env["MEGAI_QUEUE_HOME"] = str(self.worktree / ".private-queue")
        self.deliver(expected=2)
        self.assertFalse((self.worktree / ".private-queue").exists())
        self.assertEqual(self.git("rev-parse", "dev"), self.base)

    def test_interrupted_start_intent_is_not_replayed(self):
        self.directory.mkdir(parents=True)
        (self.directory / "intent.json").write_text("{}")
        self.cli("start", "--project", self.project, "--worktree", str(self.worktree),
                 "--plane-current", expected=2)
        self.assertFalse(self.worktree.exists())

    def test_queue_contention_does_not_integrate(self):
        self.prepared()
        plan = self.run_command([sys.executable, "-B", str(QUEUE), "plan", "--root", str(self.primary),
                                 "--id", "foreign-reservation", "--plane-project", self.project,
                                 "--plane-item", str(uuid.uuid4()), "--repo", str(self.primary), self.sha])
        request = self.root / "foreign-request.json"
        request.write_text(plan)
        self.run_command([sys.executable, "-B", str(QUEUE), "enqueue", "--request", str(request)])
        self.deliver(expected=2)
        self.assertEqual(self.git("rev-parse", "dev"), self.base)
        self.assertEqual(len(self.queue_rows()), 2)
        self.assertTrue(all(row["state"] == "queued" for row in self.queue_rows()))

    def test_start_never_reuses_unknown_path_or_task(self):
        self.worktree.mkdir()
        self.cli("start", "--project", self.project, "--worktree", str(self.worktree),
                 "--plane-current", expected=2)
        self.worktree.rmdir()
        self.start()
        self.cli("start", "--project", self.project, "--worktree", str(self.worktree),
                 "--plane-current", expected=2)

    def test_check_source_mutation_is_not_accepted(self):
        self.start()
        self.candidate()
        self.cli("verify", "--check", "echo changed >> change.txt", expected=2)
        self.cli("ready", expected=2)

    def test_no_background_services_and_no_queue_during_tests(self):
        started = time.monotonic()
        self.prepared()
        self.assertFalse((self.root / "queue").exists())
        self.assertLess(time.monotonic() - started, 30)


if __name__ == "__main__":
    unittest.main()

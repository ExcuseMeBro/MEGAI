"""Additional task lifecycle safety checks using disposable fixture resources."""
import json
from pathlib import Path
import sys
import unittest

from task_runner_test import TaskRunnerTest as Fixture


class LifecycleSafetyTest(unittest.TestCase):
    # Reuse only fixture methods, not the baseline's full test suite.
    setUp = Fixture.setUp
    run_command = Fixture.run_command
    git = Fixture.git
    cli = Fixture.cli
    start = Fixture.start
    candidate = Fixture.candidate
    verify = Fixture.verify
    prepared = Fixture.prepared
    deliver = Fixture.deliver
    queue_rows = Fixture.queue_rows

    wait_for_foreign = Fixture.test_queue_contention_does_not_integrate

    def test_changed_waiting_candidate_cannot_reuse_old_request(self):
        self.wait_for_foreign()
        self.git("commit", "--allow-empty", "-m", "changed", path=self.worktree)
        self.sha = self.git("rev-parse", "HEAD", path=self.worktree)
        self.verify()
        result = self.deliver(expected=2)
        self.assertIn("Waiting delivery pins changed", result.stderr)
        self.assertEqual(len(self.queue_rows()), 2)
        self.assertEqual(self.git("rev-parse", "dev"), self.base)

    def test_uncertain_claim_is_not_replayed(self):
        self.wait_for_foreign()
        path = self.directory / "delivery.json"
        value = json.loads(path.read_text())
        value["state"] = "claim-intent"
        path.write_text(json.dumps(value))
        self.assertIn("never blindly replay", self.deliver(expected=2).stderr)
        self.assertEqual(len(self.queue_rows()), 2)

    def test_changed_waiting_queue_request_is_not_replayed(self):
        self.wait_for_foreign()
        path = self.directory / "request.json"
        value = json.loads(path.read_text())
        value["id"] = "not-the-same-request"
        path.write_text(json.dumps(value))
        self.assertIn("Waiting request changed", self.deliver(expected=2).stderr)
        self.assertEqual(self.git("rev-parse", "dev"), self.base)

    def test_finish_retains_empty_untracked_directory(self):
        self.prepared()
        empty = self.worktree / "empty-user-directory"
        empty.mkdir()
        result = self.cli("finish", "--plane-current", "--targets-idle", "--cleanup-released",
                          "--reviewed-sha", self.sha)
        self.assertEqual(json.loads(result.stdout)["cleanup"]["state"], "retained")
        self.assertTrue(empty.is_dir())
        self.assertEqual(self.queue_rows()[0]["state"], "completed")

    def test_finish_retains_callers_current_worktree(self):
        self.prepared()
        runner = Path(__file__).resolve().parents[1] / "lib/task_runner.py"
        output = self.run_command([sys.executable, "-B", str(runner), "finish", "--root",
                                   str(self.primary), "--task", self.task, "--plane-current",
                                   "--targets-idle", "--cleanup-released", "--reviewed-sha", self.sha],
                                  cwd=self.worktree)
        result = json.loads(output)
        self.assertEqual(result["cleanup"]["state"], "retained")
        self.assertIn("Current process", result["cleanup"]["reason"])
        self.assertTrue(self.worktree.is_dir())
        self.assertEqual(self.queue_rows()[0]["state"], "completed")


# Avoid collecting the imported fixture's tests again.
del Fixture

if __name__ == "__main__":
    unittest.main()

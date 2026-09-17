#!/usr/bin/env python3
"""Public CLI integration checks, using only disposable local Git/SQLite fixtures."""

import concurrent.futures
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
CLI = [sys.executable, "-B", str(ROOT / "lib/integration_queue.py")]


class QueueCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="megai-queue-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / "product"
        self.project.mkdir()
        self.home = self.base / "queue"
        self.paseo = self.base / "paseo"
        (self.paseo / "projects").mkdir(parents=True)
        self.env = {**os.environ, "PASEO_HOME": str(self.paseo)}
        self.register(self.project)
        self.repos = {}
        for name in ("backend", "frontend", "mobile"):
            path = self.project / name
            path.mkdir()
            self.git(path, "init", "-b", "dev")
            self.git(path, "config", "user.email", "fixture@example.invalid")
            self.git(path, "config", "user.name", "Queue fixture")
            (path / "file").write_text("base\n")
            self.git(path, "add", "file")
            self.git(path, "commit", "-m", "base")
            self.git(path, "checkout", "-b", "task/change")
            (path / "file").write_text("candidate\n")
            self.git(path, "commit", "-am", "candidate")
            self.git(path, "checkout", "dev")
            self.repos[name] = path
        self.proof = self.base / "recovery.txt"
        self.proof.write_text("Fixture owner stopped; inspected target vectors and working trees.\n")

    def register(self, path):
        (self.paseo / "projects/projects.json").write_text(json.dumps([
            {"projectId": "prj_fixture", "rootPath": str(path), "archivedAt": None}
        ]))

    def git(self, path, *args):
        env = {k: v for k, v in self.env.items() if not k.startswith("GIT_")}
        result = subprocess.run(["git", "-C", str(path), *args], env=env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def call(self, *args, code=0):
        result = subprocess.run([*CLI, "--home", str(self.home), *map(str, args)],
                                env=self.env, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def request(self, key, *repos, after=(), target=None):
        args = ["plan", "--root", str(self.project), "--id", key,
                "--plane-project", "00000000-0000-4000-8000-000000000001",
                "--plane-item", str(uuid.uuid5(uuid.NAMESPACE_URL, key))]
        for name in repos:
            args += ["--repo", str(self.repos[name]), "task/change"]
        for dependency in after:
            args += ["--after", dependency]
        if target:
            args += ["--target-branch", target]
        value = self.call(*args)
        file = self.base / (key + ".json")
        file.write_text(json.dumps(value))
        return file

    def enqueue(self, key, *repos, after=()):
        file = self.request(key, *repos, after=after)
        return self.call("enqueue", "--request", file)

    def claim(self, key, owner="parent", code=0, lease=120):
        return self.call("claim", "--id", key, "--owner", owner,
                         "--lease-seconds", lease, code=code)

    def finish(self, grant, outcome="failed", code=0):
        return self.call("finish", "--id", grant["id"], "--owner", grant["owner"],
                         "--token", grant["token"], "--outcome", outcome, code=code)

    def test_idempotency_and_independent_fifo_resources(self):
        original = self.enqueue("first", "backend")
        duplicate = self.call("enqueue", "--request", self.base / "first.json")
        self.assertEqual(original["seq"], duplicate["seq"])
        self.enqueue("second", "backend", "frontend")
        self.enqueue("third", "frontend")
        self.enqueue("independent", "mobile")
        first = self.claim("first")
        self.assertEqual(self.claim("second", code=2)["wait_reason"], "resource:first")
        self.assertEqual(self.claim("third", code=2)["wait_reason"], "fifo:second")
        self.assertEqual(self.claim("independent")["state"], "active")
        self.finish(first)
        second = self.claim("second")
        self.assertEqual(self.claim("third", code=2)["wait_reason"], "resource:second")
        self.finish(second)
        self.assertEqual(self.claim("third")["state"], "active")

    def test_concurrent_claims_have_exactly_one_owner(self):
        self.enqueue("same", "backend", "frontend")
        def attempt(i):
            result = subprocess.run([*CLI, "--home", str(self.home), "claim", "--id", "same",
                                     "--owner", f"owner-{i}"], env=self.env,
                                    capture_output=True, text=True, timeout=20)
            return result.returncode, json.loads(result.stdout)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            values = list(pool.map(attempt, range(8)))
        winners = [v for code, v in values if code == 0]
        self.assertEqual(len(winners), 1, values)
        self.assertEqual(sum(code == 2 for code, _ in values), 7)
        repeated = self.claim("same", winners[0]["owner"])
        self.assertEqual(repeated["token"], winners[0]["token"])

    def test_expiry_retains_lock_and_reconciliation_fences_old_token(self):
        self.enqueue("old", "backend")
        self.enqueue("next", "backend")
        old = self.claim("old", lease=1)
        time.sleep(1.1)
        self.assertEqual(self.claim("next", code=2)["wait_reason"], "reconcile:old")
        self.finish(old, code=2)
        result = self.call("reconcile", "--id", "old", "--outcome", "retry",
                           "--owner-stopped", "--evidence", self.proof)
        self.assertEqual(result["state"], "queued")
        fresh = self.claim("old", "replacement")
        self.assertNotEqual(old["token"], fresh["token"])
        self.finish(old, code=2)
        self.finish(fresh)
        self.assertEqual(self.claim("next")["state"], "active")

    def test_partial_delivery_keeps_all_locks(self):
        self.enqueue("bundle", "backend", "frontend")
        grant = self.claim("bundle")
        self.git(self.repos["backend"], "merge", "--ff-only", "task/change")
        self.finish(grant, "completed", code=2)
        self.call("reconcile", "--id", "bundle", "--outcome", "retry", "--owner-stopped",
                  "--evidence", self.proof, code=2)
        self.assertEqual(self.call("status", "--id", "bundle")["state"], "active")
        self.git(self.repos["frontend"], "merge", "--ff-only", "task/change")
        self.assertEqual(self.finish(grant, "completed")["state"], "completed")

    def test_monorepo_and_worktree_map_to_one_primary(self):
        self.register(self.repos["backend"])
        self.project = self.repos["backend"]
        linked = self.base / "linked"
        self.git(self.project, "worktree", "add", "--detach", str(linked), "task/change")
        self.addCleanup(lambda: self.git(self.project, "worktree", "remove", str(linked)))
        self.repos["linked"] = linked
        direct = json.loads(self.request("direct", "backend").read_text())
        other = json.loads(self.request("linked", "linked").read_text())
        self.assertEqual(direct["repositories"], other["repositories"])
        self.assertEqual(other["repositories"][0]["path"], str(self.project.resolve()))
        self.assertFalse(self.home.exists(), "plan must not create queue state")

    def test_dependencies_cancel_and_unrelated_ready_progress(self):
        self.enqueue("dependency", "backend")
        self.enqueue("dependent", "frontend", after=["dependency"])
        self.enqueue("ready", "frontend")
        self.assertEqual(self.claim("dependent", code=2)["wait_reason"], "dependency:dependency:queued")
        ready = self.claim("ready")
        self.finish(ready)
        self.call("cancel", "--id", "dependency", "--reason", "User cancelled")
        self.assertEqual(self.claim("dependent", code=2)["wait_reason"], "dependency:dependency:cancelled")
        self.assertEqual(self.call("cancel", "--id", "dependent", "--reason", "Dependency cancelled")["state"], "cancelled")
        file = self.request("unknown", "mobile", after=["not-enqueued"])
        self.assertIn("Dependencies", self.call("enqueue", "--request", file, code=2)["reason"])

    def test_stale_vector_refresh_preserves_position_and_rechecks_target(self):
        original = self.enqueue("stale", "backend")
        path = self.repos["backend"]
        (path / "other").write_text("other change\n")
        self.git(path, "add", "other")
        self.git(path, "commit", "-m", "new base")
        self.assertIn("Commit vector", self.claim("stale", code=2)["reason"])
        fresh = self.request("stale", "backend")
        self.call("enqueue", "--request", fresh, code=2)
        refreshed = self.call("refresh", "--request", fresh, "--evidence", self.proof)
        self.assertEqual(refreshed["seq"], original["seq"])
        grant = self.claim("stale")
        self.call("refresh", "--request", fresh, "--evidence", self.proof, code=2)
        self.finish(grant)

    def test_dirty_target_and_branch_change_never_release_or_claim(self):
        self.enqueue("dirty", "backend")
        path = self.repos["backend"]
        (path / "untracked").write_text("preserve me")
        self.assertIn("dirty", self.claim("dirty", code=2)["reason"])
        (path / "untracked").unlink()
        grant = self.claim("dirty")
        (path / "file").write_text("unfinished changes")
        self.assertIn("dirty", self.finish(grant, code=2)["reason"])
        self.assertEqual((path / "file").read_text(), "unfinished changes")
        (path / "file").write_text("base\n")
        self.git(path, "checkout", "task/change")
        self.assertIn("branch changed", self.finish(grant, code=2)["reason"])
        self.git(path, "checkout", "dev")
        self.finish(grant)

    def test_bounded_wait_wakes_after_release_and_does_not_reenqueue(self):
        self.enqueue("holder", "backend")
        initial = self.enqueue("waiter", "backend")
        holder = self.claim("holder")
        def wait():
            return self.call("claim", "--id", "waiter", "--owner", "waiting-parent", "--wait-seconds", "4")
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(wait)
            time.sleep(0.4)
            self.finish(holder)
            result = future.result(timeout=10)
        self.assertEqual(result["seq"], initial["seq"])
        self.assertEqual(result["state"], "active")
        self.call("cancel", "--id", "waiter", "--reason", "unsafe", code=2)
        self.enqueue("timeout", "backend")
        start = time.monotonic()
        self.call("claim", "--id", "timeout", "--owner", "timeout-parent", "--wait-seconds", "1", code=2)
        self.assertLess(time.monotonic() - start, 4)

    def test_partial_crash_resume_only_remaining_repos_and_fences_old_owner(self):
        self.enqueue("partial", "backend", "frontend")
        old = self.claim("partial")
        self.git(self.repos["backend"], "merge", "--ff-only", "task/change")
        self.call("hold", "--id", "partial", "--owner", old["owner"], "--token", old["token"],
                  "--reason", "Executor disconnected after backend delivery")
        self.call("reconcile", "--id", "partial", "--outcome", "resume", "--owner", "new-owner",
                  "--evidence", self.proof, code=2)
        resumed = self.call("reconcile", "--id", "partial", "--outcome", "resume", "--owner", "new-owner",
                            "--owner-stopped", "--evidence", self.proof)
        self.assertEqual(resumed["remaining_repositories"], [str(self.repos["frontend"].resolve())])
        self.finish(old, "completed", code=2)
        self.git(self.repos["frontend"], "merge", "--ff-only", "task/change")
        self.assertEqual(self.finish(resumed, "completed")["state"], "completed")

    def test_unresolved_git_operation_blocks_even_when_tree_is_clean(self):
        self.enqueue("operation", "backend")
        path = self.repos["backend"]
        self.git(path, "checkout", "-b", "same-tree")
        self.git(path, "commit", "--allow-empty", "-m", "same tree")
        self.git(path, "checkout", "dev")
        self.git(path, "merge", "--no-commit", "--no-ff", "same-tree")
        self.assertEqual(self.git(path, "status", "--porcelain"), "")
        self.assertIn("Unresolved Git", self.claim("operation", code=2)["reason"])
        self.git(path, "merge", "--abort")
        self.assertEqual(self.claim("operation")["state"], "active")

    def test_explicit_unchecked_target_ref_preserves_primary_checkout(self):
        path = self.repos["backend"]
        original = self.git(path, "rev-parse", "HEAD")
        self.git(path, "branch", "pi")
        file = self.request("pi-delivery", "backend", target="pi")
        request = json.loads(file.read_text())
        self.assertEqual(request["repositories"][0]["branch"], "refs/heads/pi")
        self.assertEqual(request["repositories"][0]["checkout_branch"], "refs/heads/dev")
        self.call("enqueue", "--request", file)
        grant = self.claim("pi-delivery")
        candidate = self.git(path, "rev-parse", "task/change")
        self.git(path, "update-ref", "refs/heads/pi", candidate, original)
        self.assertEqual(self.finish(grant, "completed")["state"], "completed")
        self.assertEqual(self.git(path, "rev-parse", "HEAD"), original)
        self.assertEqual(self.git(path, "branch", "--show-current"), "dev")
        self.assertEqual((path / "file").read_text(), "base\n")
        self.assertEqual(self.git(path, "status", "--porcelain"), "")

    def test_checked_out_target_and_refresh_retarget_are_rejected(self):
        path = self.repos["backend"]
        self.git(path, "branch", "pi")
        file = self.request("ref", "backend", target="pi")
        self.call("enqueue", "--request", file)
        linked = self.base / "pi-checked-out"
        self.git(path, "worktree", "add", str(linked), "pi")
        self.assertIn("another worktree", self.claim("ref", code=2)["reason"])
        self.git(path, "worktree", "remove", str(linked))
        changed = json.loads(file.read_text())
        changed["repositories"][0]["branch"] = "refs/heads/dev"
        file.write_text(json.dumps(changed))
        self.assertIn("target identity", self.call("refresh", "--request", file,
                                                  "--evidence", self.proof, code=2)["reason"])
        self.assertEqual(self.claim("ref")["state"], "active")

    def test_ref_only_completion_rejects_unrelated_checkout_changes(self):
        path = self.repos["backend"]
        self.git(path, "branch", "pi")
        file = self.request("preserve-dev", "backend", target="pi")
        self.call("enqueue", "--request", file)
        grant = self.claim("preserve-dev")
        self.git(path, "commit", "--allow-empty", "-m", "unrelated primary work")
        self.assertIn("primary checkout HEAD changed", self.finish(grant, code=2)["reason"])
        self.assertEqual(self.call("status", "--id", "preserve-dev")["state"], "active")

    def test_concurrent_first_enqueue_is_idempotent_and_private(self):
        request = self.request("initial", "backend")
        def enqueue(_):
            return self.call("enqueue", "--request", request)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            entries = list(pool.map(enqueue, range(4)))
        self.assertEqual({entry["seq"] for entry in entries}, {1})
        self.assertEqual(len(self.call("status")), 1)

    def test_private_state_and_launcher_dispatch(self):
        self.enqueue("private", "backend")
        self.assertEqual(self.home.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.home / "queue.sqlite3").stat().st_mode & 0o777, 0o600)
        result = subprocess.run(["bash", str(ROOT / "bin/megai"), "queue", "--home", str(self.home),
                                 "status", "--id", "private"],
                                env={**self.env, "MEGAI_HOME": str(ROOT)}, capture_output=True,
                                text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["id"], "private")
        malformed = self.base / "malformed.json"
        malformed.write_text('{"schema": 1}')
        self.call("enqueue", "--request", malformed, code=2)
        self.home.chmod(0o755)
        self.assertIn("private", self.call("status", code=2)["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

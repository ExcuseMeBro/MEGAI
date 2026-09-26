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
        self.env = dict(os.environ)
        self.repos = {}
        for name in ("backend", "frontend", "mobile"):
            path = self.project / name
            path.mkdir()
            self.git(path, "init", "-b", "dev")
            self.git(path, "config", "user.email", "fixture@example.invalid")
            self.git(path, "config", "user.name", "Queue fixture")
            (path / "file").write_text("base\n")
            (path / "codedb.snapshot").write_text("tracked foreign baseline\n")
            self.git(path, "add", "file", "codedb.snapshot")
            self.git(path, "commit", "-m", "base")
            self.git(path, "checkout", "-b", "task/change")
            (path / "file").write_text("candidate\n")
            self.git(path, "commit", "-am", "candidate")
            self.git(path, "checkout", "dev")
            self.repos[name] = path
        config = self.project / ".pi"
        config.mkdir()
        (config / "project.json").write_text(json.dumps({
            "layout": "multi", "repositories": list(self.repos), "planeProject": "product"
        }))
        self.proof = self.base / "recovery.txt"
        self.proof.write_text("Fixture owner stopped; inspected target vectors and working trees.\n")

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

    def request(self, key, *repos, after=(), target=None, remote_dev=False):
        args = ["plan", "--root", str(self.project), "--id", key,
                "--plane-project", "00000000-0000-4000-8000-000000000001",
                "--plane-item", str(uuid.uuid5(uuid.NAMESPACE_URL, key))]
        for name in repos:
            args += ["--repo", str(self.repos[name]), "task/change"]
        for dependency in after:
            args += ["--after", dependency]
        if target:
            args += ["--target-branch", target]
        if remote_dev:
            args += ["--remote-dev"]
        value = self.call(*args)
        file = self.base / (key + ".json")
        file.write_text(json.dumps(value))
        return file

    def enqueue(self, key, *repos, after=()):
        file = self.request(key, *repos, after=after)
        return self.call("enqueue", "--request", file)

    def add_origin(self, name):
        path = self.repos[name]
        remote = self.base / f"{name}.git"
        remote.mkdir()
        self.git(remote, "init", "--bare")
        self.git(path, "remote", "add", "origin", str(remote))
        self.git(path, "push", "origin", "dev")
        self.git(path, "fetch", "origin", "dev")
        return remote

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

    def test_completed_accepts_candidate_at_target_head(self):
        self.enqueue("fast-forward", "backend")
        grant = self.claim("fast-forward")
        self.git(self.repos["backend"], "merge", "--ff-only", "task/change")
        self.assertEqual(self.finish(grant, "completed")["state"], "completed")

    def test_completed_accepts_candidate_behind_advanced_target(self):
        self.enqueue("advanced", "backend")
        grant = self.claim("advanced")
        path = self.repos["backend"]
        self.git(path, "merge", "--ff-only", "task/change")
        (path / "later").write_text("later merge\n")
        self.git(path, "add", "later")
        self.git(path, "commit", "-m", "later merge")
        finished = self.finish(grant, "completed")
        self.assertEqual(finished["state"], "completed")
        self.assertFalse(finished["needs_reconcile"])
        self.enqueue("after", "backend")
        self.assertEqual(self.claim("after")["state"], "active")

    def test_completed_still_refuses_unrelated_target_head(self):
        self.enqueue("unrelated", "backend")
        grant = self.claim("unrelated")
        path = self.repos["backend"]
        (path / "later").write_text("unrelated merge\n")
        self.git(path, "add", "later")
        self.git(path, "commit", "-m", "unrelated merge")
        self.assertIn("not delivered", self.finish(grant, "completed", code=2)["reason"])
        self.assertEqual(self.call("status", "--id", "unrelated")["state"], "active")

    def test_moved_expected_head_still_refuses_enqueue_claim_and_refresh(self):
        file = self.request("moved", "backend")
        self.call("enqueue", "--request", file)
        path = self.repos["backend"]
        (path / "later").write_text("moved base\n")
        self.git(path, "add", "later")
        self.git(path, "commit", "-m", "moved base")
        stale = json.loads(file.read_text())
        stale["id"] = "moved-copy"
        copy = self.base / "moved-copy.json"
        copy.write_text(json.dumps(stale))
        self.assertIn("Commit vector", self.call("enqueue", "--request", copy, code=2)["reason"])
        self.assertIn("Commit vector", self.claim("moved", code=2)["reason"])
        self.assertIn("Commit vector", self.call("refresh", "--request", file,
                                                  "--evidence", self.proof, code=2)["reason"])
        self.assertEqual(self.call("status", "--id", "moved")["state"], "queued")

    def test_reconcile_completed_accepts_candidate_behind_advanced_target(self):
        self.enqueue("reconcile-completed", "backend")
        self.claim("reconcile-completed")
        path = self.repos["backend"]
        self.git(path, "merge", "--ff-only", "task/change")
        (path / "later").write_text("later merge\n")
        self.git(path, "add", "later")
        self.git(path, "commit", "-m", "later merge")
        result = self.call("reconcile", "--id", "reconcile-completed", "--outcome", "completed",
                           "--owner-stopped", "--evidence", self.proof)
        self.assertEqual(result["state"], "completed")
        self.assertFalse(result["needs_reconcile"])

    def test_resume_excludes_candidate_behind_advanced_target(self):
        self.enqueue("resume-advanced", "backend", "frontend")
        grant = self.claim("resume-advanced")
        path = self.repos["backend"]
        self.git(path, "merge", "--ff-only", "task/change")
        (path / "later").write_text("later merge\n")
        self.git(path, "add", "later")
        self.git(path, "commit", "-m", "later merge")
        self.call("hold", "--id", "resume-advanced", "--owner", grant["owner"], "--token", grant["token"],
                  "--reason", "Executor disconnected after backend delivery")
        resumed = self.call("reconcile", "--id", "resume-advanced", "--outcome", "resume",
                            "--owner", "new-owner", "--owner-stopped", "--evidence", self.proof)
        self.assertEqual(resumed["remaining_repositories"], [str(self.repos["frontend"].resolve())])
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

    def test_remote_dev_ignores_dirty_primary_and_requires_fetched_delivery(self):
        path = self.repos["backend"]
        self.add_origin("backend")
        foreign = path / "codedb.snapshot"
        foreign.write_bytes(b"unrelated foreign tracked modification\n")
        original_bytes = foreign.read_bytes()
        original_head = self.git(path, "rev-parse", "HEAD")
        original_branch = self.git(path, "symbolic-ref", "--quiet", "HEAD")
        merge_head = path / ".git/MERGE_HEAD"
        merge_head.write_text(original_head + "\n")
        remote_head = self.git(path, "rev-parse", "refs/remotes/origin/dev")
        index = (path / ".git/index").read_bytes()
        file = self.request("remote-dev", "backend", remote_dev=True)
        request = json.loads(file.read_text())
        vector = request["repositories"][0]
        self.assertEqual(vector["branch"], "refs/remotes/origin/dev")
        self.assertEqual(vector["expected_head"], remote_head)
        self.assertEqual(vector["candidate_head"], self.git(path, "rev-parse", "task/change"))
        self.call("enqueue", "--request", file)
        grant = self.claim("remote-dev")
        waiter = self.request("remote-waiter", "backend", remote_dev=True)
        self.call("enqueue", "--request", waiter)
        self.assertEqual(self.claim("remote-waiter", code=2)["wait_reason"], "resource:remote-dev")
        self.assertEqual(self.git(path, "rev-parse", "HEAD"), original_head)
        self.assertEqual(self.git(path, "symbolic-ref", "--quiet", "HEAD"), original_branch)
        self.assertEqual(foreign.read_bytes(), original_bytes)
        self.assertEqual((path / ".git/index").read_bytes(), index)
        self.assertEqual(merge_head.read_text(), original_head + "\n")
        self.assertEqual(self.git(path, "rev-parse", "refs/remotes/origin/dev"), remote_head)

        remote = self.base / "backend.git"
        self.git(remote, "fetch", str(path), "task/change")
        candidate = vector["candidate_head"]
        self.git(remote, "update-ref", "refs/heads/dev", candidate, remote_head)
        self.assertIn("not delivered", self.finish(grant, "completed", code=2)["reason"])
        self.assertEqual(self.git(path, "rev-parse", "refs/remotes/origin/dev"), remote_head,
                         "Queue must observe fetched tracking state, never fetch itself")
        self.assertEqual(merge_head.read_text(), original_head + "\n")
        merge_head.unlink()
        self.git(path, "fetch", "origin", "dev")
        self.assertEqual(self.finish(grant, "completed")["state"], "completed")
        self.assertEqual(self.git(path, "rev-parse", "HEAD"), original_head)
        self.assertEqual(self.git(path, "symbolic-ref", "--quiet", "HEAD"), original_branch)
        self.assertEqual(foreign.read_bytes(), original_bytes)
        self.assertEqual((path / ".git/index").read_bytes(), index)

    def test_remote_dev_stale_vectors_require_enqueue_and_claim_refresh(self):
        path = self.repos["backend"]
        self.add_origin("backend")
        stale = self.request("remote-stale", "backend", remote_dev=True)
        candidate = self.git(path, "rev-parse", "task/change")
        self.git(path, "push", "origin", "task/change:dev")
        self.git(path, "fetch", "origin", "dev")
        self.assertIn("Commit vector", self.call("enqueue", "--request", stale, code=2)["reason"])

        fresh = self.request("remote-stale", "backend", remote_dev=True)
        self.call("enqueue", "--request", fresh)
        tree = self.git(path, "rev-parse", f"{candidate}^{{tree}}")
        later = self.git(path, "-c", "user.email=fixture@example.invalid", "-c",
                         "user.name=Queue fixture", "commit-tree", tree, "-p", candidate,
                         "-m", "remote dev advances")
        self.git(path, "push", "origin", f"{later}:refs/heads/dev")
        self.git(path, "fetch", "origin", "dev")
        self.assertIn("Commit vector", self.call("enqueue", "--request", fresh, code=2)["reason"])
        self.assertIn("Commit vector", self.claim("remote-stale", code=2)["reason"])

        refreshed = self.request("remote-stale", "backend", remote_dev=True)
        self.call("refresh", "--request", refreshed, "--evidence", self.proof)
        grant = self.claim("remote-stale")
        newer = self.git(path, "-c", "user.email=fixture@example.invalid", "-c",
                         "user.name=Queue fixture", "commit-tree", tree, "-p", later,
                         "-m", "remote dev advances again")
        self.git(path, "update-ref", "refs/heads/remote-later", newer)
        remote = self.base / "backend.git"
        self.git(remote, "fetch", str(path), "refs/heads/remote-later")
        self.git(remote, "update-ref", "refs/heads/dev", newer, later)
        self.git(path, "fetch", "origin", "dev")
        self.assertIn("Commit vector", self.claim("remote-stale", owner=grant["owner"], code=2)["reason"])
        self.assertEqual(self.finish(grant, "completed")["state"], "completed")

    def test_remote_dev_rejects_forged_refs_and_target_branch(self):
        path = self.repos["backend"]
        self.add_origin("backend")
        file = self.request("remote-forged", "backend", remote_dev=True)
        request = json.loads(file.read_text())
        request["repositories"][0]["branch"] = "refs/remotes/origin/feature"
        file.write_text(json.dumps(request))
        self.assertIn("branch", self.call("enqueue", "--request", file, code=2)["reason"])

        conflict = ["plan", "--root", str(self.project), "--id", "remote-conflict",
                    "--plane-project", "00000000-0000-4000-8000-000000000001",
                    "--plane-item", str(uuid.uuid5(uuid.NAMESPACE_URL, "remote-conflict")),
                    "--repo", str(path), "task/change", "--remote-dev", "--target-branch", "dev"]
        self.assertIn("cannot be combined", self.call(*conflict, code=2)["reason"])

    def test_local_dev_still_refuses_dirty_primary(self):
        path = self.repos["backend"]
        foreign = path / "codedb.snapshot"
        foreign.write_bytes(b"unrelated foreign tracked modification\n")
        original_bytes = foreign.read_bytes()
        original_head = self.git(path, "rev-parse", "HEAD")
        file = self.request("local-dirty", "backend")
        self.assertIn("dirty", self.call("enqueue", "--request", file, code=2)["reason"])
        self.assertEqual(foreign.read_bytes(), original_bytes)
        self.assertEqual(self.git(path, "rev-parse", "HEAD"), original_head)

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

#!/usr/bin/env python3
"""Contracts for the /mdev and /prdev delivery sweep.

The sweep is what makes a fresh session own the whole delivery: adopt abandoned work,
merge exact task SHAs into `dev`, verify the push, prove each Plane task In Review and
retire what it proved. These tests run it against real throwaway repositories with a
stub Plane, so a regression shows up without a network call or a real project.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = ROOT / "pi-defaults"
sys.path.insert(0, str(DEFAULTS))

import delivery  # noqa: E402

PROJECT = {"id": "project-1", "name": "MEGAI", "identifier": "MEGAI"}
STATES = {"Todo": "state-todo", "In Progress": "state-progress",
          "In Review": "state-review", "Done": "state-done"}


def run_git(path, *args, env=None):
    environment = {"PATH": os.environ["PATH"], "HOME": str(path)}
    environment.update(env or {})
    result = subprocess.run(["git", "-C", str(path), *args], capture_output=True,
                            text=True, timeout=120, env=environment)
    if result.returncode:
        raise AssertionError(f"git {args} failed: {result.stderr or result.stdout}")
    return result.stdout


class StubPlane:
    """The narrow Plane surface, in memory: no transport, no retries, no surprises."""

    def __init__(self, offline=False):
        self.offline = offline
        self.items = {"7": {"id": "task-7", "sequence_id": 7, "state": STATES["In Progress"]},
                      "8": {"id": "task-8", "sequence_id": 8, "state": STATES["In Progress"]}}
        self.reviews = []

    def context(self, cwd):
        return {"planeProject": PROJECT["name"], "repositories": [str(self.repo)]}

    def pages(self, name, **arguments):
        if self.offline:
            raise delivery.Blocked("Plane unreachable: timed out")
        if name == "project":
            return [PROJECT]
        if name == "state":
            return [{"id": value, "name": key, "group": group}
                    for key, value, group in (
                        ("Todo", STATES["Todo"], "unstarted"),
                        ("In Progress", STATES["In Progress"], "started"),
                        ("In Review", STATES["In Review"], "started"),
                        ("Done", STATES["Done"], "completed"))]
        if name == "workitem":
            return [dict(item) for item in self.items.values()]
        raise AssertionError(f"unexpected Plane resource {name}")

    @staticmethod
    def unique(rows, name):
        matches = [row for row in rows if row["name"] == name]
        assert len(matches) == 1, matches
        return matches[0]

    @staticmethod
    def states(project):
        return dict(STATES)

    def review_boundary(self, project_id, task_id, receipt, evidence):
        if self.offline:
            raise delivery.Blocked("Plane unreachable: timed out")
        item = next(item for item in self.items.values() if item["id"] == task_id)
        item["state"] = STATES["In Review"]
        self.reviews.append({"task_id": task_id, "receipt": receipt, "evidence": evidence})
        return {"project_id": project_id, "task_id": task_id, "state": "In Review"}


class SweepCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="pi-delivery-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.origin = self.root / "origin.git"
        run_git(self.root, "init", "-q", "--bare", "-b", "dev", str(self.origin))
        self.repo = self.root / "repo"
        self.repo.mkdir()
        run_git(self.repo, "init", "-q", "-b", "dev")
        run_git(self.repo, "config", "user.name", "Test")
        run_git(self.repo, "config", "user.email", "test@example.invalid")
        run_git(self.repo, "remote", "add", "origin", str(self.origin))
        (self.repo / "README.md").write_text("base\n")
        run_git(self.repo, "add", "README.md")
        run_git(self.repo, "commit", "-q", "-m", "base")
        run_git(self.repo, "push", "-q", "-u", "origin", "dev")
        # Task 7: committed work in its own checkout.
        run_git(self.repo, "branch", "task/megai-7-alpha", "dev")
        self.alpha = self.root / "wt-alpha"
        run_git(self.repo, "worktree", "add", "-q", str(self.alpha), "task/megai-7-alpha")
        (self.alpha / "alpha.txt").write_text("alpha\n")
        run_git(self.alpha, "add", "alpha.txt")
        run_git(self.alpha, "commit", "-q", "-m", "alpha work")
        # Task 8: abandoned uncommitted work in an idle checkout.
        run_git(self.repo, "branch", "task/megai-8-beta", "dev")
        self.beta = self.root / "wt-beta"
        run_git(self.repo, "worktree", "add", "-q", str(self.beta), "task/megai-8-beta")
        (self.beta / "beta.txt").write_text("beta\n")
        # Writer detection is exercised separately; the sweep runs as if nothing is writing.
        self.patch_newest_write(None)
        self.state = self.root / "state"
        self.backups = self.root / "backups"
        self.plane = StubPlane()
        self.plane.repo = self.repo

    def patch_newest_write(self, value):
        original = delivery.newest_write
        self.real_newest_write = original
        delivery.newest_write = (lambda root: value) if value is None else (lambda root: value)
        self.addCleanup(setattr, delivery, "newest_write", original)

    def options(self, **extra):
        options = {"cwd": str(self.repo), "remote": "origin", "state": str(self.state),
                   "backups": str(self.backups), "active_minutes": 15,
                   "prefixes": delivery.TASK_PREFIXES, "project_prefixes": {"megai"},
                   "adopt": True, "push": True, "retire": True, "dry_run": False,
                   "check": None, "base": "main"}
        options.update(extra)
        return options

    def context(self):
        return {"planeProject": PROJECT["name"], "repositories": [str(self.repo)],
                "persistentBranches": [], "preserveBranches": {}}

    def sweep(self, **extra):
        return delivery.run(self.plane, self.context(), self.options(**extra))

    def refs(self):
        return run_git(self.repo, "for-each-ref", "--format=%(refname:short)",
                       "refs/heads").split()

    def test_run_merges_pushes_proves_and_retires(self):
        report = self.sweep()
        branches = {row["branch"] for row in report["merged"]}
        self.assertEqual(branches, {"task/megai-7-alpha", "task/megai-8-beta"})
        adopted = {row["branch"] for row in report["adopted"]}
        self.assertEqual(adopted, {"task/megai-8-beta"})
        backup = Path(report["adopted"][0]["backup"])
        self.assertTrue((backup / "status.txt").is_file())
        # Every merged SHA is an ancestor of the pushed dev tip, locally and remotely.
        dev = run_git(self.repo, "rev-parse", "dev").strip()
        remote = run_git(self.repo, "ls-remote", "origin", "refs/heads/dev").split()[0]
        self.assertEqual(dev, remote)
        for row in report["merged"]:
            subject = run_git(self.repo, "log", "--format=%s", f"{row['sha']}^..{row['sha']}")
            self.assertIn("alpha work" if row["task"] == 7 else "adopt uncommitted work", subject)
        self.assertEqual(sorted(review["task_id"] for review in self.plane.reviews),
                         ["task-7", "task-8"])
        # Proven rows are gone from Git and from disk.
        remaining = self.refs()
        self.assertNotIn("task/megai-7-alpha", remaining)
        self.assertNotIn("task/megai-8-beta", remaining)
        self.assertFalse(self.alpha.exists())
        self.assertFalse(self.beta.exists())
        self.assertEqual([row for row in report["resources"] if not row["removed"]], [])

    def test_second_run_is_idempotent_and_does_not_repeat_plane_evidence(self):
        self.sweep()
        reviews = len(self.plane.reviews)
        report = self.sweep()
        self.assertEqual(report["merged"], [])
        self.assertEqual(len(self.plane.reviews), reviews)
        self.assertEqual(report["pending_plane"], [])

    def test_plane_outage_journals_and_retains_then_resume_replays(self):
        self.plane.offline = True
        report = self.sweep()
        self.assertEqual(len(report["pending_plane"]), 2)
        self.assertEqual(len(report["merged"]), 2)  # Git delivery still completes
        self.assertTrue(any(not row["removed"] for row in report["resources"]))
        self.assertIn("task/megai-7-alpha", self.refs())  # retained until proven
        self.plane.offline = False
        replayed = delivery.resume(self.plane, self.context(), self.options())
        self.assertEqual(len(replayed["replayed"]), 2)
        self.assertEqual(replayed["pending"], [])
        self.assertEqual(sorted(review["task_id"] for review in self.plane.reviews),
                         ["task-7", "task-8"])
        self.assertEqual(list((self.state / "pending").glob("*.json")), [])

    def test_busy_writer_is_retained(self):
        delivery.newest_write = lambda root: __import__("time").time()
        report = self.sweep()
        self.assertEqual(report["merged"], [])
        reasons = " ".join(row["reason"] for row in report["retained"])
        self.assertIn("writer", reasons)
        self.assertIn("task/megai-7-alpha", self.refs())

    def test_session_mention_alone_is_a_warning_and_never_blocks_a_clean_checkout(self):
        sessions = self.root / "sessions"
        sessions.mkdir()
        (sessions / "session.jsonl").write_text(json.dumps({"cwd": str(self.alpha)}) + "\n")
        clean = delivery.writer_activity(self.alpha, 15, session_dir=sessions)
        self.assertEqual(clean["level"], "warning")
        self.assertIn("open Pi session", clean["reasons"][0])
        original = delivery.session_reference
        delivery.session_reference = lambda path, window, session_dir=None: "session.jsonl"
        self.addCleanup(setattr, delivery, "session_reference", original)
        clean_row = delivery.row_for(self.repo, str(self.alpha), "task/megai-7-alpha", None,
                                     {"active_minutes": 15, "project_prefixes": {"megai"}})
        self.assertEqual(clean_row["activity"]["level"], "warning")
        (self.alpha / "notes.txt").write_text("mid-edit\n")
        dirty_row = delivery.row_for(self.repo, str(self.alpha), "task/megai-7-alpha", None,
                                     {"active_minutes": 15, "project_prefixes": {"megai"}})
        self.assertEqual(dirty_row["activity"]["level"], "busy")
        self.assertIn("uncommitted work in a checkout referenced by an open session",
                      dirty_row["activity"]["reasons"][-1])

    def test_fresh_writes_in_the_dev_checkout_are_not_a_target_blocker(self):
        # The dev checkout is normally the operator's own directory: a fetch, a merge or an
        # open session there must never look like a competing writer of the shared target.
        delivery.newest_write = self.real_newest_write
        (self.repo / "README.md").write_text("base\nlocal note\n")
        self.assertEqual(delivery.writer_activity(self.repo, 15)["level"], "busy")
        self.assertEqual(delivery.target_signals(self.repo), [])
        (delivery.worktree_git_dir(self.repo) / "index.lock").write_text("")
        self.assertIn("index.lock present", delivery.target_signals(self.repo))

    def test_session_mention_does_not_retain_a_clean_row(self):
        original = delivery.session_reference
        delivery.session_reference = lambda path, window, session_dir=None: "session.jsonl"
        self.addCleanup(setattr, delivery, "session_reference", original)
        report = self.sweep()
        self.assertIn("task/megai-7-alpha", {row["branch"] for row in report["merged"]})
        reasons = " ".join(row["reason"] for row in report["retained"])
        self.assertNotIn("task/megai-7-alpha", reasons)

    def test_task_number_requires_the_project_prefix(self):
        self.assertEqual(delivery.task_number("task/megai-151-slug", {"megai"}), 151)
        self.assertIsNone(delivery.task_number("task/other-151-slug", {"megai"}))
        self.assertIsNone(delivery.task_number("dev", {"megai"}))

    def test_remove_resource_refuses_an_unmerged_branch(self):
        run_git(self.repo, "checkout", "-q", "-b", "task/megai-9-gamma", "dev")
        (self.repo / "gamma.txt").write_text("gamma\n")
        run_git(self.repo, "add", "gamma.txt")
        run_git(self.repo, "commit", "-q", "-m", "unmerged gamma work")
        run_git(self.repo, "checkout", "-q", "dev")
        row = delivery.row_for(self.repo, None, "task/megai-9-gamma", None,
                               {"active_minutes": 15, "project_prefixes": {"megai"}})
        outcome = delivery.remove_resource(self.repo, row, self.backups)
        self.assertFalse(outcome["removed"])
        self.assertIn("not merged", outcome["reason"])
        self.assertIn("task/megai-9-gamma", self.refs())

    def test_merge_conflict_keeps_dev_and_reports_the_row(self):
        run_git(self.repo, "checkout", "-q", "-b", "task/megai-10-delta", "dev")
        (self.repo / "README.md").write_text("delta\n")
        run_git(self.repo, "commit", "-q", "-am", "delta edits readme")
        run_git(self.repo, "checkout", "-q", "dev")
        (self.repo / "README.md").write_text("dev side\n")
        run_git(self.repo, "commit", "-q", "-am", "dev edits readme")
        before = run_git(self.repo, "rev-parse", "dev").strip()
        report = self.sweep(retire=False)
        retained = " ".join(row["reason"] for row in report["retained"])
        self.assertIn("merge refused", retained)
        self.assertIn("task/megai-10-delta", self.refs())
        # The failed merge is aborted, so dev keeps its own content and no conflict state.
        self.assertNotEqual(run_git(self.repo, "rev-parse", "dev").strip(), before)
        self.assertEqual((self.repo / "README.md").read_text(), "dev side\n")
        self.assertEqual(run_git(self.repo, "status", "--porcelain").strip(), "")
        self.assertFalse((self.repo / ".git/MERGE_HEAD").exists())


class ForgeCase(unittest.TestCase):
    def test_existing_request_is_reused_and_uncertain_create_is_not_repeated(self):
        delivery_bin = DEFAULTS / "delivery.py"
        self.assertTrue(delivery_bin.is_file())
        forge = delivery.detect_forge("git@github.com:owner/name.git")
        self.assertEqual(forge, "github")
        self.assertEqual(delivery.forge_binary(forge), "gh")
        calls = []

        def runner(argv, cwd, timeout=300):
            calls.append(argv)
            if "list" in argv:
                return 0, json.dumps([{"url": "https://github.com/owner/name/pull/7",
                                       "headRefName": "dev", "baseRefName": "main",
                                       "headRefOid": "a" * 40, "baseRefOid": "b" * 40,
                                       "state": "OPEN"}]), ""
            raise AssertionError(f"unexpected forge call {argv}")

        found = delivery.open_request(forge, Path("/tmp"), "main", "dev", runner)
        self.assertEqual(found["url"], "https://github.com/owner/name/pull/7")
        self.assertIn("list", calls[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)

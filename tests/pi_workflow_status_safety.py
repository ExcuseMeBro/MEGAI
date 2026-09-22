#!/usr/bin/env python3
"""Supplementary safety contract for the read-only ``pi-workflow status`` inventory.

This file is additive: the frozen ``tests/pi_workflow_status.py`` stays
byte-identical. It reuses that file's disposable Git fixture, fake Paseo and
helpers, and adds the independent-review blocking cases: categorical cleanup
exclusions, complete Paseo field validation, fail-closed Git observation
errors, race additions/removals/lock transitions, fatal project-identity
resolution, and forge/remote fetch policy.

A small ``git`` shim on PATH injects command failures without touching any real
repository: it forwards to the real ``git`` unless ``FAKE_GIT_FAIL`` matches the
argument text.
"""
from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from tests.pi_workflow_status import (
    PROJECT,
    Fixture,
    _git,
    _git_bare,
    agent,
    inspect,
    run_cli,
    workspace,
)

REAL_GIT = shutil.which("git")

FAKE_GIT = '''#!/usr/bin/env python3
import os, sys
fail = os.environ.get("FAKE_GIT_FAIL")
if fail and fail in " ".join(sys.argv[1:]):
    print("injected git failure", file=sys.stderr)
    sys.exit(2)
os.execv({real!r}, ["git", *sys.argv[1:]])
'''


def install_git_shim(bin_dir: Path):
    shim = bin_dir / "git"
    shim.write_text(FAKE_GIT.format(real=str(REAL_GIT)))
    shim.chmod(0o755)


class SafetyContract(unittest.TestCase):
    def setUp(self):
        if REAL_GIT is None:  # pragma: no cover - environment guard
            self.skipTest("git is required")
        self.fx = Fixture()
        self.addCleanup(self.fx.cleanup)
        install_git_shim(self.fx.bin)

    def status(self, git_fail=None, fixture=None, **env_kw):
        fx = fixture or self.fx
        env = fx.env(**env_kw)
        if git_fail:
            env["FAKE_GIT_FAIL"] = git_fail
        return run_cli(["status", "--cwd", str(fx.primary)], env=env)

    def load(self, result):
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def rows(self, data, fixture=None):
        fx = fixture or self.fx
        repo = next(r for r in data["repositories"] if r["path"] == str(fx.primary))
        return repo, {w["workspaceId"]: w for w in data["workspaces"]}

    def add_existing_worktree(self, name, branch):
        wt = self.fx.tmp / name
        _git(self.fx.primary, "worktree", "add", str(wt), branch)
        return wt

    def released_agent(self, ws_id, path):
        return [workspace(ws_id, path)], [agent("agent-safe", path)], inspect(
            "agent-safe", path, archived=True
        )

    # --- 1. categorical cleanup exclusions ---------------------------------

    def test_primary_checkout_mislabeled_as_worktree_is_never_eligible(self):
        ws, agents, inspects = self.released_agent("wks_primary", self.fx.root)
        ws[0]["isolation"] = "worktree"
        repo, rows = self.rows(self.load(self.status(workspaces=ws, agents=agents, inspects=inspects)))
        self.assertFalse(rows["wks_primary"]["archiveEligible"])
        self.assertIn("primary-path", rows["wks_primary"]["blocked"])

    def test_persistent_branches_are_never_eligible(self):
        _git(self.fx.primary, "checkout", "--detach")
        for branch in ("dev", "main"):
            wt = self.add_existing_worktree(f"wt-{branch}", branch)
            ws_id = f"wks_{branch}"
            ws, agents, inspects = self.released_agent(ws_id, wt)
            data = self.load(self.status(workspaces=ws, agents=agents, inspects=inspects))
            _, rows = self.rows(data)
            self.assertFalse(rows[ws_id]["archiveEligible"], branch)
            self.assertIn("protected-branch", rows[ws_id]["blocked"])

    def test_preserve_branch_is_never_eligible(self):
        fx = Fixture(preserve={".": ["release"]})
        self.addCleanup(fx.cleanup)
        _git(fx.primary, "branch", "release")
        _git(fx.primary, "push", "origin", "release")
        wt = fx.tmp / "wt-release"
        _git(fx.primary, "worktree", "add", str(wt), "release")
        ws = [workspace("wks_release", wt)]
        agents = [agent("agent-release", wt)]
        inspects = inspect("agent-release", wt, archived=True)
        data = self.load(self.status(fixture=fx, workspaces=ws, agents=agents, inspects=inspects))
        _, rows = self.rows(data, fixture=fx)
        self.assertFalse(rows["wks_release"]["archiveEligible"])
        self.assertIn("protected-branch", rows["wks_release"]["blocked"])

    def test_detached_and_non_task_branches_are_never_eligible(self):
        detached = self.fx.tmp / "wt-detached"
        _git(self.fx.primary, "worktree", "add", "--detach", str(detached), "dev")
        feature = self.fx.add_worktree("wt-feature", "feature/x")
        data = self.load(
            self.status(
                workspaces=[workspace("wks_det", detached), workspace("wks_feat", feature)],
                agents=[agent("agent-det", detached), agent("agent-feat", feature)],
                inspects={
                    **inspect("agent-det", detached, archived=True),
                    **inspect("agent-feat", feature, archived=True),
                },
            )
        )
        _, rows = self.rows(data)
        self.assertFalse(rows["wks_det"]["archiveEligible"])
        self.assertIn("detached-head", rows["wks_det"]["blocked"])
        self.assertFalse(rows["wks_feat"]["archiveEligible"])
        self.assertIn("non-task-branch", rows["wks_feat"]["blocked"])

    # --- 2. complete Paseo field validation --------------------------------

    def test_zero_project_match_is_fatal(self):
        result = self.status(projects=[])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BLOCKED", result.stderr)
        self.assertEqual(result.stdout.strip(), "")
        self.assertNotIn("Traceback", result.stderr)

    def test_ambiguous_project_match_is_blocked_not_eligible(self):
        wt = self.fx.add_worktree("wt-ambig", "task/ambig")
        projects = [
            {"projectId": "prj_a", "name": PROJECT, "kind": "git", "path": str(self.fx.root)},
            {"projectId": "prj_b", "name": PROJECT, "kind": "git", "path": str(self.fx.root)},
        ]
        data = self.load(
            self.status(
                workspaces=[workspace("wks_ambig", wt)],
                agents=[agent("agent-ambig", wt)],
                inspects=inspect("agent-ambig", wt, archived=True),
                projects=projects,
            )
        )
        _, rows = self.rows(data)
        self.assertEqual(rows["wks_ambig"]["ownership"], "unknown")
        self.assertFalse(rows["wks_ambig"]["archiveEligible"])

    def test_malformed_agent_list_is_controlled_blocked(self):
        bad = {"id": "a", "cwd": str(self.fx.root), "status": "idle"}  # missing fields
        result = self.status(agents=[bad])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BLOCKED", result.stderr)
        self.assertEqual(result.stdout.strip(), "")
        self.assertNotIn("Traceback", result.stderr)

    def test_malformed_inspect_is_blocked_not_traceback(self):
        wt = self.fx.add_worktree("wt-bad", "task/bad")
        bad = inspect("agent-bad", wt, archived=True)["agent-bad"]
        bad["Id"] = 123
        data = self.load(
            self.status(
                workspaces=[workspace("wks_bad", wt)],
                agents=[agent("agent-bad", wt)],
                inspects={"agent-bad": bad},
            )
        )
        _, rows = self.rows(data)
        self.assertFalse(rows["wks_bad"]["archiveEligible"])
        self.assertTrue(
            any("Id" in reason for reason in rows["wks_bad"]["blocked"]),
            rows["wks_bad"]["blocked"],
        )

    def test_missing_pending_permissions_is_unknown(self):
        wt = self.fx.add_worktree("wt-perm", "task/perm")
        payload = inspect("agent-perm", wt, archived=True)["agent-perm"]
        payload.pop("PendingPermissions")
        data = self.load(
            self.status(
                workspaces=[workspace("wks_perm", wt)],
                agents=[agent("agent-perm", wt)],
                inspects={"agent-perm": payload},
            )
        )
        _, rows = self.rows(data)
        self.assertFalse(rows["wks_perm"]["released"])
        self.assertFalse(rows["wks_perm"]["archiveEligible"])
        self.assertIn("pending-permissions-unknown", rows["wks_perm"]["blocked"])

    def test_one_bad_inspect_invalidates_workspace(self):
        wt = self.fx.add_worktree("wt-mix", "task/mix")
        data = self.load(
            self.status(
                workspaces=[workspace("wks_mix", wt)],
                agents=[agent("agent-good", wt), agent("agent-run", wt, status="running")],
                inspects={
                    **inspect("agent-good", wt, archived=True),
                    **inspect("agent-run", wt, archived=False, status="running"),
                },
            )
        )
        _, rows = self.rows(data)
        self.assertFalse(rows["wks_mix"]["released"])
        self.assertFalse(rows["wks_mix"]["archiveEligible"])

    def test_one_failed_inspect_invalidates_workspace(self):
        wt = self.fx.add_worktree("wt-fail-inspect", "task/fi")
        data = self.load(
            self.status(
                workspaces=[workspace("wks_fi", wt)],
                agents=[agent("agent-good", wt), agent("agent-missing", wt)],
                # no inspect entry for agent-missing -> fake paseo exits non-zero
                inspects=inspect("agent-good", wt, archived=True),
            )
        )
        _, rows = self.rows(data)
        self.assertFalse(rows["wks_fi"]["released"])
        self.assertFalse(rows["wks_fi"]["archiveEligible"])
        self.assertIn("inspect-failed", rows["wks_fi"]["blocked"])

    def test_missing_runner_identity_is_not_eligible(self):
        wt = self.fx.add_worktree("wt-norunner", "task/nr")
        env = self.fx.env(
            workspaces=[workspace("wks_nr", wt)],
            agents=[agent("agent-nr", wt)],
            inspects=inspect("agent-nr", wt, archived=True),
        )
        env.pop("PASEO_AGENT_ID")
        result = run_cli(["status", "--cwd", str(self.fx.primary)], env=env)
        data = self.load(result)
        _, rows = self.rows(data)
        self.assertFalse(rows["wks_nr"]["archiveEligible"])
        self.assertIn("runner-unknown", rows["wks_nr"]["blocked"])

    # --- 3. fail-closed Git observation ------------------------------------

    def _baseline_eligible(self):
        wt = self.fx.add_worktree("wt-safe", "task/safe")
        data = self.load(
            self.status(
                workspaces=[workspace("wks_safe", wt)],
                agents=[agent("agent-safe", wt)],
                inspects=inspect("agent-safe", wt, archived=True),
            )
        )
        _, rows = self.rows(data)
        return wt, rows["wks_safe"]

    def test_baseline_workspace_is_eligible_under_clean_observations(self):
        _wt, row = self._baseline_eligible()
        self.assertTrue(row["archiveEligible"], row["blocked"])
        self.assertEqual(row["dirty"], False)
        self.assertEqual(row["ignored"], [])

    def test_injected_git_failures_never_yield_eligibility(self):
        cases = {
            "--porcelain=v1": "git-error:status",
            "--ignored": "git-error:ignored",
            "--git-dir": "git-error:operation",
            "worktree list": "git-error:worktree-list",
            "--quiet": "git-error:local-ref:dev",
            "--is-ancestor": "git-error:ancestor:dev",
            "for-each-ref": "snapshot-error:for-each-ref failed",
            "--verify HEAD": "git-error:head",
            "symbolic-ref": "git-error:symbolic-ref",
        }
        wt = self.fx.add_worktree("wt-safe", "task/safe")
        for pattern, expected in cases.items():
            with self.subTest(pattern=pattern):
                data = self.load(
                    self.status(
                        git_fail=pattern,
                        workspaces=[workspace("wks_safe", wt)],
                        agents=[agent("agent-safe", wt)],
                        inspects=inspect("agent-safe", wt, archived=True),
                    )
                )
                repo, rows = self.rows(data)
                self.assertFalse(rows["wks_safe"]["archiveEligible"], pattern)
                reasons = repo["blocked"] + rows["wks_safe"]["blocked"]
                self.assertIn(expected, reasons, f"{pattern}: {reasons}")

    def test_git_status_failure_is_unknown_not_clean(self):
        wt = self.fx.add_worktree("wt-safe", "task/safe")
        data = self.load(
            self.status(
                git_fail="--porcelain=v1",
                workspaces=[workspace("wks_safe", wt)],
                agents=[agent("agent-safe", wt)],
                inspects=inspect("agent-safe", wt, archived=True),
            )
        )
        repo, rows = self.rows(data)
        self.assertIsNone(repo["dirty"])
        self.assertFalse(rows["wks_safe"]["archiveEligible"])

    # --- 4. race additions/removals and lock transitions -------------------

    def _race_row(self, hook, wt):
        data = self.load(
            self.status(
                hook=hook,
                workspaces=[workspace("wks_race", wt)],
                agents=[agent("agent-race", wt)],
                inspects=inspect("agent-race", wt, archived=True),
            )
        )
        repo, rows = self.rows(data)
        return repo, rows["wks_race"]

    def test_branch_addition_and_removal_are_detected(self):
        wt = self.fx.add_worktree("wt-race", "task/race")
        repo, row = self._race_row(f"git -C {self.fx.primary} branch raced-addition", wt)
        self.assertTrue(repo["stale"])
        self.assertIn("ref-moved", repo["blocked"])
        self.assertFalse(row["archiveEligible"])
        self.assertIn("stale-observation", row["blocked"])

        _git(self.fx.primary, "branch", "doomed")
        repo, row = self._race_row(f"git -C {self.fx.primary} branch -D doomed", wt)
        self.assertTrue(repo["stale"])
        self.assertFalse(row["archiveEligible"])

    def test_worktree_lock_and_unlock_transitions_are_detected(self):
        wt = self.fx.add_worktree("wt-race-lock", "task/race-lock")
        repo, row = self._race_row(f"git -C {self.fx.primary} worktree lock {wt}", wt)
        self.assertTrue(repo["stale"])
        self.assertFalse(row["archiveEligible"])

        repo, row = self._race_row(f"git -C {self.fx.primary} worktree unlock {wt}", wt)
        self.assertTrue(repo["stale"])
        self.assertFalse(row["archiveEligible"])

    # --- 6. forge policy and failing remote --------------------------------

    def test_forge_policy_blocks_before_any_fetch(self):
        config = json.loads((self.fx.root / ".pi/project.json").read_text())
        config["forge"] = "example.invalid"
        (self.fx.root / ".pi/project.json").write_text(json.dumps(config))
        _git(self.fx.root, "add", ".pi/project.json")
        _git(self.fx.root, "commit", "-m", "forge")
        fetch_head = self.fx.primary / ".git" / "FETCH_HEAD"
        if fetch_head.exists():
            fetch_head.unlink()
        wt = self.fx.add_worktree("wt-forge", "task/forge")
        before = _git(self.fx.primary, "show-ref")
        data = self.load(
            self.status(
                workspaces=[workspace("wks_forge", wt)],
                agents=[agent("agent-forge", wt)],
                inspects=inspect("agent-forge", wt, archived=True),
            )
        )
        repo, rows = self.rows(data)
        self.assertIn("remote-forge-policy", repo["blocked"])
        self.assertIsNone(repo["remoteDev"])
        self.assertFalse(fetch_head.exists(), "forge policy must block before fetch")
        self.assertFalse(rows["wks_forge"]["archiveEligible"])
        self.assertIn("repo-blocked", rows["wks_forge"]["blocked"])
        self.assertEqual(_git(self.fx.primary, "show-ref"), before)

    def test_failing_persistent_branch_blocks_workspace_cleanup(self):
        origin = self.fx.origins["."]
        _git_bare(origin, "update-ref", "-d", "refs/heads/main")
        wt = self.fx.add_worktree("wt-fail-branch", "task/fail-branch")
        before = _git(self.fx.primary, "show-ref")
        data = self.load(
            self.status(
                workspaces=[workspace("wks_fail", wt)],
                agents=[agent("agent-fail", wt)],
                inspects=inspect("agent-fail", wt, archived=True),
            )
        )
        repo, rows = self.rows(data)
        self.assertIn("fetch-failed:main", repo["blocked"])
        self.assertIsNotNone(repo["remoteDev"])
        self.assertFalse(rows["wks_fail"]["archiveEligible"])
        self.assertIn("repo-blocked", rows["wks_fail"]["blocked"])
        self.assertEqual(_git(self.fx.primary, "show-ref"), before)


if __name__ == "__main__":
    unittest.main()

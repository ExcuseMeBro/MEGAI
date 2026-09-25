#!/usr/bin/env python3
"""Regression contract for the read-only ``pi-workflow status`` inventory.

Phase-1 red proof and the freezeable contract for MEGAI-88. It runs the real CLI
(``pi-defaults/workflow.py``) as a subprocess against disposable Git fixtures and
a fake ``paseo`` executable that mocks the documented Paseo read schemas
(``project ls``, ``workspace ls``, ``agent ls --all``, ``agent inspect``), so it
needs no network, no real Paseo daemon and no user profile.

Before the product edit, every ``status`` test fails because the current CLI
rejects the subcommand with argparse ``invalid choice: 'status'`` (exit 2); the
single ``context`` baseline test passes and guards the existing commands.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "pi-defaults/workflow.py"
PROJECT = "MEGAI"
PROJECT_ID = "prj_megai"
RUNNER = "runner-fixed-0001"

FAKE_PASEO = r'''#!/usr/bin/env python3
"""Stand-in for the documented Paseo read commands."""
import json
import os
import subprocess
import sys

argv = sys.argv[1:]
hook = os.environ.get("FAKE_PASEO_HOOK")
if hook:
    subprocess.run(hook, shell=True, capture_output=True)
if os.environ.get("FAKE_PASEO_MODE") == "fail":
    print("paseo: daemon unavailable", file=sys.stderr)
    sys.exit(3)
state_path = os.environ.get("FAKE_PASEO_STATE")
state = json.load(open(state_path)) if state_path else None
if argv[:2] == ["project", "ls"]:
    raw = os.environ.get("FAKE_PROJECTS")
    out = json.loads(raw) if raw else [{
        "projectId": os.environ["FAKE_PROJECT_ID"],
        "name": os.environ["FAKE_PROJECT"],
        "kind": "git",
        "path": os.environ["FAKE_ROOT"],
    }]
elif argv[:2] == ["workspace", "ls"]:
    out = state["workspaces"] if state else json.loads(os.environ.get("FAKE_WORKSPACES", "[]"))
elif argv[:2] == ["workspace", "archive"] and state:
    if os.environ.get("FAKE_ARCHIVE_LOG"):
        with open(os.environ["FAKE_ARCHIVE_LOG"], "a") as f:
            f.write("workspace\n")
    positional = [a for a in argv[2:] if not a.startswith("-")]
    key = positional[0] if positional else ""
    matches = [w for w in state["workspaces"] if w["workspaceId"] == key]
    if len(matches) != 1:
        sys.exit(4)
    subprocess.run(["git", "-C", os.environ["FAKE_ROOT"], "worktree", "remove", matches[0]["cwd"]], check=True)
    state["workspaces"] = [w for w in state["workspaces"] if w["workspaceId"] != key]
    with open(state_path, "w") as f:
        json.dump(state, f)
    out = {"workspaceId": key}
elif argv[:2] == ["terminal", "ls"]:
    counter = os.environ.get("FAKE_TERMINAL_COUNTER")
    if counter:
        n = int(open(counter).read()) + 1
        with open(counter, "w") as f:
            f.write(str(n))
        out = [{"id": "new-terminal"}] if n >= 2 else []
    else:
        out = json.loads(os.environ.get("FAKE_TERMINALS", "[]"))
elif argv[:2] == ["agent", "ls"]:
    out = state.get("agents", []) if state and "agents" in state else json.loads(os.environ.get("FAKE_AGENTS", "[]"))
elif argv[:2] == ["agent", "archive"] and state:
    if os.environ.get("FAKE_AGENT_ARCHIVE_FAIL"):
        sys.exit(4)
    positional = [a for a in argv[2:] if not a.startswith("-")]
    key = positional[0] if positional else ""
    if key not in state.get("inspects", {}):
        sys.exit(4)
    if os.environ.get("FAKE_ARCHIVE_LOG"):
        with open(os.environ["FAKE_ARCHIVE_LOG"], "a") as f:
            f.write("agent\n")
    state["inspects"][key]["Archived"] = True
    if os.environ.get("FAKE_NEW_OWNER_AFTER_ARCHIVE"):
        state["agents"].append({"id": "foreign", "shortId": "foreign", "name": "foreign",
                                "provider": "pi", "thinking": "high", "status": "running",
                                "cwd": state["agents"][0]["cwd"], "created": "now"})
    with open(state_path, "w") as f:
        json.dump(state, f)
    out = {"Id": key, "Archived": True}
elif argv[:2] == ["agent", "inspect"]:
    inspects = state.get("inspects", {}) if state and "inspects" in state else json.loads(os.environ.get("FAKE_INSPECTS", "{}"))
    positional = [a for a in argv[2:] if not a.startswith("-")]
    key = positional[0] if positional else ""
    if key not in inspects:
        print("paseo: unknown agent", file=sys.stderr)
        sys.exit(4)
    out = inspects[key]
else:
    print("paseo: unsupported command", file=sys.stderr)
    sys.exit(4)
print(json.dumps(out))
'''


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _git_bare(gitdir: Path, *args: str) -> str:
    return subprocess.run(
        ["git", f"--git-dir={gitdir}", *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def run_cli(args, env=None, timeout=120):
    return subprocess.run(
        [sys.executable, str(WORKFLOW), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


class Fixture:
    """Disposable mono/multi project with bare remotes and a fake Paseo."""

    def __init__(self, layout="mono", repositories=None, preserve=None, no_origin=()):
        self.tmp = Path(tempfile.mkdtemp(prefix="m88-status-")).resolve()
        self.root = self.tmp / "proj"
        self.root.mkdir()
        (self.root / ".pi").mkdir()
        self.origins = {}
        self.no_origin = set(no_origin)
        if layout == "mono":
            self.repositories = ["."]
        else:
            self.repositories = list(repositories or [])
        # Write the tracked project config BEFORE the primary commit so the mono
        # fixture repo is clean and `.pi/project.json` (which lives inside it)
        # is committed, not an untracked leftover.
        self._write_config(layout, preserve)
        if layout == "mono":
            self.primary = self.root
            self.origins["."] = self._make_repo(self.root)
        else:
            for name in self.repositories:
                self.origins[name] = self._make_repo(self.root / name)
            self.primary = self.root / self.repositories[0]
        self.head = _git(self.primary, "rev-parse", "HEAD")
        self.dev = _git(self.primary, "rev-parse", "dev")
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        paseo = self.bin / "paseo"
        paseo.write_text(FAKE_PASEO)
        paseo.chmod(0o755)

    def _write_config(self, layout, preserve):
        config = {
            "layout": layout,
            "planeProject": PROJECT,
            "repositories": self.repositories,
        }
        if preserve:
            config["preserveBranches"] = preserve
        (self.root / ".pi/project.json").write_text(json.dumps(config))

    def _make_repo(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        _git(path, "-c", "init.defaultBranch=main", "init")
        _git(path, "config", "user.email", "t@example.com")
        _git(path, "config", "user.name", "Test")
        (path / "README.md").write_text("fixture\n")
        (path / ".gitignore").write_text("build/\n")
        _git(path, "add", ".")
        _git(path, "commit", "-m", "init")
        _git(path, "branch", "dev")
        if path.name in self.no_origin:
            return None
        origin = self.tmp / (path.name + "-origin.git")
        _git(self.tmp, "init", "--bare", str(origin))
        _git(path, "remote", "add", "origin", str(origin))
        _git(path, "push", "origin", "main", "dev")
        return origin

    def repo(self, name="."):
        return self.root if name == "." else self.root / name

    def add_worktree(self, name, branch, base="dev", repo="."):
        primary = self.repo(repo)
        wt = self.tmp / name
        _git(primary, "worktree", "add", "-b", branch, str(wt), base)
        return wt

    def commit_in(self, path: Path, filename: str) -> str:
        (path / filename).write_text("x\n")
        _git(path, "add", ".")
        _git(path, "commit", "-m", filename)
        return _git(path, "rev-parse", "HEAD")

    def advance_remote_dev(self, repo="."):
        """Advance bare ``dev`` without touching the local remote-tracking ref."""
        primary = self.repo(repo)
        origin = self.origins[repo]
        _git(primary, "checkout", "-q", "-b", "_adv")
        (primary / "advance.txt").write_text("a\n")
        _git(primary, "add", ".")
        _git(primary, "commit", "-qm", "advance")
        sha = _git(primary, "rev-parse", "HEAD")
        _git(primary, "push", "-q", "origin", f"{sha}:refs/heads/_tmpadv")
        _git_bare(origin, "update-ref", "refs/heads/dev", sha)
        _git(primary, "push", "-q", "origin", ":refs/heads/_tmpadv")
        _git(primary, "checkout", "-q", "main")
        _git(primary, "branch", "-D", "_adv")
        return sha

    def env(self, workspaces=None, agents=None, inspects=None, mode=None,
            projects=None, hook=None, root=None, primary=None, runner=RUNNER):
        env = dict(os.environ)
        for key in ("FAKE_PASEO_HOOK", "FAKE_PROJECTS", "FAKE_PASEO_MODE"):
            env.pop(key, None)
        env["PATH"] = f"{self.bin}{os.pathsep}{env.get('PATH', '')}"
        env["FAKE_PROJECT"] = PROJECT
        env["FAKE_PROJECT_ID"] = PROJECT_ID
        env["FAKE_ROOT"] = str(root or self.root)
        env["FAKE_WORKSPACES"] = json.dumps(workspaces or [])
        env["FAKE_AGENTS"] = json.dumps(agents or [])
        env["FAKE_INSPECTS"] = json.dumps(inspects or {})
        env["PASEO_AGENT_ID"] = runner
        if mode:
            env["FAKE_PASEO_MODE"] = mode
        if projects is not None:
            env["FAKE_PROJECTS"] = json.dumps(projects)
        if hook:
            env["FAKE_PASEO_HOOK"] = hook
        return env

    def cleanup(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class CleanupContract(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        self.addCleanup(self.fx.cleanup)
        self.wt = self.fx.add_worktree("cleanup-task", "task/megai-162")
        self.tip = self.fx.commit_in(self.wt, "task.txt")
        _git(self.fx.primary, "switch", "dev")
        _git(self.fx.primary, "merge", "--ff-only", self.tip)
        self.state = self.fx.tmp / "paseo-state.json"
        self.state.write_text(json.dumps({"workspaces": [workspace("wks_own", self.wt)]}))

    def run_cleanup(self, *, tip=None, env=None):
        default = self.fx.env(agents=[agent("child", self.wt)],
                              inspects=inspect("child", self.wt, archived=True))
        default["FAKE_PASEO_STATE"] = str(self.state)
        if env:
            default.update(env)
        return run_cli(["cleanup", "--cwd", str(self.fx.primary), "--workspace", "wks_own",
                        "--branch", "task/megai-162", "--tip", tip or self.tip], env=default)

    def test_local_dev_delivery_archives_only_owned_workspace_then_branch(self):
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.wt.exists())
        self.assertNotIn("task/megai-162", _git(self.fx.primary, "branch", "--list", "task/megai-162"))
        self.assertEqual(json.loads(self.state.read_text())["workspaces"], [])

    def test_generated_pyc_is_privately_preserved_before_cleanup(self):
        info_exclude = self.fx.primary / ".git/info/exclude"
        info_exclude.write_text(info_exclude.read_text() + "\n__pycache__/\n")
        generated = self.wt / "pkg/__pycache__/example.cpython-314.pyc"
        generated.parent.mkdir(parents=True)
        generated.write_bytes(b"generated bytecode")
        self.assertIn("__pycache__", _git(self.wt, "ls-files", "--others", "--ignored", "--exclude-standard"))
        backups = self.fx.tmp / "private-backups"
        backups.mkdir(mode=0o700)
        result = self.run_cleanup(env={"MEGAI_CLEANUP_BACKUPS": str(backups)})
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        saved = Path(report["backup"]) / "pkg/__pycache__/example.cpython-314.pyc"
        self.assertEqual(saved.read_bytes(), b"generated bytecode")
        self.assertEqual(Path(report["backup"]).stat().st_mode & 0o777, 0o700)
        self.assertEqual((Path(report["backup"]) / "manifest.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads((Path(report["backup"]) / "manifest.json").read_text())["files"][0]["path"],
                         "pkg/__pycache__/example.cpython-314.pyc")
        self.assertFalse(self.wt.exists())

    def test_backup_inside_task_checkout_is_refused(self):
        info_exclude = self.fx.primary / ".git/info/exclude"
        info_exclude.write_text(info_exclude.read_text() + "\n__pycache__/\n")
        generated = self.wt / "__pycache__/task.pyc"
        generated.parent.mkdir()
        generated.write_bytes(b"keep")
        result = self.run_cleanup(env={"MEGAI_CLEANUP_BACKUPS": str(self.wt / "backups")})
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(generated.read_bytes(), b"keep")
        self.assertTrue(self.wt.exists())

    def test_stale_tip_or_ignored_data_keeps_both_resources(self):
        stale = self.run_cleanup(tip=self.fx.dev)
        self.assertNotEqual(stale.returncode, 0)
        self.assertTrue(self.wt.exists())
        (self.wt / "build").mkdir()
        (self.wt / "build" / "keep.txt").write_text("private")
        ignored = self.run_cleanup()
        self.assertNotEqual(ignored.returncode, 0)
        self.assertTrue((self.wt / "build" / "keep.txt").exists())
        self.assertEqual(len(json.loads(self.state.read_text())["workspaces"]), 1)

    def test_idle_direct_child_archives_before_workspace_and_branch(self):
        child = inspect("child", self.wt, archived=False)["child"]
        child["ParentAgentId"] = RUNNER
        self.state.write_text(json.dumps({"workspaces": [workspace("wks_own", self.wt)],
                                          "agents": [agent("child", self.wt)],
                                          "inspects": {"child": child}}))
        order = self.fx.tmp / "archive-order"
        result = self.run_cleanup(env={"FAKE_ARCHIVE_LOG": str(order)})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(order.read_text().splitlines(), ["agent", "workspace"])
        self.assertFalse(self.wt.exists())
        self.assertEqual(_git(self.fx.primary, "branch", "--list", "task/megai-162"), "")

    def test_child_archive_failure_preserves_workspace_and_ref(self):
        child = inspect("child", self.wt, archived=False)["child"]
        child["ParentAgentId"] = RUNNER
        self.state.write_text(json.dumps({"workspaces": [workspace("wks_own", self.wt)],
                                          "agents": [agent("child", self.wt)],
                                          "inspects": {"child": child}}))
        result = self.run_cleanup(env={"FAKE_AGENT_ARCHIVE_FAIL": "1"})
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.wt.exists())
        self.assertNotEqual(_git(self.fx.primary, "branch", "--list", "task/megai-162"), "")

    def test_new_owner_after_child_archive_keeps_workspace(self):
        child = inspect("child", self.wt, archived=False)["child"]
        child["ParentAgentId"] = RUNNER
        self.state.write_text(json.dumps({"workspaces": [workspace("wks_own", self.wt)],
                                          "agents": [agent("child", self.wt)],
                                          "inspects": {"child": child}}))
        result = self.run_cleanup(env={"FAKE_NEW_OWNER_AFTER_ARCHIVE": "1"})
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.wt.exists())
        self.assertNotEqual(_git(self.fx.primary, "branch", "--list", "task/megai-162"), "")

    def test_unreleased_agent_keeps_workspace(self):
        result = self.run_cleanup(env={"FAKE_INSPECTS": json.dumps(inspect("child", self.wt, archived=False))})
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.wt.exists())

    def test_unmerged_task_keeps_workspace(self):
        _git(self.fx.primary, "reset", "--hard", self.fx.dev)
        result = self.run_cleanup()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.wt.exists())

    def test_terminal_or_running_agent_keeps_workspace(self):
        terminal = self.run_cleanup(env={"FAKE_TERMINALS": json.dumps([{"id": "busy"}])})
        self.assertNotEqual(terminal.returncode, 0)
        running = self.run_cleanup(env={"FAKE_AGENTS": json.dumps([agent("child", self.wt, "running")])})
        self.assertNotEqual(running.returncode, 0)
        self.assertTrue(self.wt.exists())

    def test_foreign_workspace_or_current_cwd_keeps_resources(self):
        foreign = self.run_cleanup(env={"FAKE_PROJECTS": json.dumps([{
            "projectId": "other", "name": "other", "kind": "git", "path": str(self.fx.root)
        }])})
        self.assertNotEqual(foreign.returncode, 0)
        default = self.fx.env(agents=[agent("child", self.wt)],
                              inspects=inspect("child", self.wt, archived=True))
        default["FAKE_PASEO_STATE"] = str(self.state)
        current = run_cli(["cleanup", "--cwd", str(self.wt), "--workspace", "wks_own",
                           "--branch", "task/megai-162", "--tip", self.tip], env=default)
        self.assertNotEqual(current.returncode, 0)
        self.assertTrue(self.wt.exists())

    def test_descendant_agent_or_caller_keeps_workspace(self):
        nested = self.wt / "nested"
        nested.mkdir()
        agents = [agent("child", self.wt), agent("other", nested, "running")]
        inspects = inspect("child", self.wt, archived=True)
        inspects.update(inspect("other", nested, archived=False, status="running"))
        result = self.run_cleanup(env={"FAKE_AGENTS": json.dumps(agents),
                                       "FAKE_INSPECTS": json.dumps(inspects)})
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.wt.exists())
        caller = self.fx.env(agents=[agent("caller", nested)],
                             inspects=inspect("caller", nested, archived=False), runner="caller")
        caller["FAKE_PASEO_STATE"] = str(self.state)
        result = run_cli(["cleanup", "--cwd", str(nested), "--workspace", "wks_own",
                          "--branch", "task/megai-162", "--tip", self.tip], env=caller)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.wt.exists())

    def test_missing_agent_release_evidence_keeps_workspace(self):
        result = self.run_cleanup(env={"FAKE_AGENTS": "[]"})
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.wt.exists())

    def test_terminal_appearing_during_preflight_keeps_workspace(self):
        counter = self.fx.tmp / "terminal-reads"
        counter.write_text("0")
        result = self.run_cleanup(env={"FAKE_TERMINAL_COUNTER": str(counter)})
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.wt.exists())

    def test_failed_branch_readback_never_reports_deletion(self):
        spec = importlib.util.spec_from_file_location("cleanup_workflow", WORKFLOW)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        real = module._local_ref
        def fail_after_deletion(path, name):
            result = real(path, name)
            if name == "task/megai-162" and result == (None, None):
                return None, "simulated read failure"
            return result
        env = self.fx.env(agents=[agent("child", self.wt)],
                          inspects=inspect("child", self.wt, archived=True))
        env["FAKE_PASEO_STATE"] = str(self.state)
        with mock.patch.dict(os.environ, env), mock.patch.object(module, "_local_ref", side_effect=fail_after_deletion):
            with self.assertRaises(ValueError):
                module.cleanup(str(self.fx.primary), "wks_own", "task/megai-162", self.tip)

    def test_no_dev_checkout_keeps_workspace_before_archival(self):
        _git(self.fx.primary, "switch", "main")
        result = self.run_cleanup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dev checkout", result.stderr)
        self.assertTrue(self.wt.exists())
        self.assertEqual(len(json.loads(self.state.read_text())["workspaces"]), 1)

    def test_archived_workspace_is_not_assumed_safe_for_branch_retry(self):
        self.assertEqual(self.run_cleanup().returncode, 0)
        result = self.run_cleanup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing", result.stderr)


def workspace(ws_id, cwd, project=PROJECT, isolation="worktree", name=None):
    return {
        "workspaceId": ws_id,
        "project": project,
        "name": name or ws_id,
        "isolation": isolation,
        "cwd": str(cwd),
    }


def agent(agent_id, cwd, status="idle"):
    return {
        "id": agent_id,
        "shortId": agent_id,
        "name": agent_id,
        "provider": "pi/deepseek/deepseek-flash",
        "thinking": "low",
        "status": status,
        "cwd": str(cwd),
        "created": "now",
    }


def inspect(agent_id, cwd, archived=False, status="idle", permissions=None):
    return {
        agent_id: {
            "Id": agent_id,
            "Name": agent_id,
            "Provider": "pi",
            "Model": "deepseek/deepseek-flash",
            "Thinking": "low",
            "Status": status,
            "Archived": archived,
            "ArchivedAt": "now" if archived else None,
            "Mode": "default",
            "Cwd": str(cwd),
            "CreatedAt": "now",
            "UpdatedAt": "now",
            "PendingPermissions": list(permissions or []),
            "Worktree": None,
            "ParentAgentId": None,
        }
    }


class StatusContract(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        self.addCleanup(self.fx.cleanup)

    def status(self, extra=None, fixture=None, **env_kw):
        fx = fixture or self.fx
        args = ["status", "--cwd", str(fx.primary)] + list(extra or [])
        return run_cli(args, env=fx.env(**env_kw))

    def load(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def repo_row(self, data, fixture=None):
        fx = fixture or self.fx
        return next(
            r for r in data["repositories"] if r["path"] == str(fx.primary)
        )

    # --- baseline: passes before and after the product edit ----------------

    def test_context_baseline_unchanged(self):
        result = run_cli(["context", "--cwd", str(self.fx.primary)], env=self.fx.env())
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["root"], str(self.fx.root))
        self.assertIn(str(self.fx.primary), data["repositories"])
        self.assertEqual(data["persistentBranches"], ["dev", "main"])

    # --- status contract: red on the current product ------------------------

    def test_status_reports_fetch_fresh_inventory(self):
        data = self.load(self.status())
        self.assertEqual(data["root"], str(self.fx.root))
        self.assertEqual(data["planeProject"], PROJECT)
        for key in (
            "repositories",
            "workspaces",
            "pendingDelivery",
            "cleanupEligible",
            "blocked",
        ):
            self.assertIn(key, data)
        row = self.repo_row(data)
        self.assertEqual(row["head"], self.fx.head)
        self.assertEqual(row["current"], "main")
        self.assertFalse(row["detached"])
        self.assertEqual(row["remoteDev"], self.fx.dev)
        self.assertEqual(row["remoteDevError"], None)
        self.assertFalse(row["dirty"])
        self.assertEqual(row["untracked"], [])
        self.assertIsNone(row["operation"])
        self.assertEqual(row["blocked"], [])
        self.assertEqual(row["branches"]["dev"]["local"], self.fx.dev)
        self.assertEqual(row["branches"]["dev"]["remote"], self.fx.dev)
        self.assertTrue(row["branches"]["dev"]["inRemoteDev"])
        self.assertEqual(row["branches"]["main"]["local"], self.fx.head)

    def test_status_is_read_only_for_named_refs(self):
        before = {
            "refs": _git(self.fx.primary, "show-ref"),
            "worktrees": _git(self.fx.primary, "worktree", "list", "--porcelain"),
        }
        self.load(self.status())
        after = {
            "refs": _git(self.fx.primary, "show-ref"),
            "worktrees": _git(self.fx.primary, "worktree", "list", "--porcelain"),
        }
        self.assertEqual(before, after, "status must not move refs or worktrees")

    def test_status_reports_fresh_remote_dev_without_rewriting_tracking_ref(self):
        stale = _git(self.fx.primary, "rev-parse", "refs/remotes/origin/dev")
        fresh = self.fx.advance_remote_dev()
        self.assertNotEqual(stale, fresh)
        data = self.load(self.status())
        self.assertEqual(self.repo_row(data)["remoteDev"], fresh)
        self.assertEqual(
            _git(self.fx.primary, "rev-parse", "refs/remotes/origin/dev"), stale
        )

    def test_status_fails_closed_on_unreadable_paseo(self):
        result = self.status(mode="fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BLOCKED", result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_status_fails_closed_on_absent_requested_workspace(self):
        result = self.status(extra=["--workspace", "wks_missing"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BLOCKED", result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_status_refuses_foreign_requested_workspace(self):
        other = self.fx.tmp / "other"
        other.mkdir()
        projects = [
            {"projectId": PROJECT_ID, "name": PROJECT, "kind": "git",
             "path": str(self.fx.root)},
            {"projectId": "prj_other", "name": "OTHER", "kind": "git",
             "path": str(other)},
        ]
        result = self.status(
            extra=["--workspace", "wks_foreign"],
            workspaces=[workspace("wks_foreign", other, project="OTHER")],
            projects=projects,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BLOCKED", result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_status_workspace_scope_keeps_full_repository_inventory(self):
        wt = self.fx.add_worktree("wt-ok", "task/ok")
        data = self.load(
            self.status(
                extra=["--workspace", "wks_ok"],
                workspaces=[workspace("wks_ok", wt)],
                agents=[agent("agent-ok", wt)],
                inspects=inspect("agent-ok", wt, archived=True),
            )
        )
        self.assertIn(str(self.fx.primary), [r["path"] for r in data["repositories"]])
        self.assertEqual([w["workspaceId"] for w in data["workspaces"]], ["wks_ok"])

    def test_status_blocks_dirty_and_unfinished_repository(self):
        (self.fx.primary / "untracked.txt").write_text("u\n")
        (self.fx.primary / ".git/MERGE_HEAD").write_text(self.fx.head + "\n")
        data = self.load(self.status())
        row = self.repo_row(data)
        self.assertTrue(row["dirty"])
        self.assertIn("untracked.txt", row["untracked"])
        self.assertEqual(row["operation"], "merge")
        self.assertTrue(row["blocked"])

    def test_status_reports_clean_unpublished_task_tip_as_pending_delivery(self):
        wt = self.fx.add_worktree("wt-task", "task/unpublished")
        tip = self.fx.commit_in(wt, "work.txt")
        data = self.load(self.status())
        self.assertTrue(
            any(
                e["head"] == tip and e["reason"] == "not-in-remote-dev"
                for e in data["pendingDelivery"]
            ),
            data["pendingDelivery"],
        )
        entry = next(w for w in self.repo_row(data)["worktrees"] if w["head"] == tip)
        self.assertFalse(entry["inRemoteDev"])
        self.assertNotIn(tip, {w["head"] for w in data["cleanupEligible"]})

    def test_status_cleanup_requires_archived_release_evidence(self):
        ok = self.fx.add_worktree("wt-ok", "task/ok")
        none = self.fx.add_worktree("wt-none", "task/none")
        idle = self.fx.add_worktree("wt-idle", "task/idle")
        agents = [agent("agent-ok", ok), agent("agent-idle", idle)]
        inspects = {
            **inspect("agent-ok", ok, archived=True),
            **inspect("agent-idle", idle, archived=False),
        }
        data = self.load(
            self.status(
                workspaces=[workspace("wks_ok", ok), workspace("wks_none", none),
                            workspace("wks_idle", idle)],
                agents=agents,
                inspects=inspects,
            )
        )
        rows = {w["workspaceId"]: w for w in data["workspaces"]}
        eligible = {w["workspaceId"] for w in data["cleanupEligible"]}
        self.assertTrue(rows["wks_ok"]["archiveEligible"])
        self.assertTrue(rows["wks_ok"]["released"])
        self.assertEqual(rows["wks_ok"]["ignored"], [])
        self.assertIn("wks_ok", eligible)
        self.assertFalse(rows["wks_none"]["archiveEligible"])
        self.assertIn("wks_none", {e["id"] for e in data["blocked"]})
        self.assertTrue(rows["wks_idle"]["busy"])
        self.assertFalse(rows["wks_idle"]["archiveEligible"])
        self.assertNotIn("wks_idle", eligible)

    def test_status_cleanup_blocks_ignored_files(self):
        wt = self.fx.add_worktree("wt-ignored", "task/ignored")
        (wt / "build").mkdir()
        (wt / "build/artifact.bin").write_text("data\n")
        # Normal status is clean; only the ignored scan can see the data.
        self.assertEqual(_git(wt, "status", "--porcelain"), "")
        data = self.load(
            self.status(
                workspaces=[workspace("wks_ignored", wt)],
                agents=[agent("agent-ignored", wt)],
                inspects=inspect("agent-ignored", wt, archived=True),
            )
        )
        row = next(w for w in data["workspaces"] if w["workspaceId"] == "wks_ignored")
        self.assertFalse(row["archiveEligible"])
        self.assertIn("build/artifact.bin", row["ignored"])
        self.assertIn("ignored", " ".join(row["blocked"]).lower())
        self.assertNotIn("wks_ignored", {w["workspaceId"] for w in data["cleanupEligible"]})

    def test_status_cleanup_blocks_locked_worktree(self):
        wt = self.fx.add_worktree("wt-locked", "task/locked")
        _git(self.fx.primary, "worktree", "lock", str(wt))
        data = self.load(
            self.status(
                workspaces=[workspace("wks_locked", wt)],
                agents=[agent("agent-locked", wt)],
                inspects=inspect("agent-locked", wt, archived=True),
            )
        )
        row = next(w for w in data["workspaces"] if w["workspaceId"] == "wks_locked")
        self.assertFalse(row["archiveEligible"])
        entry = next(
            w for w in self.repo_row(data)["worktrees"] if w["path"] == str(wt)
        )
        self.assertTrue(entry["locked"])
        self.assertNotIn("wks_locked", {w["workspaceId"] for w in data["cleanupEligible"]})

    def test_status_fails_closed_on_unreleased_agents(self):
        run = self.fx.add_worktree("wt-run", "task/run")
        perm = self.fx.add_worktree("wt-perm", "task/perm")
        cur = self.fx.add_worktree("wt-cur", "task/cur")
        unk = self.fx.add_worktree("wt-unk", "task/unk")
        arch = self.fx.add_worktree("wt-archunk", "task/archunk")
        agents = [
            agent("agent-run", run, status="running"),
            agent("agent-perm", perm),
            agent(RUNNER, cur, status="running"),
            agent("agent-unk", unk, status="weird"),
            agent("agent-archunk", arch, status="weird"),
        ]
        inspects = {
            **inspect("agent-run", run, archived=False, status="running"),
            **inspect("agent-perm", perm, archived=True,
                      permissions=[{"id": "p1"}]),
            **inspect(RUNNER, cur, archived=False, status="running"),
            **inspect("agent-unk", unk, archived=False, status="weird"),
            # Archived but with no known idle terminal evidence: incomplete, not safe.
            **inspect("agent-archunk", arch, archived=True, status="weird"),
        }
        data = self.load(
            self.status(
                workspaces=[workspace("wks_run", run), workspace("wks_perm", perm),
                            workspace("wks_cur", cur), workspace("wks_unk", unk),
                            workspace("wks_archunk", arch)],
                agents=agents,
                inspects=inspects,
            )
        )
        rows = {w["workspaceId"]: w for w in data["workspaces"]}
        for ws_id in ("wks_run", "wks_perm", "wks_cur", "wks_unk", "wks_archunk"):
            self.assertFalse(rows[ws_id]["archiveEligible"], ws_id)
            self.assertNotIn(ws_id, {w["workspaceId"] for w in data["cleanupEligible"]})
        self.assertTrue(rows["wks_perm"]["busy"])
        self.assertTrue(rows["wks_cur"]["protected"])
        self.assertTrue(rows["wks_unk"]["busy"])
        self.assertFalse(rows["wks_archunk"]["released"])

    def test_status_local_primary_is_never_cleanup_eligible(self):
        data = self.load(
            self.status(
                workspaces=[workspace("wks_primary", self.fx.root, isolation="local")],
                agents=[agent("agent-primary", self.fx.root)],
                inspects=inspect("agent-primary", self.fx.root, archived=True),
            )
        )
        row = next(w for w in data["workspaces"] if w["workspaceId"] == "wks_primary")
        self.assertFalse(row["archiveEligible"])
        self.assertNotIn("wks_primary", {w["workspaceId"] for w in data["cleanupEligible"]})

    def test_status_blocks_ambiguous_project_identity(self):
        wt = self.fx.add_worktree("wt-ambig", "task/ambig")
        projects = [
            {"projectId": "prj_a", "name": PROJECT, "kind": "git",
             "path": str(self.fx.root)},
            {"projectId": "prj_b", "name": PROJECT, "kind": "git",
             "path": str(self.fx.root)},
        ]
        data = self.load(
            self.status(
                workspaces=[workspace("wks_ambig", wt)],
                agents=[agent("agent-ambig", wt)],
                inspects=inspect("agent-ambig", wt, archived=True),
                projects=projects,
            )
        )
        row = next(w for w in data["workspaces"] if w["workspaceId"] == "wks_ambig")
        self.assertEqual(row["ownership"], "unknown")
        self.assertFalse(row["archiveEligible"])
        self.assertIn("wks_ambig", {e["id"] for e in data["blocked"]})

    def test_status_detects_workspace_ref_movement(self):
        wt = self.fx.add_worktree("wt-race", "task/race")
        data = self.load(
            self.status(
                workspaces=[workspace("wks_race", wt)],
                agents=[agent("agent-race", wt)],
                inspects=inspect("agent-race", wt, archived=True),
                hook=f"git -C {wt} commit --allow-empty -m race",
            )
        )
        row = next(w for w in data["workspaces"] if w["workspaceId"] == "wks_race")
        self.assertFalse(row["archiveEligible"])
        self.assertNotIn("wks_race", {w["workspaceId"] for w in data["cleanupEligible"]})
        reasons = [e["reason"].lower() for e in data["blocked"]]
        self.assertTrue(
            any("moved" in r or "race" in r for r in reasons),
            f"ref movement must be reported blocked: {reasons}",
        )


class StatusTopology(unittest.TestCase):
    def test_status_reports_preserve_branch_and_detached_head(self):
        fx = Fixture(preserve={".": ["release"]})
        self.addCleanup(fx.cleanup)
        _git(fx.primary, "branch", "release")
        _git(fx.primary, "push", "origin", "release")
        result = run_cli(["status", "--cwd", str(fx.primary)], env=fx.env())
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        row = next(r for r in data["repositories"] if r["path"] == str(fx.primary))
        self.assertIn("release", row["branches"])
        self.assertEqual(row["branches"]["release"]["local"],
                         _git(fx.primary, "rev-parse", "release"))
        _git(fx.primary, "checkout", "--detach", fx.head)
        result = run_cli(["status", "--cwd", str(fx.primary)], env=fx.env())
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        row = next(r for r in data["repositories"] if r["path"] == str(fx.primary))
        self.assertIsNone(row["current"])
        self.assertTrue(row["detached"])

    def test_status_multi_repo_partial_remote_failure(self):
        fx = Fixture(layout="multi", repositories=["a", "b"], no_origin=["b"])
        self.addCleanup(fx.cleanup)
        result = run_cli(["status", "--cwd", str(fx.repo("a"))], env=fx.env())
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        rows = {Path(r["path"]).name: r for r in data["repositories"]}
        self.assertIn("a", rows)
        self.assertIn("b", rows)
        self.assertIsNotNone(rows["a"]["remoteDev"])
        self.assertIsNone(rows["b"]["remoteDev"])
        self.assertTrue(rows["b"]["remoteDevError"])
        self.assertTrue(rows["b"]["blocked"])
        self.assertFalse(rows["a"]["blocked"])
        self.assertIn(str(fx.repo("b")), {e["id"] for e in data["blocked"]})


if __name__ == "__main__":
    unittest.main()

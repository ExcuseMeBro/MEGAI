"""Observable repository and Plane delivery contracts; no live service calls."""

import copy
import html
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "workflow", ROOT / "pi-defaults/workflow.py"
)
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
STATES = {s: s for s in ("Todo", "In Progress", "In Review", "Done")}


class Delivery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.projects = self.root / "PROJECTS"
        self.projects.mkdir()
        self.env = patch.dict(os.environ, {"PI_PROJECTS_ROOT": str(self.projects)})
        self.env.start()
        self.repo = self.make_repo(self.projects / "APP")
        self.sha = w.git(self.repo, "rev-parse", "HEAD")
        self.receipt = {"repositories": [{"path": str(self.repo), "commit": self.sha}]}
        self.item = {"state": "In Progress", "description_html": "<p>Acceptance</p>"}
        self.writes = []

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def make_repo(self, path):
        path.mkdir(parents=True)
        w.git(path, "init", "-b", "main")
        w.git(path, "config", "user.name", "Test")
        w.git(path, "config", "user.email", "test@example.test")
        (path / "file.txt").write_text("initial\n")
        w.git(path, "add", ".")
        w.git(path, "commit", "-m", "initial")
        remote = self.root / (path.name + "-remote.git")
        subprocess.run(
            ["git", "init", "--bare", str(remote)], check=True, capture_output=True
        )
        w.git(path, "remote", "add", "origin", str(remote))
        w.git(path, "push", "origin", "main")
        return path

    def call(self, tool, args):
        if tool == "project":
            return {"id": "project", "name": "APP"}
        if args["action"] == "retrieve":
            return copy.deepcopy(self.item)
        if args["action"] == "update":
            self.writes.append(args)
            self.item.update(
                {k: v for k, v in args.items() if k in ("state", "description_html")}
            )
            return self.item
        raise AssertionError((tool, args))

    def command(self, *args):
        with (
            patch.object(sys, "argv", ["pi-workflow", *args]),
            patch.object(w, "call", side_effect=self.call),
            patch.object(w, "states", return_value=STATES),
        ):
            return w.main()

    def review(self, receipt=None):
        file = self.root / "receipt.json"
        file.write_text(json.dumps(receipt or self.receipt))
        evidence = self.root / "evidence.txt"
        evidence.write_text("Acceptance tests passed; independent review complete.")
        return self.command(
            "review",
            "--project-id",
            "project",
            "--task-id",
            "task",
            "--receipt",
            str(file),
            "--evidence-file",
            str(evidence),
        )

    def test_main_gate_reads_remote_not_local_main(self):
        w.verify_main(self.receipt)
        (self.repo / "file.txt").write_text("local only\n")
        w.git(self.repo, "commit", "-am", "not delivered")
        self.receipt["repositories"][0]["commit"] = w.git(
            self.repo, "rev-parse", "HEAD"
        )
        with self.assertRaises(ValueError):
            w.verify_main(self.receipt)
        w.git(self.repo, "push", "origin", "main")
        self.assertEqual(len(w.verify_main(self.receipt)), 1)

    def test_group_policy_survives_component_override_and_worktree(self):
        group = self.projects / "GROUP"
        repo = self.make_repo(group / "mobile")
        (group / ".pi").mkdir()
        (group / ".pi/project.json").write_text(
            json.dumps(
                {
                    "layout": "multi",
                    "planeProject": "ADAM",
                    "repositories": ["mobile"],
                    "forge": "git.adam.uz",
                    "preserveBranches": {"mobile": ["validationsdk"]},
                }
            )
        )
        (group / "AGENTS.md").write_text("Group policy")
        (repo / ".pi").mkdir()
        (repo / ".pi/project.json").write_text(
            '{"layout":"mono","planeProject":"wrong"}'
        )
        tree = self.root / "outside"
        w.git(repo, "worktree", "add", "-b", "task/check", str(tree))
        resolved = w.context(tree)
        self.assertEqual(resolved["root"], str(group))
        self.assertEqual(resolved["planeProject"], "ADAM")
        self.assertEqual(resolved["forge"], "git.adam.uz")
        self.assertIn("validationsdk", resolved["preserveBranches"]["mobile"])
        self.assertIn(str(group / "AGENTS.md"), resolved["rules"])

    def test_monorepo_nested_context_uses_one_repository(self):
        nested = self.repo / "packages/api"
        nested.mkdir(parents=True)
        (nested / "AGENTS.md").write_text("API rules")
        result = w.context(nested)
        self.assertEqual(result["repositories"], [str(self.repo)])
        self.assertIn(str(nested / "AGENTS.md"), result["rules"])

    def test_review_normalizes_worktree_and_done_survives_cleanup(self):
        tree = self.root / "task-tree"
        w.git(self.repo, "worktree", "add", "-b", "task/check", str(tree))
        self.receipt["repositories"][0]["path"] = str(tree)
        self.review()
        w.git(self.repo, "worktree", "remove", str(tree))
        result = self.command("done", "--project-id", "project", "--task-id", "task")
        self.assertEqual(result["state"], "Done")

    def test_review_rejects_foreign_project_and_different_task(self):
        foreign = self.make_repo(self.projects / "OTHER")
        self.receipt["repositories"][0]["path"] = str(foreign)
        self.receipt["repositories"][0]["commit"] = w.git(foreign, "rev-parse", "HEAD")
        with self.assertRaisesRegex(ValueError, "different Plane project"):
            self.review()
        self.receipt["task_id"] = "other-task"
        with self.assertRaisesRegex(ValueError, "different Plane task"):
            self.review()
        self.assertEqual(self.writes, [])

    def test_rereview_cannot_drop_old_repository(self):
        self.review()
        old = json.loads(
            html.unescape(
                __import__("re").findall(
                    w.MARKER, self.item["description_html"], __import__("re").S
                )[0]
            )
        )
        second = self.make_repo(self.projects / "SECOND")
        old["repositories"].append(
            {
                "path": str(second),
                "commit": w.git(second, "rev-parse", "HEAD"),
                "remote": "origin",
            }
        )
        self.item["description_html"] = (
            f"<pre>PI_DELIVERY_V1:{html.escape(json.dumps(old))}:END_PI_DELIVERY_V1</pre>"
        )
        with self.assertRaisesRegex(ValueError, "cannot drop"):
            self.review()
        self.assertEqual(len(self.writes), 1)

    def test_done_rejects_concurrent_reopen_without_overwriting(self):
        self.review()
        original = w.verify_main

        def verify(receipt):
            result = original(receipt)
            self.item.update(state="In Progress", description_html="human edit")
            return result

        with (
            patch.object(w, "verify_main", side_effect=verify),
            self.assertRaisesRegex(ValueError, "changed during"),
        ):
            self.command("done", "--project-id", "project", "--task-id", "task")
        self.assertEqual(self.item["description_html"], "human edit")
        self.assertEqual(len(self.writes), 1)

    def test_plane_html_sanitization_keeps_receipt_readable(self):
        self.review()
        # Plane strips data-* attributes; completion metadata must live in text.
        import re

        self.item["description_html"] = re.sub(
            r"<pre[^>]*>", "<pre>", self.item["description_html"]
        )
        result = self.command("done", "--project-id", "project", "--task-id", "task")
        self.assertEqual(result["state"], "Done")

    def test_done_rejects_changed_remote(self):
        self.review()
        w.git(self.repo, "remote", "set-url", "origin", str(self.root / "other.git"))
        with self.assertRaisesRegex(ValueError, "Remote URL changed"):
            self.command("done", "--project-id", "project", "--task-id", "task")
        self.assertEqual(self.item["state"], "In Review")

    def test_pagination_failure_is_not_an_empty_project(self):
        with (
            patch.object(w, "call", return_value={"results": []}),
            self.assertRaisesRegex(ValueError, "Incomplete"),
        ):
            w.pages("project")

    def test_start_creates_todo_then_in_progress_after_all_pages(self):
        calls = []

        def api(tool, args):
            calls.append((tool, args))
            if tool == "project":
                return {
                    "results": [{"name": "APP", "id": "project"}],
                    "next_page_results": False,
                }
            if args["action"] == "list":
                return {"results": [], "next_page_results": False}
            if args["action"] == "create":
                return {"id": "task", "state": args["state"]}
            return {"id": "task", "state": args["state"]}

        with (
            patch.object(
                sys,
                "argv",
                [
                    "pi-workflow",
                    "start",
                    "--cwd",
                    str(self.repo),
                    "--title",
                    "Build feature",
                ],
            ),
            patch.object(w, "call", side_effect=api),
            patch.object(w, "states", return_value=STATES),
        ):
            self.assertEqual(w.main()["state"], "In Progress")
        mutations = [
            args for _, args in calls if args["action"] in ("create", "update")
        ]
        self.assertEqual([m["state"] for m in mutations], ["Todo", "In Progress"])


class InstallerPreflight(unittest.TestCase):
    def test_custom_roots_fail_before_reset(self):
        for variable in ("MEGAI_HOME", "PI_CODING_AGENT_DIR"):
            with (
                self.subTest(variable=variable),
                tempfile.TemporaryDirectory() as temporary,
            ):
                home = Path(temporary)
                marker = home / ".pi/agent/keep.txt"
                marker.parent.mkdir(parents=True)
                marker.write_text("existing session")
                env = {**os.environ, "HOME": str(home)}
                env.pop("MEGAI_HOME", None)
                env.pop("PI_CODING_AGENT_DIR", None)
                env[variable] = str(home / "custom")
                result = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(ROOT / "pi-defaults/install.py"),
                        "--reset",
                    ],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("unsupported", result.stderr)
                self.assertEqual(marker.read_text(), "existing session")


if __name__ == "__main__":
    unittest.main()

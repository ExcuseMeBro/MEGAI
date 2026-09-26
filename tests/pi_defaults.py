"""Observable repository and Plane delivery contracts; no live service calls."""

import copy
import html
import importlib.util
import json
import os
from pathlib import Path
import re
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
install_spec = importlib.util.spec_from_file_location(
    "pi_defaults_install", ROOT / "pi-defaults/install.py"
)
install = importlib.util.module_from_spec(install_spec)
install_spec.loader.exec_module(install)
retire_spec = importlib.util.spec_from_file_location(
    "retire_local_decisions", ROOT / "lib/retire_local_decisions.py"
)
retired = importlib.util.module_from_spec(retire_spec)
retire_spec.loader.exec_module(retired)
DEFAULTS = ROOT / "pi-defaults"
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


class Distribution(unittest.TestCase):
    """The distribution must match the approved clean native-Git profile."""

    def setUp(self):
        self.package = json.loads((DEFAULTS / "package.json").read_text())

    def test_no_pi_subagents_in_packages_settings_or_tools(self):
        self.assertNotIn("pi-subagents", self.package["dependencies"])
        self.assertNotIn("pi-subagents", (DEFAULTS / "package-lock.json").read_text())
        settings = install.profile_settings(
            self.package["dependencies"], Path("/Users/example")
        )
        self.assertNotIn("subagents", settings)
        sources = [entry["source"] for entry in settings["packages"]]
        self.assertEqual([s for s in sources if "subagent" in s], [])
        self.assertFalse(any("pi-superpowers" in s or "ponytail" in s or "openspec" in s for s in sources))
        verify = (DEFAULTS / "verify.mjs").read_text()
        required = re.search(r"const requiredTools = .*?\[(.*?)\];", verify, re.S).group(1)
        self.assertNotIn("subagent", required)
        removed = re.search(r"const removedTools = \[(.*?)\]", verify, re.S).group(1)
        self.assertIn("subagent", removed)
        self.assertNotIn("sift", required)
        profile = (DEFAULTS / "AGENTS.md").read_text()
        self.assertNotIn(retired.TOOL, profile.lower())
        self.assertNotIn("`sift`", profile)
        self.assertNotIn(retired.TOOL, required)

    def test_settings_and_mcp_merge_never_drop_operator_keys(self):
        """An update must keep the chosen provider, model and extra MCP servers.

        The clean profile regenerated both files from scratch, which silently removed
        defaultProvider/defaultModel and every MCP server other than plane.
        """
        current = {
            "theme": "light",
            "defaultProvider": "deepseek",
            "defaultModel": "deepseek-flash",
            "modelThinkingLevels": {"deepseek/deepseek-flash": "high"},
            "skills": ["!~/mine/**"],
            "packages": ["npm:custom-package", {"source": "npm:pi-mcp-adapter@old", "extensions": ["custom-filter"]},
                         "npm:@fission-ai/openspec@1.13.0"],
        }
        settings = install.profile_settings(
            self.package["dependencies"], Path("/Users/example"), current
        )
        self.assertEqual(settings["defaultProvider"], "deepseek")
        self.assertEqual(settings["defaultModel"], "deepseek-flash")
        self.assertEqual(settings["modelThinkingLevels"], {"deepseek/deepseek-flash": "high"})
        self.assertEqual(settings["theme"], "light")
        self.assertIn("!~/mine/**", settings["skills"])
        self.assertIn("npm:custom-package", settings["packages"])
        adapter = next(p for p in settings["packages"] if isinstance(p, dict) and "pi-mcp-adapter" in p["source"])
        self.assertEqual(adapter["extensions"], ["custom-filter"])
        self.assertFalse(any("openspec" in str(p) for p in settings["packages"]))
        self.assertIn("!/Users/example/.agents/skills/**", settings["skills"])
        self.assertEqual(
            [e["source"] for e in settings["packages"] if isinstance(e, dict) and "pi-superpowers" in e["source"]],
            [],
        )
        mcp = install.profile_mcp(
            Path("/tmp/defaults"),
            Path("/Users/example"),
            {"mcpServers": {"pencil": {"url": "https://example.invalid"}},
             "settings": {"directTools": True}},
        )
        self.assertIn("plane", mcp["mcpServers"])
        self.assertIn("pencil", mcp["mcpServers"])
        self.assertIs(mcp["settings"]["directTools"], True)
        self.assertEqual(mcp["settings"]["mcpFooterStatus"], "compact")
        with tempfile.TemporaryDirectory(prefix="megai-settings-") as staging:
            broken = Path(staging) / "settings.json"
            broken.write_text("not json")
            with self.assertRaises(SystemExit):
                install.read_object(broken)

    def test_an_update_keeps_the_injected_policy_blocks(self):
        """Other wirings own the blocks marked inside AGENTS.md; the document is ours."""
        slim = b"<!-- megai:slim:begin -->\n# MEGAI adaptive\nkeep me\n<!-- megai:slim:end -->\n"
        models = b"<!-- megai:subagent-models:begin -->\nPi children: keep me\n<!-- megai:subagent-models:end -->\n"
        current = b"# Pi defaults\nold body\n" + slim + b"\n" + models
        source = b"# Pi defaults\nnew body\n"
        merged = install.profile_agents_md(current, source)
        self.assertTrue(merged.startswith(source))
        self.assertNotIn(b"old body", merged)
        self.assertIn(slim.rstrip(b"\n"), merged)
        self.assertIn(models.rstrip(b"\n"), merged)
        self.assertEqual(install.profile_agents_md(merged, source), merged)
        self.assertEqual(install.profile_agents_md(current, current), current)
        self.assertEqual(install.profile_agents_md(None, source), source)

    def test_the_two_installers_share_one_headroom_bridge(self):
        """lib/slim_wiring.py owns this same path and refuses a differing file."""
        source = (DEFAULTS.parent / "lib/slim_wiring.py").read_text()
        literal = re.search(r"bridge = b'([^']*)'", source).group(1)
        self.assertEqual(
            install.HEADROOM_BRIDGE, literal.encode().decode("unicode_escape").encode()
        )

    def test_the_clean_profile_keeps_one_headroom_adapter(self):
        """Both adapter names expose the same tools, and Pi refuses one of them."""
        with tempfile.TemporaryDirectory(prefix="megai-headroom-") as staging:
            home = Path(staging)
            agent = home / ".pi/agent"
            canonical = agent / "extensions/megai-headroom"
            canonical.mkdir(parents=True)
            (canonical / "index.ts").write_text("canonical")
            duplicate = agent / "extensions/headroom"
            duplicate.mkdir(parents=True)
            (duplicate / "index.ts").write_text("duplicate")
            moved = install.retire_duplicate_headroom(agent, home)
            self.assertFalse(duplicate.exists())
            self.assertEqual(moved.parent, home / ".pi/backups")
            self.assertEqual((moved / "index.ts").read_text(), "duplicate")
            self.assertEqual((canonical / "index.ts").read_text(), "canonical")
            self.assertIsNone(install.retire_duplicate_headroom(agent, home))

    def test_native_policy_and_prompts_are_distributed_and_verified(self):
        policy = (DEFAULTS / "AGENTS.md").read_text()
        self.assertIn("verified task-owned worktree", policy)
        self.assertNotIn("pa" + "seo", policy.lower())
        self.assertNotIn("Use pi-subagents", policy)
        self.assertIn("do not reinstall it", policy)
        names = sorted(p.stem for p in (DEFAULTS / "prompts").glob("*.md"))
        self.assertEqual(names, ["factory", "mdev", "prdev", "rwbrowser"])
        verify = (DEFAULTS / "verify.mjs").read_text()
        for name in names:
            front = (DEFAULTS / f"prompts/{name}.md").read_text().split("---")[1]
            self.assertIn("description:", front)
            self.assertIn(f"'{name}'", verify)
        self.assertIn('SOURCE / "prompts"', (DEFAULTS / "install.py").read_text())
        self.assertIn("Main promotion and pushes require separate explicit approval", policy)
        self.assertIn("No separate reviewer is required", policy)
        self.assertNotIn("Explicit independent-review requests are honored", policy)
        browser = (DEFAULTS / "prompts/rwbrowser.md").read_text()
        self.assertIn("explicitly invoked `/rwbrowser`", browser)
        self.assertIn("bounded browser review only", browser)
        self.assertEqual(browser, (ROOT / ".pi/prompts/rwbrowser.md").read_text())
        self.assertIn("Do not start a browser", (ROOT / "AGENTS.md").read_text())

    def test_verifier_respects_explicit_prompt_exclusions(self):
        verify = (DEFAULTS / "verify.mjs").read_text()
        self.assertIn("selection.prompts", verify)
        self.assertIn("excludedPrompts.has(`-prompts/${name}.md`)", verify)
        self.assertIn("Invalid Pi prompt selection", verify)
        self.assertIn("readFileSync(c.winnerPath).equals(readFileSync(c.loserPath))", verify)
        self.assertIn("diagnostics.length", verify)

    def test_factory_prompt_drains_explicit_scope_and_fails_closed(self):
        prompt = (DEFAULTS / "prompts/factory.md").read_text()
        for clause in (
            "${@:-}", "Todo", "In Progress", "comma-separated", "project identity",
            "all pages", "pi-workflow factory-start", "Git", "In Review", "--no-overwrite-ignore",
            "not a daemon", "no push", "no main", "no Done", "factory-plan",
            "frozen selected UUIDs", "zero Todo", "only blocked/externally owned",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, prompt)
        self.assertNotIn("pi-workflow start --title", prompt)

    def test_delivery_prompts_use_native_git_and_keep_fail_closed_boundaries(self):
        mdev = (DEFAULTS / "prompts/mdev.md").read_text()
        for clause in ("git worktree list --porcelain", "--no-overwrite-ignore",
                       "megai queue plan", "source-current formal PASS", "non-force push",
                       "In Review", "uncertain ownership"):
            self.assertIn(clause, mdev)
        for obsolete in ("pi-workflow status", "pi-workflow cleanup", "pa" + "seo"):
            self.assertNotIn(obsolete, mdev.lower() if obsolete == "pa" + "seo" else mdev)
        prdev = (DEFAULTS / "prompts/prdev.md").read_text()
        for clause in ("github.com", "Missing evidence for the captured `dev` SHA",
                       "No commits in that diff means no PR"):
            self.assertIn(clause, prdev)
        self.assertNotIn("cleanup", subprocess.run(
            [sys.executable, "-B", str(DEFAULTS / "workflow.py"), "--help"],
            capture_output=True, text=True, timeout=10, check=True).stdout)

    def test_pi_version_is_resolved_at_install_and_read_back_from_the_manifest(self):
        """The profile installs the newest Pi and records what it resolved.

        A pinned version went stale: the deployed verify step demanded 0.85.1 while a
        newer Pi was on PATH, so the whole check aborted and verified nothing.
        """
        installer = (DEFAULTS / "install.py").read_text()
        self.assertIn("@latest", installer)
        self.assertNotIn("pi-coding-agent@0.", installer)
        self.assertIn('"pi": installed', installer)
        verify = (DEFAULTS / "verify.mjs").read_text()
        self.assertIn("defaults/manifest.json", verify)
        self.assertNotIn("0.85.1", verify)

    def test_native_worktree_and_user_decision_policy(self):
        policy = (DEFAULTS / "AGENTS.md").read_text()
        for required in (
            "one writer per worktree", "verified task-owned worktree",
            "never edit, stage or commit task source in the dev/main checkout",
            "Never idle over a decision", "at most five minutes",
            "Reserved user decisions", "Main/push/publishing still need separate explicit approval",
            "Cleanup only clean, released, proven-merged task-owned resources",
        ):
            self.assertIn(required, policy)
        self.assertNotIn("pa" + "seo", policy.lower())


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

    def test_a_failed_policy_transaction_is_fatal(self):
        with patch.dict(os.environ, {"MEGAI_PI_POLICY": "false"}):
            with self.assertRaises(SystemExit) as caught:
                install.apply_pi_policy(ROOT, dict(os.environ))
        self.assertIn("inspect the reported conflict and current assets before retry", str(caught.exception))
        self.assertNotIn("rolled back", str(caught.exception))

    def test_a_verified_policy_transaction_continues(self):
        with patch.dict(os.environ, {"MEGAI_PI_POLICY": "true"}):
            install.apply_pi_policy(ROOT, dict(os.environ))

    def test_policy_transaction_runs_after_extension_copy(self):
        source = (ROOT / "pi-defaults/install.py").read_text()
        activation = source.index("apply_pi_policy(REPO, env)")
        self.assertLess(
            source.index('shutil.copytree(SOURCE / "extensions", agent / "extensions"'),
            activation,
        )
        self.assertLess(
            source.index('shutil.copytree(SOURCE / "skills", agent / "skills"'),
            activation,
        )


if __name__ == "__main__":
    unittest.main()

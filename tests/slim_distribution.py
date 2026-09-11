#!/usr/bin/env python3
"""Offline slim acceptance; every child inherits an outer disposable HOME."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Slim(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="megai-slim-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.home = self.root / "home"
        self.megai = self.home / ".megai"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.megai.mkdir(parents=True)
        for folder in ("lib", "pi-skill", "skills", "task-flow", "bin"):
            shutil.copytree(ROOT / folder, self.megai / folder)
        self.env = dict(os.environ, HOME=str(self.home), MEGAI_HOME=str(self.megai),
                        PI_CODING_AGENT_DIR=str(self.home / ".pi/agent"),
                        CODEX_HOME=str(self.home / ".codex"), PASEO_HOME=str(self.home / ".paseo"), OMP_PROFILE="", PI_PROFILE="",
                        PATH=f"{self.bin}:{os.environ['PATH']}", PYTHONDONTWRITEBYTECODE="1")
        # A second outer sandbox protects against single-export shell expansion bugs.
        for key in ("HOME", "MEGAI_HOME", "PI_CODING_AGENT_DIR", "CODEX_HOME"):
            self.assertTrue(Path(self.env[key]).is_relative_to(self.root))
        (self.bin / "python3").symlink_to(sys.executable)
        for name in ("tgrep", "codedb", "zg", "rtk", "ruff", "agentmemory", "pi", "omp", "claude", "codex", "npm", "npx", "curl", "node"):
            self.stub(name, 'printf "%s\\n" "$0 $*" >>"$HOME/calls"\nexit 0\n')
        runtime = self.write(self.megai / "venv/headroom/bin/python", '#!/bin/sh\nprintf "headroom-runtime %s\\n" "$*" >>"$HOME/calls"\n')
        runtime.chmod(0o700)
        (self.megai / "state.json").write_text('{"tools":{},"agents":{},"ports":{"agent-memory":3111},"keep":{"value":42}}\n')
        self.project = self.root / "project"
        self.project.mkdir()
        self.legacy = self.project / ".todos"
        self.legacy.mkdir()
        (self.legacy / "sentinel").write_text("historical private board, never touched\n")
        self.write(self.megai / "lib/ensure_dev.sh", '#!/bin/sh\nprintf "branch-check\\n" >>"$HOME/calls"\n')

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def stub(self, name, body):
        p = self.write(self.bin / name, "#!/bin/sh\n" + body)
        p.chmod(0o755)

    def run_cmd(self, *args, ok=True, env=None, input_text=None):
        result = subprocess.run(args, cwd=self.project, env=env or self.env, text=True, capture_output=True, input=input_text)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def wire(self, *args, **kwargs):
        return self.run_cmd(sys.executable, str(self.megai / "lib/slim_wiring.py"), "pi", *args, **kwargs)

    def snapshot(self):
        result = {}
        for path in self.root.rglob("*"):
            if path.is_file() and not path.is_symlink():
                result[str(path.relative_to(self.root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        return result

    def test_fresh_idempotent_and_ownership_removal(self):
        self.wire()
        before = self.snapshot()
        self.wire()
        self.assertEqual(self.snapshot(), before)
        self.wire("--verify")
        proxy = json.loads((self.home / ".pi/agent/mcp.json").read_text())["mcpServers"]["zvec_grep"]
        self.assertEqual(proxy["lifecycle"], "lazy")
        self.assertTrue((self.home / ".pi/agent/skills/megai-task-flow/SKILL.md").is_file())
        self.assertTrue(os.access(self.megai / "bin/megai-headroom", os.X_OK))
        self.assertFalse((self.megai / "bin/megai-memory").exists())
        self.assertTrue((self.home / ".pi/agent/extensions/megai-headroom/index.ts").is_file())
        self.assertFalse((self.home / ".claude/hooks").exists())
        self.assertEqual((self.legacy / "sentinel").read_text(), "historical private board, never touched\n")
        self.wire("--remove")
        self.assertNotIn("zvec_grep", json.loads((self.home / ".pi/agent/mcp.json").read_text())["mcpServers"])
        self.assertTrue((self.legacy / "sentinel").exists())

    def test_workspace_guard_assets_install_verify_and_remove(self):
        self.wire()
        target = self.home / ".pi/agent/extensions/megai-workspace-guard"
        for name in ("index.ts", "identity.mjs"):
            self.assertEqual((target / name).read_bytes(),
                             (ROOT / "pi-skill/workspace-guard" / name).read_bytes())
        self.assertIn("canonical Git primary/Paseo project",
                      (self.home / ".pi/agent/AGENTS.md").read_text())
        before = self.snapshot()
        self.wire("--verify")
        self.wire()
        self.assertEqual(self.snapshot(), before)
        self.wire("--remove")
        self.assertFalse((target / "index.ts").exists())
        self.assertFalse((target / "identity.mjs").exists())

    def test_custom_workspace_guard_preserved_before_any_write(self):
        self.write(self.home / ".pi/agent/extensions/megai-workspace-guard/index.ts",
                   "user-owned workspace guard")
        before = self.snapshot()
        self.assertIn("custom/legacy asset preserved", self.wire(ok=False).stderr)
        self.assertEqual(self.snapshot(), before)

    def test_workspace_cli_preserves_arguments_without_startup(self):
        self.stub("node", "exec python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]))' \"$@\"\n")
        result = self.run_cmd("bash", str(self.megai / "bin/megai"),
                              "workspace", "--root", "path with spaces")
        self.assertEqual(json.loads(result.stdout),
                         [str(self.megai / "pi-skill/workspace-guard/identity.mjs"),
                          "--root", "path with spaces"])
        self.assertFalse((self.home / "calls").exists())

    def test_acceptance_assets_install_idempotently_and_remove(self):
        self.wire()
        target = self.home / ".pi/agent/skills/megai-acceptance"
        for name in ("SKILL.md", "reference.md", "contract.example.json"):
            self.assertEqual((target / name).read_bytes(),
                             (ROOT / "pi-skill/acceptance" / name).read_bytes())
        self.assertIn("source-current PASS", (self.home / ".pi/agent/AGENTS.md").read_text())
        before = self.snapshot()
        self.wire()
        self.assertEqual(self.snapshot(), before)
        self.wire("--remove")
        self.assertFalse((target / "SKILL.md").exists())
        self.assertFalse((target / "reference.md").exists())
        self.assertFalse((target / "contract.example.json").exists())

    def test_custom_acceptance_asset_blocks_without_overwriting(self):
        target = self.home / ".pi/agent/skills/megai-acceptance/reference.md"
        self.write(target, "user-owned acceptance policy")
        before = self.snapshot()
        result = self.wire(ok=False)
        self.assertIn("custom/legacy asset preserved", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_acceptance_cli_routing_preserves_argv(self):
        self.write(self.megai / "lib/acceptance_gate.py",
                   "import json, sys\nprint(json.dumps(sys.argv[1:]))\n")
        result = self.run_cmd("bash", str(self.megai / "bin/megai"),
                              "acceptance", "snapshot", "--root", "path with spaces")
        self.assertEqual(json.loads(result.stdout),
                         ["snapshot", "--root", "path with spaces"])
        self.assertFalse((self.home / "calls").exists())

    def test_paseo_allows_only_pi_preserving_other_settings(self):
        original = {"version": 1, "daemon": {"listen": "127.0.0.1:6767", "appendSystemPrompt": "keep"},
                    "agents": {"providers": {"codex": {"enabled": True, "model": "keep"},
                                               "pi": {"enabled": False, "thinking": "keep"},
                                               "custom": {"extends": "codex", "enabled": True}},
                               "skills": {"selection": {"mode": "all"}}}}
        config = self.write(self.home / ".paseo/config.json", json.dumps(original))
        before = self.snapshot()
        self.wire("--check")
        self.assertEqual(self.snapshot(), before)
        self.wire()
        actual = json.loads(config.read_text())
        providers = actual["agents"]["providers"]
        self.assertTrue(providers["pi"]["enabled"])
        for name in ("codex", "claude", "omp", "opencode", "copilot", "custom"):
            self.assertFalse(providers[name]["enabled"])
        for name, settings in original["agents"]["providers"].items():
            self.assertEqual({k: v for k, v in providers[name].items() if k != "enabled"},
                             {k: v for k, v in settings.items() if k != "enabled"})
        self.assertEqual(actual["daemon"], original["daemon"])
        self.assertEqual(actual["agents"]["skills"], original["agents"]["skills"])
        before = self.snapshot()
        self.wire()
        self.assertEqual(self.snapshot(), before)
        self.wire("--verify")
        self.assertFalse((self.home / "calls").exists(), "Wiring must not start/reload daemons")
        # Uninstall must not silently re-enable a forbidden harness.
        self.wire("--remove")
        self.assertEqual(json.loads(config.read_text()), actual)

    def test_paseo_malformed_config_fails_before_any_write(self):
        config = self.home / ".paseo/config.json"
        for value in ("{bad", '[]', '{"agents":null}', '{"agents":{"providers":[]}}',
                      '{"agents":{"providers":{"codex":null}}}',
                      '{"agents":{"providers":{"pi":{"enabled":"yes"}}}}'):
            self.write(config, value)
            before = self.snapshot()
            self.wire(ok=False)
            self.assertEqual(self.snapshot(), before)

    def test_paseo_home_override_and_empty_default(self):
        config = self.write(self.home / ".paseo/config.json", '{"version":1}')
        self.wire(env=dict(self.env, PASEO_HOME=""))
        self.assertTrue(json.loads(config.read_text())["agents"]["providers"]["pi"]["enabled"])
        config.write_text("{unrelated malformed default")
        alternate = self.write(self.root / "custom-paseo/config.json", '{"version":1}')
        self.wire(env=dict(self.env, PASEO_HOME=str(alternate.parent)))
        self.assertEqual(config.read_text(), "{unrelated malformed default")
        self.assertTrue(json.loads(alternate.read_text())["agents"]["providers"]["pi"]["enabled"])

    def test_paseo_symlinked_root_is_refused(self):
        outside = self.root / "outside"
        self.write(outside / "config.json", '{"version":1}')
        (self.home / ".paseo").symlink_to(outside)
        before = self.snapshot()
        self.wire(ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_pi_only_delegation_policy_and_optional_paseo(self):
        self.wire()
        self.assertFalse((self.home / ".paseo").exists())
        policy = (self.home / ".pi/agent/AGENTS.md").read_text()
        self.assertIn("Parents and all delegated agents use Pi only", policy)
        core = (self.home / ".pi/agent/skills/megai/SKILL.md").read_text()
        for text in ("--provider pi", "openai-codex/", "returned harness", "no non-GPT or non-Pi fallback"):
            self.assertIn(text, core)

    def test_headroom_defaults_are_wired_without_background_work(self):
        self.wire()
        for root, policy in ((".pi/agent", "AGENTS.md"),):
            text = (self.home / root / policy).read_text()
            for retired in ("caveman", "RTK", "agent-memory"):
                self.assertNotIn(retired, text)
            for required in ("Headroom", "codedb", "zvec-grep", "Ruff", "Matt Pocock/UI-UX", "megai-task-flow", "agent-worktree-lifecycle", "acceptance", "raw"):
                self.assertIn(required, text)
        extension = self.home / ".pi/agent/extensions/megai-headroom/index.ts"
        self.assertEqual(extension.read_bytes(), (ROOT / "pi-skill/headroom/index.ts").read_bytes())
        core = (ROOT / "pi-skill/SKILL.md").read_text()
        for required in ("headroom_retrieve", "Headroom", "raw", "exit status", "acceptance", "on demand"):
            self.assertIn(required, core)
        for required in ("observable acceptance", "original exit status", "full native", "only when the user requests persistence", "No separate enablement request", "independent review"):
            self.assertIn(required, core)
        for retired in ("skills/caveman/SKILL.md", "lib/install_rtk.sh", "lib/install_agent_memory.sh"):
            self.assertFalse((ROOT / retired).exists())
        self.assertFalse((self.home / "calls").exists())
        self.wire("--remove")
        self.assertFalse((self.home / ".pi/agent/skills/caveman/SKILL.md").exists())
        self.assertFalse((self.home / ".pi/agent/skills/caveman/LICENSE.md").exists())

    def test_receipted_old_slim_policy_upgrades_without_overwriting_user_text(self):
        self.wire()
        path = self.home / ".pi/agent/AGENTS.md"
        old = path.read_text().split("Default workflow:", 1)[0] + "<!-- megai:slim:end -->\n"
        path.write_text(old)
        receipt_path = self.megai / "slim-wiring.json"
        receipt = json.loads(receipt_path.read_text())
        receipt[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        receipt_path.write_text(json.dumps(receipt))
        self.wire()
        self.assertIn("Default workflow:", path.read_text())
        self.assertEqual(path.read_text().count("<!-- megai:slim:begin -->"), 1)
        self.wire("--verify")
        # Unrecorded edits outside the exact current block remain user-owned.
        path.write_text("Keep this user rule.\n" + path.read_text())
        self.wire()
        self.assertTrue(path.read_text().startswith("Keep this user rule.\n"))

    def test_caveman_conflicts_and_resource_opt_outs_are_preserved(self):
        custom = self.write(self.home / ".pi/agent/skills/caveman/SKILL.md", "custom user style")
        before = self.snapshot()
        self.wire(ok=False)
        self.assertEqual(self.snapshot(), before)
        custom.unlink()
        settings = self.write(self.home / ".pi/agent/settings.json", json.dumps({
            "defaultModel": "keep", "skills": ["!caveman"], "extensions": ["!rtk*"],
        }))
        original = json.loads(settings.read_text())
        self.wire()
        actual = json.loads(settings.read_text())
        self.assertEqual(actual.pop("skills")[1:], original.pop("skills"))
        self.assertEqual(actual, original)
        skill = self.home / ".pi/agent/extensions/megai-headroom/index.ts"
        skill.write_text(skill.read_text() + "custom change")
        before = self.snapshot()
        self.wire("--remove", ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_pi_only_preserves_other_harnesses_even_when_malformed(self):
        for path in (".claude/settings.json", ".codex/config.toml", ".omp/agent/mcp.json",
                     ".agents/skills/task-flow/SKILL.md", ".agents/skills/caveman/SKILL.md"):
            self.write(self.home / path, "unrelated legacy/custom bytes")
        def others():
            return {p: value for p, value in self.snapshot().items()
                    if p.startswith(("home/.claude/", "home/.codex/", "home/.omp/", "home/.agents/"))}
        before = others()
        self.wire()
        self.wire("--verify")
        self.wire("--remove")
        self.assertEqual(others(), before)
        for client in ("all", "cc", "codex", "omp"):
            before = self.snapshot()
            self.run_cmd(sys.executable, str(self.megai / "lib/slim_wiring.py"), client, ok=False)
            self.assertEqual(self.snapshot(), before)

    def test_skill_kits_use_pi_private_sources_and_migrate_only_pi_links(self):
        matt = self.root / "matt-source"
        self.write(matt / "skills/engineering/example/SKILL.md", '---\nname: example\ndescription: Example\n---\n')
        old = self.write(self.megai / "mattpocock-skills/skills/engineering/example/SKILL.md", "old shared source")
        shared = self.home / ".agents/skills/example"
        shared.parent.mkdir(parents=True)
        shared.symlink_to(old.parent)
        local = self.home / ".pi/agent/skills/example"
        local.parent.mkdir(parents=True)
        local.symlink_to(old.parent)
        self.run_cmd("bash", str(self.megai / "lib/install_mattpocock_skills.sh"), env=dict(self.env, MATTPOCOCK_SKILLS_SOURCE=str(matt)))
        self.assertEqual(old.read_text(), "old shared source")
        self.assertEqual(shared.readlink(), old.parent)
        self.assertEqual(local.readlink(), self.megai / "pi-kits/mattpocock-skills/skills/engineering/example")
        ux = self.root / "ux-source"
        names = "a11y-audit apply-aesthetic brandkit design-code design-component design-qa design-review design-tokens figma-integration governance image-to-code migrate-design-system performance prototype redesign token-build ux-writing".split()
        for name in names:
            self.write(ux / f".claude/skills/{name}/SKILL.md", f"---\nname: {name}\ndescription: Fixture\n---\n")
        self.write(ux / "package.json", '{"version":"fixture"}')
        old_ui = self.write(self.megai / "ux-ui-agent-skills/.megai-skills/a11y-audit/SKILL.md", "keep shared UI")
        link = local.parent / "a11y-audit"
        link.symlink_to(old_ui.parent)
        self.run_cmd("bash", str(self.megai / "lib/install_ux_ui_agent_skills.sh"), env=dict(self.env, UX_UI_AGENT_SKILLS_SOURCE=str(ux)))
        self.assertEqual(old_ui.read_text(), "keep shared UI")
        self.assertEqual(link.readlink(), self.megai / "pi-kits/ux-ui-agent-skills/.megai-skills/a11y-audit")
        self.assertFalse((self.home / ".claude").exists())
        self.assertFalse((self.home / ".codex").exists())
        self.assertFalse((self.home / ".omp").exists())
        self.assertEqual(shared.readlink(), old.parent)
        self.run_cmd("bash", str(self.megai / "lib/install_ux_ui_agent_skills.sh"), "--remove")
        self.assertFalse(link.exists())
        self.assertEqual(old_ui.read_text(), "keep shared UI")

    def test_pi_kit_symlink_ancestors_fail_before_writes(self):
        external = self.root / "outside"
        external.mkdir()
        (self.megai / "pi-kits").symlink_to(external)
        before = self.snapshot()
        for script in ("install_mattpocock_skills.sh", "install_ux_ui_agent_skills.sh"):
            self.run_cmd("bash", str(self.megai / "lib" / script), ok=False)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(list(external.iterdir()), [])

    def test_plane_symlink_ancestors_refused_before_read_or_write(self):
        token = self.write(self.home / "token", "synthetic-secret")
        token.chmod(0o600)
        script = str(self.megai / "lib/plane_mcp.sh")
        for index, relative in enumerate((".pi", ".pi/agent")):
            external = self.root / f"outside-{index}"
            config = self.write(external / ("agent/mcp.json" if index == 0 else "mcp.json"), '{"mcpServers":{}}')
            link = self.home / relative
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(external)
            before = self.snapshot()
            for action in ("setup", "status", "remove", "restore"):
                args = ["--workspace", "test", "--token-file", str(token)] if action == "setup" else []
                result = self.run_cmd("bash", script, action, *args, ok=False)
                self.assertIn("symlinked path", result.stderr)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(config.read_text(), '{"mcpServers":{}}')
            link.unlink()

    def test_plane_lifecycle_is_pi_only_and_preserves_credentials(self):
        token = self.write(self.home / "token", "synthetic-secret")
        token.chmod(0o600)
        config = self.write(self.home / ".pi/agent/mcp.json", '{"mcpServers":{"user":{"command":"keep"}}}')
        other = self.write(self.home / ".codex/config.toml", "invalid but unrelated")
        script = str(self.megai / "lib/plane_mcp.sh")
        for action in ("setup", "status", "remove", "restore"):
            for client in ("all", "codex"):
                before = self.snapshot()
                args = ["--workspace", "test", "--token-file", str(token)] if action == "setup" else []
                self.run_cmd("bash", script, action, *args, "--client", client, ok=False)
                self.assertEqual(self.snapshot(), before)
        self.run_cmd("bash", script, "setup", "--workspace", "test", "--token-file", str(token))
        configured = json.loads(config.read_text())
        self.assertEqual(configured["mcpServers"]["user"], {"command": "keep"})
        self.assertNotIn("synthetic-secret", config.read_text())
        self.run_cmd("bash", script, "status")
        self.run_cmd("bash", script, "remove")
        self.assertNotIn("plane", json.loads(config.read_text())["mcpServers"])
        self.run_cmd("bash", script, "restore")
        self.assertEqual(json.loads(config.read_text()), configured)
        self.assertEqual(other.read_text(), "invalid but unrelated")
        self.assertFalse((self.home / ".claude").exists())
        self.assertFalse((self.home / ".omp").exists())
        before = config.read_bytes()
        token.chmod(0o644)
        self.run_cmd("bash", script, "setup", "--workspace", "test", "--token-file", str(token), ok=False)
        self.assertEqual(config.read_bytes(), before)
        token.chmod(0o600)
        self.run_cmd("bash", script, "setup", "--workspace", "bad/slug", "--token-file", str(token), ok=False)
        self.assertEqual(config.read_bytes(), before)

    def test_installed_gpt_only_pi_delegation_contract(self):
        self.wire()
        for relative in (".pi/agent/AGENTS.md",):
            policy = (self.home / relative).read_text()
            self.assertIn("GPT-only", policy, relative)
            self.assertIn("Pi harness", policy, relative)
            self.assertIn("`megai`", policy, relative)
            self.assertIn("no non-GPT or non-Pi fallback", policy, relative)
        for relative in (".codex/AGENTS.md", ".claude/CLAUDE.md", ".omp/agent/RULES.md", ".agents/skills/megai/SKILL.md"):
            self.assertFalse((self.home / relative).exists(), relative)
        skill = (self.home / ".pi/agent/skills/megai/SKILL.md").read_text()
        for row in (
            "| Parent/orchestrator | `openai-codex/gpt-6-astra` | high |",
            "| Discovery/research | `openai-codex/gpt-5.6-luna` | medium |",
            "| Scoped implementation | `openai-codex/gpt-5.6-luna` | high |",
            "| Independent review, complex debugging or fallback | `openai-codex/gpt-5.6-sol` | high |",
        ):
            self.assertIn(row, skill)
        for requirement in (
            "--provider pi", "--model openai-codex/gpt-5.6-luna", "--thinking high",
            'provider: "pi/openai-codex/gpt-5.6-luna"',
            "settings: {thinkingOptionId: \"high\"}",
            "before sending task context", "neutral preflight prompt",
            "On mismatch, cancel the child", "no non-GPT or non-Pi fallback",
        ):
            self.assertIn(requirement, skill)
        lifecycle = (self.home / ".pi/agent/skills/agent-worktree-lifecycle/SKILL.md").read_text()
        self.assertIn("Select Pi explicitly", lifecycle)
        self.assertIn("`megai`", lifecycle)
        self.wire("--verify")

    def test_owned_delegation_policy_upgrade_and_custom_edit_refusal(self):
        self.wire()
        policy = self.home / ".pi/agent/AGENTS.md"
        skill = self.home / ".pi/agent/skills/megai/SKILL.md"
        previous_policy = (
            "User prefix stays.\n<!-- megai:slim:begin -->\n# MEGAI slim\n"
            "Before project changes, the parent loads `megai-task-flow` and starts the linked Plane item. "
            "Plane is the only execution tracker. Reuse the identity through refinements; children never mutate it. "
            "Use `agent-worktree-lifecycle` for isolated writes and the agreed delivery target. "
            "Verify task acceptance with actual tests and review; security/data-integrity risks require independent review. "
            "Hand off at In Review, never Done. Main promotion requires separate explicit approval.\n"
            "<!-- megai:slim:end -->\nUser suffix stays.\n"
        )
        policy.write_text(previous_policy)
        skill.write_text("# Previous managed MEGAI skill\nCore lookup policy.\n")
        receipt_path = self.megai / "slim-wiring.json"
        receipt = json.loads(receipt_path.read_text())
        for path in (policy, skill):
            receipt[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        receipt_path.write_text(json.dumps(receipt))
        before = self.snapshot()
        result = self.wire("--verify", ok=False)
        self.assertIn("missing/stale", result.stderr)
        self.assertEqual(self.snapshot(), before)
        self.wire("--check")
        self.assertEqual(self.snapshot(), before)
        self.wire()
        self.assertTrue(policy.read_text().startswith("User prefix stays.\n"))
        self.assertTrue(policy.read_text().endswith("User suffix stays.\n"))
        self.assertEqual(policy.read_text().count("<!-- megai:slim:begin -->"), 1)
        self.assertIn("GPT-only delegation", policy.read_text())
        self.assertIn("openai-codex/gpt-6-astra", skill.read_text())
        self.assertIn("openai-codex/gpt-5.6-luna", skill.read_text())
        self.assertIn("openai-codex/gpt-5.6-sol", skill.read_text())
        self.wire("--verify")
        upgraded = self.snapshot()
        self.wire()
        self.assertEqual(self.snapshot(), upgraded)
        policy.write_text(policy.read_text().replace("GPT-only delegation", "Custom routing exception"))
        custom = self.snapshot()
        result = self.wire(ok=False)
        self.assertIn("custom slim policy preserved", result.stderr)
        self.assertEqual(self.snapshot(), custom)

    def test_user_config_and_policy_text_survive(self):
        files = {
            ".pi/agent/settings.json": '{"defaultProvider":"keep","defaultModel":"keep","defaultThinkingLevel":"high","packages":["user-extension"],"skills":["user-skill"]}',
            ".pi/agent/auth.json": '{"private-test":"unchanged"}',
            ".codex/config.toml": 'model = "keep"\n[mcp_servers.user]\ncommand = "custom"\n',
            ".claude.json": '{"mcpServers":{"user":{"command":"custom"}}}',
            ".claude/settings.json": '{"hooks":{"SessionStart":[{"hooks":[{"command":"user-hook"}]}]},"statusLine":{"command":"custom-status"}}',
        }
        for path, content in files.items():
            self.write(self.home / path, content)
        self.write(self.home / ".pi/agent/AGENTS.md", "User policy stays exactly.\n")
        self.wire()
        for path, content in files.items():
            if path == ".pi/agent/settings.json":
                actual = json.loads((self.home / path).read_text())
                expected = json.loads(content)
                self.assertEqual(actual.pop("skills")[1:], expected.pop("skills"))
                self.assertEqual(actual, expected)
            else:
                self.assertEqual((self.home / path).read_text(), content, path)
        self.assertTrue((self.home / ".pi/agent/AGENTS.md").read_text().startswith("User policy stays exactly.\n"))
        before = self.snapshot()
        self.wire()
        self.assertEqual(self.snapshot(), before)

    def test_malformed_late_config_fails_before_any_write(self):
        self.write(self.home / ".pi/agent/mcp.json", '{bad JSON')
        before = self.snapshot()
        self.wire(ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_legacy_hooks_and_skills_require_manual_migration(self):
        paths = [
            (".pi/agent/settings.json", '{"hooks":{"SessionStart":[{"hooks":[{"command":"custom && taskflow-session.js"}]}]}}'),
            (".pi/agent/skills/task-flow/SKILL.md", "custom legacy skill"),
            (".pi/agent/AGENTS.md", "custom .todos rules"),
            (".pi/agent/mcp.json", '{bad'),
        ]
        for path, content in paths:
            target = self.write(self.home / path, content)
            before = self.snapshot()
            self.wire(ok=False)
            self.assertEqual(self.snapshot(), before, path)
            target.unlink()
            # A retired empty skill directory is still ambiguous; remove the fixture.
            if "skills/task-flow" in path:
                target.parent.rmdir()

    def test_symlink_ancestor_and_custom_assets_preserved(self):
        external = self.root / "outside"
        external.mkdir()
        (self.home / ".pi").symlink_to(external, target_is_directory=True)
        self.wire(ok=False)
        self.assertEqual(list(external.iterdir()), [])
        (self.home / ".pi").unlink()
        path = self.write(self.home / ".pi/agent/skills/megai/SKILL.md", "user-owned")
        before = self.snapshot()
        self.wire(ok=False)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(path.read_text(), "user-owned")

    def test_missing_search_and_unowned_proxy_fail(self):
        path = self.write(self.home / ".pi/agent/mcp.json", '{"mcpServers":{"zvec_grep":{"command":"custom-zg"},"plane":{"url":"https://example.invalid"}}}')
        before = self.snapshot()
        self.wire(ok=False)
        self.assertEqual(self.snapshot(), before)
        path.unlink()
        (self.bin / "zg").unlink()
        # Restrict PATH to prevent the host's installed zg from satisfying readiness.
        env = dict(self.env, PATH=f"{self.bin}:/usr/bin:/bin")
        self.run_cmd(sys.executable, str(self.megai / "lib/slim_wiring.py"), "pi", ok=False, env=env)
        self.assertFalse((self.megai / "slim-wiring.json").exists())

    def test_startup_all_harnesses_and_profile_do_not_prewarm(self):
        self.wire()
        before = self.snapshot()
        self.run_cmd("bash", str(self.megai / "bin/megai"), "pi", "--version")
        for client in ("cc", "codex", "omp"):
            self.run_cmd("bash", str(self.megai / "bin/megai"), client, "--version", ok=False)
            self.run_cmd("bash", str(self.megai / "bin/megai"), "wire", client, ok=False)
        self.run_cmd("bash", str(self.megai / "bin/megai"))
        calls = (self.home / "calls").read_text()
        for name in ("zg", "agentmemory", "npm", "npx", "curl", "node", "rtk"):
            self.assertNotIn(str(self.bin / name), calls)
        self.assertEqual(calls.count("branch-check"), 2)
        after = self.snapshot()
        after.pop("home/calls")
        self.assertEqual(before, after)
        for client in ("all", "cc", "codex", "omp"):
            self.run_cmd(sys.executable, str(self.megai / "lib/slim_wiring.py"), client, ok=False)
        self.assertEqual((self.home / "calls").read_text(), calls)

    def test_codedb_default_lookup_preserves_existing_mcp_and_indexes(self):
        config = self.write(self.home / ".codex/config.toml", '[mcp_servers.codedb]\ncommand="user-codedb"\n')
        original = config.read_bytes()
        snapshot = self.write(self.project / "codedb.snapshot", "existing index")
        self.wire()
        self.assertEqual(config.read_bytes(), original)
        wrapper = str(self.megai / "bin/megai-codedb")
        self.run_cmd(wrapper, "symbol", "MySymbol")
        self.run_cmd(wrapper, "outline", "src/main.py")
        self.run_cmd(wrapper, "index", ".")
        calls = (self.home / "calls").read_text()
        self.assertIn("codedb find MySymbol", calls)
        self.assertIn("codedb outline src/main.py", calls)
        self.assertIn("codedb . tree", calls)
        self.assertEqual(snapshot.read_text(), "existing index")
        self.wire("--remove")
        self.assertEqual(config.read_bytes(), original)
        self.assertFalse(Path(wrapper).exists())

    def test_codedb_installer_reuse_and_checksum_failure_are_safe(self):
        self.stub("codedb", 'echo "codedb 0.2.56"\n')
        (self.bin / "jq").symlink_to(shutil.which("jq"))
        env = dict(self.env, PATH=f"{self.bin}:/usr/bin:/bin")
        installer = str(self.megai / "lib/install_codedb.sh")
        index = self.write(self.project / "codedb.snapshot", "retain")
        self.run_cmd("bash", installer, env=env)
        self.run_cmd("bash", installer, env=dict(env, MEGAI_UPDATE="1"))
        self.assertEqual(json.loads((self.megai / "state.json").read_text())["tools"]["codedb"]["version"], "codedb 0.2.56")
        self.assertFalse((self.home / "calls").exists())
        (self.bin / "codedb").unlink()
        self.stub("uname", 'case "$1" in -s) echo Darwin;; -m) echo arm64;; esac\n')
        self.stub("curl", 'echo "$*" >"$HOME/download-call"\nwhile [ "$#" -gt 0 ]; do if [ "$1" = -o ]; then shift; echo invalid-binary >"$1"; break; fi; shift; done\n')
        self.run_cmd("bash", installer, ok=False, env=env)
        self.assertIn("/v0.2.56/codedb-darwin-arm64", (self.home / "download-call").read_text())
        self.assertFalse((self.megai / "bin/codedb").exists())
        self.assertEqual(index.read_text(), "retain")
        self.assertFalse((self.home / ".claude.json").exists())
        self.assertFalse((self.home / ".codedb").exists())

    def test_explicit_zvec_reindex_does_not_rebuild_codedb(self):
        self.run_cmd("bash", str(self.megai / "bin/megai"), "reindex")
        calls = (self.home / "calls").read_text()
        self.assertIn("--embedding local/potion-code-16m-v2", calls)
        self.write(self.project / ".zvec-grep/manifest.json", '{}')
        self.run_cmd("bash", str(self.megai / "bin/megai"), "reindex")
        self.assertIn("--rebuild", (self.home / "calls").read_text())
        self.assertNotIn("codedb", (self.home / "calls").read_text())

    def test_search_installer_pin_reuse_and_data_preservation(self):
        (self.bin / "zg").unlink()
        (self.bin / "jq").symlink_to(shutil.which("jq"))
        self.stub("npm", 'printf "%s\\n" "$*" >>"$HOME/npm-calls"\nprintf "#!/bin/sh\\necho zg-0.2.1\\n" >"$TEST_BIN/zg"\nchmod +x "$TEST_BIN/zg"\n')
        self.write(self.megai / "venv/cocoindex/user-data", "retain unrelated data")
        env = dict(self.env, TEST_BIN=str(self.bin), PATH=f"{self.bin}:/usr/bin:/bin")
        installer = str(self.megai / "lib/install_zvec_grep.sh")
        self.run_cmd("bash", installer, env=env)
        self.run_cmd("bash", installer, env=dict(env, MEGAI_UPDATE="1"))
        self.assertEqual((self.home / "npm-calls").read_text().splitlines(), ["install -g --ignore-scripts @zvec/zvec-grep@0.2.1"])
        self.assertEqual((self.megai / "venv/cocoindex/user-data").read_text(), "retain unrelated data")
        self.assertFalse((self.project / ".zvec-grep").exists())

    def test_pipeline_install_update_exact_stack_and_failure(self):
        self.wire()
        self.write(self.megai / "pi-kits/ux-ui-agent-skills/package.json", '{}')
        (self.megai / "pi-kits/mattpocock-skills/skills").mkdir(parents=True)
        selected = ("headroom", "tgrep", "zvec_grep", "codedb", "ruff", "ux_ui_agent_skills", "mattpocock_skills", "taskflow", "worktree_lifecycle", "pi_packages")
        for path in (self.megai / "lib").glob("install_*.sh"):
            name = path.stem.removeprefix("install_")
            self.write(path, f'#!/bin/sh\necho install:{name} >>"$HOME/install-calls"\n')
        for client in ("cc", "codex", "pi", "omp", "path"):
            self.write(self.megai / f"lib/wire_{client}.sh", '#!/bin/sh\nexit 0\n')
        self.write(self.megai / "lib/detect.sh", 'detect_os() { MEGAI_OS=test; MEGAI_ARCH=test; }\ndetect_runtimes() { MEGAI_HAS_CURL=1; MEGAI_HAS_PY=1; MEGAI_HAS_NODE=1; MEGAI_HAS_JQ=1; }\nrequire_or_install_jq() { :; }\nrequire_or_install_node() { :; }\nrequire_or_install_pipx() { :; }\n')
        for command in ("install", "update", "install"):
            self.run_cmd("bash", str(self.megai / "bin/megai"), command)
        calls = (self.home / "install-calls").read_text().splitlines()
        self.assertEqual(calls, [f"install:{name}" for name in selected] * 3)
        self.write(self.megai / "lib/install_ruff.sh", '#!/bin/sh\nexit 7\n')
        self.run_cmd("bash", str(self.megai / "bin/megai"), "update", ok=False)

    def test_owned_skill_update_and_custom_edit_refusal(self):
        self.wire()
        source = self.megai / "pi-skill/SKILL.md"
        source.write_text(source.read_text() + "\nUpdated distribution guidance.\n")
        self.wire()
        installed = self.home / ".pi/agent/skills/megai/SKILL.md"
        self.assertEqual(installed.read_text(), source.read_text())
        installed.write_text(installed.read_text() + "custom local rule")
        before = self.snapshot()
        self.wire("--remove", ok=False)
        self.assertEqual(before, self.snapshot())

    def test_rollback_and_concurrent_edit_refusal(self):
        code = '''
import os,sys
from pathlib import Path
sys.path.insert(0, str(Path(os.environ['MEGAI_HOME'])/'lib'))
import slim_wiring as w
first=w.HOME/'first'; second=w.HOME/'second'
first.write_bytes(b'original')
p=w.Plan();p.stage(first,b'new',b'original');p.stage(second,b'new',None)
real=w.atomic_write; count=0
def injected(path,data):
 global count
 count+=1
 if count==2: raise OSError('injected write failure')
 real(path,data)
w.atomic_write=injected
try:p.apply(False)
except OSError:pass
else:raise AssertionError('write failure swallowed')
assert first.read_bytes()==b'original' and not second.exists()
w.atomic_write=real
p=w.Plan();p.stage(first,b'new',b'original');first.write_bytes(b'concurrent user edit')
try:p.apply(False)
except ValueError:pass
else:raise AssertionError('concurrent edit overwritten')
assert first.read_bytes()==b'concurrent user edit'
'''
        self.run_cmd(sys.executable, "-c", code)

    def test_headroom_bridge_dispatches_without_proxy_or_old_memory(self):
        self.wire()
        self.run_cmd("bash", str(self.megai / "bin/megai"), "headroom", "recall", 'quoted " query')
        calls = (self.home / "calls").read_text()
        self.assertIn("headroom/bridge.py recall", calls)
        self.assertNotIn("agentmemory", calls)
        self.assertNotIn("curl", calls)
        self.assertFalse((self.megai / "bin/megai-memory").exists())

    def test_matt_source_and_custom_skill_preservation(self):
        source = self.root / "matt-source"
        self.write(source / "skills/engineering/example/SKILL.md", '---\nname: example\ndescription: Example\n---\n')
        custom = self.write(self.home / ".pi/agent/skills/example/SKILL.md", "user customization")
        env = dict(self.env, MATTPOCOCK_SKILLS_SOURCE=str(source))
        self.run_cmd("bash", str(self.megai / "lib/install_mattpocock_skills.sh"), env=env)
        kit = self.megai / "pi-kits/mattpocock-skills"
        self.write(kit / "local-note", "keep custom source data")
        self.run_cmd("bash", str(self.megai / "lib/install_mattpocock_skills.sh"), env=env)
        self.assertEqual(custom.read_text(), "user customization")
        saved = list((self.megai / "backups").glob("matt-source.*/source/local-note"))
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].read_text(), "keep custom source data")
        self.assertFalse((self.home / "calls").exists())

    def test_pi_adapter_preserves_explicit_selection_and_ignores_full_flag(self):
        path = self.write(self.home / ".pi/agent/settings.json", json.dumps({"defaultModel": "keep", "packages": [{"source": "npm:pi-mcp-adapter", "enabled": False}, "npm:user", "npm:pi-subagents"]}))
        before = path.read_bytes()
        self.run_cmd("bash", str(self.megai / "lib/install_pi_packages.sh"), env=dict(self.env, MEGAI_PI_FULL="1"))
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((self.home / "calls").exists())
        path.write_text('{"packages":[]}')
        self.run_cmd("bash", str(self.megai / "lib/install_pi_packages.sh"), env=dict(self.env, MEGAI_PI_FULL="1"))
        calls = (self.home / "calls").read_text()
        self.assertEqual(calls.count("install npm:pi-mcp-adapter"), 1)
        self.assertNotIn("pi-subagents", calls)

    def test_source_install_backs_up_without_deleting_custom_files(self):
        source = self.root / "source"
        source.mkdir()
        for folder in ("lib", "bin", "pi-skill", "omp-skill", "task-flow", "skills"):
            (source / folder).mkdir()
        self.write(source / "bin/megai", "#!/bin/sh\necho new-source\n")
        self.write(self.megai / "bin/user-tool", "retain")
        previous = (self.megai / "bin/megai").read_bytes()
        self.run_cmd(sys.executable, str(self.megai / "lib/install_slim_source.py"), str(source))
        self.assertEqual((self.megai / "bin/user-tool").read_text(), "retain")
        manifests = list((self.megai / "backups").glob("slim-wiring-*/manifest.json"))
        manifest = json.loads(manifests[0].read_text())
        self.assertEqual((manifests[0].parent / manifest[str(self.megai / "bin/megai")]).read_bytes(), previous)

    def test_uninstall_conflicts_preflight_before_plane_mutation(self):
        self.wire()
        self.write(self.megai / "lib/plane_mcp.sh", '#!/bin/sh\necho mutated >"$HOME/plane-mutated"\n')
        skill = self.home / ".pi/agent/skills/megai/SKILL.md"
        original = skill.read_text()
        skill.write_text(original + "custom rule")
        before = self.snapshot()
        self.run_cmd("bash", str(self.megai / "bin/megai"), "uninstall", ok=False, input_text="y\n")
        self.assertEqual(before, self.snapshot())
        skill.write_text(original)
        rc = next(path for path in (self.home / ".bashrc", self.home / ".zshrc", self.home / ".profile") if path.exists())
        rc.write_text('# >>> megai-managed (do not edit) >>>\ncustom user shell code\n# <<< megai-managed <<<\n')
        before = self.snapshot()
        self.run_cmd("bash", str(self.megai / "bin/megai"), "uninstall", ok=False, input_text="y\n")
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.home / "plane-mutated").exists())

    def test_doctor_requires_every_selected_tool_and_skill_kit(self):
        self.wire()
        self.stub("ruff", 'echo "ruff 0.15.0"\n')
        for name in ("bash", "jq", "git", "rg", "find", "grep", "env"):
            if not (self.bin / name).exists():
                (self.bin / name).symlink_to(shutil.which(name))
        env = dict(self.env, PATH=str(self.bin))
        ui = self.write(self.megai / "pi-kits/ux-ui-agent-skills/package.json", '{}')
        self.write(self.megai / "pi-kits/ux-ui-agent-skills/.megai-skills/a11y-audit/SKILL.md", 'fixture')
        matt = self.write(self.megai / "pi-kits/mattpocock-skills/skills/example/SKILL.md", 'fixture')
        self.run_cmd("bash", str(self.megai / "bin/megai"), "doctor", env=env)
        for path in (self.bin / "codedb", self.megai / "venv/headroom/bin/python", ui, matt):
            hidden = path.with_name(path.name + ".hidden")
            path.rename(hidden)
            self.run_cmd("bash", str(self.megai / "bin/megai"), "doctor", ok=False, env=env)
            hidden.rename(path)

    def test_retired_daemon_commands_do_not_start_services(self):
        self.wire()
        for command in ("start", "stop", "logs"):
            self.run_cmd("bash", str(self.megai / "bin/megai"), command, ok=False)
        self.assertFalse((self.home / "calls").exists())
        self.assertFalse((self.megai / "memory-process.json").exists())

    def test_state_values_are_data_and_malformed_state_preserved(self):
        value = json.dumps({"value": 'quote " | error("injected")'})
        result = self.run_cmd("bash", "-c", '. "$MEGAI_HOME/lib/state.sh"; state_set .tools.test "$1"', "test", value)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads((self.megai / "state.json").read_text())["tools"]["test"], json.loads(value))
        (self.megai / "state.json").write_text("not-json")
        self.run_cmd("bash", "-c", '. "$MEGAI_HOME/lib/state.sh"; state_set .tools.test "{}"', ok=False)
        self.assertEqual((self.megai / "state.json").read_text(), "not-json")

    def test_policy_guards_and_public_branch(self):
        policy = (ROOT / "task-flow/skills/megai-task-flow/SKILL.md").read_text()
        for required in ("every Plane project page", "every workflow-state page", "group=started", "automatically create exactly one item without asking for approval", "In Progress", "In Review", "Only the user", "independent review", "persistent branch", "unavailable", "before retrying"):
            self.assertIn(required.lower(), policy.lower())
        for active in (ROOT / "pi-skill/SKILL.md", ROOT / "skills/agent-worktree-lifecycle/SKILL.md", ROOT / "task-flow/skills/megai-task-flow/SKILL.md"):
            self.assertNotIn(".todos", active.read_text())
            self.assertNotIn("MiniMax", active.read_text())
        self.assertIn('MEGAI_REF="${MEGAI_REF:-slim}"', (ROOT / "install.sh").read_text())
        for flag in ("--no-fix", "--no-fix-only", "--no-cache", "ruff format --check"):
            self.assertIn(flag, (ROOT / "pi-skill/SKILL.md").read_text())


if __name__ == "__main__":
    unittest.main()

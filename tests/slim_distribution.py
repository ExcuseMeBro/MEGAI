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
                        CODEX_HOME=str(self.home / ".codex"), OMP_PROFILE="", PI_PROFILE="",
                        PATH=f"{self.bin}:{os.environ['PATH']}", PYTHONDONTWRITEBYTECODE="1")
        # A second outer sandbox protects against single-export shell expansion bugs.
        for key in ("HOME", "MEGAI_HOME", "PI_CODING_AGENT_DIR", "CODEX_HOME"):
            self.assertTrue(Path(self.env[key]).is_relative_to(self.root))
        (self.bin / "python3").symlink_to(sys.executable)
        for name in ("zg", "rtk", "ruff", "agentmemory", "pi", "omp", "claude", "codex", "npm", "npx", "curl", "node"):
            self.stub(name, 'printf "%s\\n" "$0 $*" >>"$HOME/calls"\nexit 0\n')
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

    def run_cmd(self, *args, ok=True, env=None):
        result = subprocess.run(args, cwd=self.project, env=env or self.env, text=True, capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def wire(self, *args, **kwargs):
        return self.run_cmd(sys.executable, str(self.megai / "lib/slim_wiring.py"), "all", *args, **kwargs)

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
        self.assertTrue((self.home / ".agents/skills/megai-task-flow/SKILL.md").is_file())
        self.assertTrue(os.access(self.megai / "bin/megai-memory", os.X_OK))
        self.assertFalse((self.home / ".claude/hooks").exists())
        self.assertEqual((self.legacy / "sentinel").read_text(), "historical private board, never touched\n")
        self.wire("--remove")
        self.assertNotIn("zvec_grep", json.loads((self.home / ".pi/agent/mcp.json").read_text())["mcpServers"])
        self.assertTrue((self.legacy / "sentinel").exists())

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
            self.assertEqual((self.home / path).read_text(), content, path)
        self.assertTrue((self.home / ".pi/agent/AGENTS.md").read_text().startswith("User policy stays exactly.\n"))
        before = self.snapshot()
        self.wire()
        self.assertEqual(self.snapshot(), before)

    def test_malformed_late_config_fails_before_any_write(self):
        self.write(self.home / ".omp/agent/mcp.json", '{bad JSON')
        before = self.snapshot()
        self.wire(ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_legacy_hooks_and_skills_require_manual_migration(self):
        paths = [
            (".claude/settings.json", '{"hooks":{"SessionStart":[{"hooks":[{"command":"custom && taskflow-session.js"}]}]}}'),
            (".agents/skills/task-flow/SKILL.md", "custom legacy skill"),
            (".pi/agent/AGENTS.md", "custom .todos rules"),
            (".codex/config.toml", '[mcp_servers.codedb]\ncommand="custom"\n'),
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
        (self.home / ".claude").symlink_to(external, target_is_directory=True)
        self.wire(ok=False)
        self.assertEqual(list(external.iterdir()), [])
        (self.home / ".claude").unlink()
        path = self.write(self.home / ".agents/skills/megai/SKILL.md", "user-owned")
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
        self.run_cmd(sys.executable, str(self.megai / "lib/slim_wiring.py"), "all", ok=False, env=env)
        self.assertFalse((self.megai / "slim-wiring.json").exists())

    def test_startup_all_harnesses_and_profile_do_not_prewarm(self):
        self.wire()
        before = self.snapshot()
        for client in ("cc", "codex", "pi", "omp"):
            self.run_cmd("bash", str(self.megai / "bin/megai"), client, "--version")
        self.run_cmd("bash", str(self.megai / "bin/megai"))
        calls = (self.home / "calls").read_text()
        for name in ("zg", "agentmemory", "npm", "npx", "curl", "node", "rtk"):
            self.assertNotIn(str(self.bin / name), calls)
        self.assertEqual(calls.count("branch-check"), 5)
        after = self.snapshot()
        after.pop("home/calls")
        self.assertEqual(before, after)
        env = dict(self.env, OMP_PROFILE="work")
        self.run_cmd(sys.executable, str(self.megai / "lib/slim_wiring.py"), "omp", env=env)
        self.run_cmd("bash", str(self.megai / "bin/megai"), "omp", "--profile", "work", "--version")
        self.assertIn("--profile work --version", (self.home / "calls").read_text())

    def test_explicit_reindex_without_codedb(self):
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
        self.write(self.megai / "ux-ui-agent-skills/package.json", '{}')
        (self.megai / "mattpocock-skills/skills").mkdir(parents=True)
        selected = ("agent_memory", "zvec_grep", "rtk", "ruff", "ux_ui_agent_skills", "mattpocock_skills", "taskflow", "worktree_lifecycle", "pi_packages")
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
        installed = self.home / ".agents/skills/megai/SKILL.md"
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

    def test_memory_bridge_has_bounded_http_and_no_startup(self):
        self.wire()
        self.run_cmd(str(self.megai / "bin/megai-memory"), "recall", 'quoted " query')
        calls = (self.home / "calls").read_text()
        self.assertIn("--connect-timeout 3 --max-time 15", calls)
        self.assertIn("smart-search", calls)
        self.assertNotIn("agentmemory --port", calls)
        for port in ("3111@remote.invalid", "0", "65536", "not-a-port"):
            self.run_cmd(str(self.megai / "bin/megai-memory"), "recall", "private-test", ok=False, env=dict(self.env, AGENTMEMORY_PORT=port))
        self.assertEqual((self.home / "calls").read_text(), calls)

    def test_matt_source_and_custom_skill_preservation(self):
        source = self.root / "matt-source"
        self.write(source / "skills/engineering/example/SKILL.md", '---\nname: example\ndescription: Example\n---\n')
        custom = self.write(self.home / ".agents/skills/example/SKILL.md", "user customization")
        env = dict(self.env, MATTPOCOCK_SKILLS_SOURCE=str(source))
        self.run_cmd("bash", str(self.megai / "lib/install_mattpocock_skills.sh"), env=env)
        kit = self.megai / "mattpocock-skills"
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
        for required in ("every Plane project page", "every workflow-state page", "group=started", "ask approval to create", "In Progress", "In Review", "Only the user", "independent review", "persistent branch", "unavailable", "before retrying"):
            self.assertIn(required.lower(), policy.lower())
        for active in (ROOT / "pi-skill/SKILL.md", ROOT / "skills/agent-worktree-lifecycle/SKILL.md", ROOT / "task-flow/skills/megai-task-flow/SKILL.md"):
            self.assertNotIn(".todos", active.read_text())
            self.assertNotIn("MiniMax", active.read_text())
        self.assertIn('MEGAI_REF="${MEGAI_REF:-slim}"', (ROOT / "install.sh").read_text())
        for flag in ("--no-fix", "--no-fix-only", "--no-cache", "ruff format --check"):
            self.assertIn(flag, (ROOT / "pi-skill/SKILL.md").read_text())


if __name__ == "__main__":
    unittest.main()

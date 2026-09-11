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
        for name in ("tgrep", "codedb", "zg", "ruff", "pi", "omp", "claude", "codex", "npm", "npx", "curl", "node"):
            self.stub(name, 'printf "%s\\n" "$0 $*" >>"$HOME/calls"\nexit 0\n')
        (self.megai / "state.json").write_text('{"tools":{},"agents":{},"ports":{"agent-memory":3111},"keep":{"value":42}}\n')
        self.project = self.root / "project"
        self.project.mkdir()
        # Shared retired Caveman resources are intentionally absent; ambiguous
        # legacy content must block adoption rather than become an active default.
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
        self.assertTrue(os.access(self.megai / "bin/megai-headroom", os.X_OK))
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
        for root in (".agents", ".claude", ".omp/agent"):
            self.assertFalse((self.home / root / "skills/megai-acceptance").exists())
        self.assertIn("source-current PASS", (self.home / ".pi/agent/AGENTS.md").read_text())
        before = self.snapshot()
        self.wire()
        self.assertEqual(self.snapshot(), before)
        self.wire("--remove")
        for name in ("SKILL.md", "reference.md", "contract.example.json"):
            self.assertFalse((target / name).exists())

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

    def test_task_workspaces_return_to_primary_after_delivery(self):
        policy = (ROOT / "skills/agent-worktree-lifecycle/SKILL.md").read_text()
        for clause in ("Each new task", "one primary workspace at rest",
                       "same task", "safely merged", "read-only reviewers"):
            self.assertIn(clause, policy)
        self.assertNotIn("megai finish --verified", policy)
        self.assertLess(policy.index("Release all task writers"),
                        policy.index("git -C PRIMARY merge --ff-only"))
        self.assertIn("does not enforce branch/base/title", policy)
        self.wire()
        self.assertIn("one primary workspace after verified delivery",
                      (self.home / ".pi/agent/AGENTS.md").read_text())

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
                continue  # slim owns only the managed Pi selection delta
            self.assertEqual((self.home / path).read_text(), content, path)
        settings = json.loads((self.home / ".pi/agent/settings.json").read_text())
        self.assertEqual(settings["defaultProvider"], "keep")
        self.assertEqual(settings["defaultModel"], "keep")
        self.assertEqual(settings["defaultThinkingLevel"], "high")
        self.assertEqual(settings["packages"], ["user-extension"])
        self.assertIn("user-skill", settings["skills"])
        self.assertTrue(any(item.endswith("/.agents/skills/**") and item.startswith("!") for item in settings["skills"]))
        self.assertTrue((self.home / ".pi/agent/skills/megai/SKILL.md").is_file())
        self.assertTrue((self.home / ".pi/agent/AGENTS.md").read_text().startswith("User policy stays exactly.\n"))
        before = self.snapshot()
        self.wire()
        self.assertEqual(self.snapshot(), before)

    def test_malformed_late_config_fails_before_any_write(self):
        self.write(self.home / ".omp/agent/mcp.json", '{bad JSON')
        before = self.snapshot()
        self.wire(ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_shared_retired_skill_blocks_and_legacy_pi_boolean_survives(self):
        shared = self.write(self.home / ".agents/skills/caveman/SKILL.md", "user-owned legacy\n")
        before = self.snapshot()
        self.wire(ok=False)
        self.assertEqual(self.snapshot(), before)
        shared.unlink()
        shared.parent.rmdir()
        settings = self.write(self.home / ".pi/agent/settings.json", json.dumps({
            "skills": {"customDirectories": ["user-skill"], "enableSkillCommands": False},
        }))
        self.wire()
        updated = json.loads(settings.read_text())
        self.assertEqual(updated["enableSkillCommands"], False)
        self.assertIsInstance(updated["skills"], list)
        self.assertIn("user-skill", updated["skills"])
        settings.write_text('{"skills":{"customDirectories":[],"enableSkillCommands":"bad"}}')
        malformed_before = self.snapshot()
        self.wire(ok=False)
        self.assertEqual(settings.read_text(), '{"skills":{"customDirectories":[],"enableSkillCommands":"bad"}}')
        self.assertEqual(malformed_before, self.snapshot())

    def test_legacy_hooks_and_skills_require_manual_migration(self):
        paths = [
            (".claude/settings.json", '{"hooks":{"SessionStart":[{"hooks":[{"command":"custom && taskflow-session.js"}]}]}}'),
            (".agents/skills/task-flow/SKILL.md", "custom legacy skill"),
            (".pi/agent/AGENTS.md", "custom .todos rules"),
            (".codex/config.toml", '[mcp_servers\n'),
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

    def test_all_harnesses_share_policy_and_pi_uses_native_headroom(self):
        self.wire()
        for path in (
            self.home / ".claude/CLAUDE.md",
            self.home / ".codex/AGENTS.md",
            self.home / ".pi/agent/AGENTS.md",
            self.home / ".omp/agent/RULES.md",
        ):
            self.assertIn("Headroom", path.read_text())
            self.assertNotIn("GPT-only", path.read_text())
        for name in ("index.ts", "bridge.py", "assets.py", "persistence.py"):
            self.assertTrue((self.home / ".pi/agent/extensions/megai-headroom" / name).is_file())
        settings = json.loads((self.home / ".pi/agent/settings.json").read_text())
        self.assertTrue(any(value.startswith("!") and ".agents/skills/**" in value for value in settings["skills"]))
        env = dict(self.env, OMP_PROFILE="work")
        self.run_cmd(sys.executable, str(self.megai / "lib/slim_wiring.py"), "omp", env=env)
        self.assertIn("Headroom", (self.home / ".omp/profiles/work/agent/RULES.md").read_text())

    def test_launch_verifies_only_selected_client_and_forwards_omp_profile(self):
        self.wire()
        self.write(self.home / ".claude/settings.json", "{bad JSON")
        self.write(self.home / ".codex/config.toml", "broken = [\n")
        self.run_cmd("bash", str(self.megai / "bin/megai"), "pi", "--version")
        self.write(self.home / ".claude/settings.json", "{}\n")
        self.run_cmd("bash", str(self.megai / "bin/megai"), "cc", "--version")
        self.run_cmd(sys.executable, str(self.megai / "lib/slim_wiring.py"), "omp", env=dict(self.env, OMP_PROFILE="work"))
        self.run_cmd("bash", str(self.megai / "bin/megai"), "omp", "--profile", "work", "--version")
        self.assertIn("--profile work --version", (self.home / "calls").read_text())

    def test_startup_all_harnesses_and_profile_do_not_prewarm(self):
        self.wire()
        before = self.snapshot()
        for client in ("cc", "codex", "pi", "omp"):
            self.run_cmd("bash", str(self.megai / "bin/megai"), client, "--version")
        self.run_cmd("bash", str(self.megai / "bin/megai"))
        calls = (self.home / "calls").read_text()
        for name in ("zg", "npm", "npx", "curl", "node"):
            self.assertNotIn(str(self.bin / name), calls)
        self.assertEqual(calls.count("branch-check"), 5)
        after = self.snapshot()
        after.pop("home/calls")
        self.assertEqual(before, after)
        env = dict(self.env, OMP_PROFILE="work")
        self.run_cmd(sys.executable, str(self.megai / "lib/slim_wiring.py"), "omp", env=env)
        self.run_cmd("bash", str(self.megai / "bin/megai"), "omp", "--profile", "work", "--version")
        self.assertIn("--profile work --version", (self.home / "calls").read_text())

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

    def retired_artifacts(self):
        argent = self.write(self.home / ".agents/skills/argent/SKILL.md", "---\nmanaged-by: megai\n---\nlegacy\n")
        links = []
        for root, name in ((self.home / ".agents/skills", "numasec-security"),
                           (self.home / ".pi/agent/skills", "megai-openspec")):
            root.mkdir(parents=True, exist_ok=True)
            link = root / name
            link.symlink_to(self.megai / "skills" / name)
            links.append(link)
        return [argent, *links]

    def test_pipeline_install_update_exact_stack_and_failure(self):
        self.wire()
        self.write(self.megai / "ux-ui-agent-skills/package.json", '{}')
        (self.megai / "mattpocock-skills/skills").mkdir(parents=True)
        selected = ("headroom", "tgrep", "zvec_grep", "codedb", "ruff", "ux_ui_agent_skills", "mattpocock_skills", "taskflow", "worktree_lifecycle", "pi_packages")
        for path in (self.megai / "lib").glob("install_*.sh"):
            name = path.stem.removeprefix("install_")
            self.write(path, f'#!/bin/sh\necho install:{name} >>"$HOME/install-calls"\n')
        for client in ("cc", "codex", "pi", "omp", "path"):
            self.write(self.megai / f"lib/wire_{client}.sh", '#!/bin/sh\nexit 0\n')
        self.write(self.megai / "lib/detect.sh", 'detect_os() { MEGAI_OS=test; MEGAI_ARCH=test; }\ndetect_runtimes() { MEGAI_HAS_CURL=1; MEGAI_HAS_PY=1; MEGAI_HAS_NODE=1; MEGAI_HAS_JQ=1; }\nrequire_or_install_jq() { :; }\nrequire_or_install_node() { :; }\nrequire_or_install_pipx() { :; }\n')
        for command in ("install", "update", "install"):
            retired = self.retired_artifacts()
            self.run_cmd("bash", str(self.megai / "bin/megai"), command)
            self.assertTrue(all(not p.exists() and not p.is_symlink() for p in retired))
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
# A concurrent edit after one publication must also survive rollback.
first.write_bytes(b'original')
p=w.Plan();p.stage(first,b'new',b'original');p.stage(second,b'new',None)
real=w.atomic_write; count=0
def injected_after_publish(path,data):
 global count
 count+=1
 if count==2:
  first.write_bytes(b'concurrent after publish')
  raise OSError('injected late write failure')
 real(path,data)
w.atomic_write=injected_after_publish
try:p.apply(False)
except OSError:pass
else:raise AssertionError('late write failure swallowed')
assert first.read_bytes()==b'concurrent after publish'
'''
        self.run_cmd(sys.executable, "-c", code)

    def test_headroom_cli_is_shared_and_no_legacy_daemon_startup(self):
        self.wire()
        self.assertTrue((self.megai / "bin/megai-headroom").is_file())
        self.run_cmd("bash", str(self.megai / "bin/megai"), "start", ok=False)
        self.assertFalse((self.home / "calls").exists())

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
        self.write(source / "lib/install_caveman.sh", "#!/bin/sh\necho caveman-helper\n")
        self.write(self.megai / "bin/user-tool", "retain")
        foreign = self.write(self.megai / "lib/user-script.sh", "retain")
        foreign.chmod(0o600)
        retired = self.megai / "lib/install_graphify.sh"
        retired_bytes = (ROOT / "tests/fixtures/retired-source/install_graphify.sh").read_bytes()
        retired.write_bytes(retired_bytes)
        previous = (self.megai / "bin/megai").read_bytes()
        receipt = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in (self.megai / "lib/install_agent_memory.sh",
                                self.megai / "lib/install_rtk.sh",
                                self.megai / "lib/install_caveman.sh",
                                self.megai / "pi-skill/extensions/memory.sh") if path.exists()}
        (self.megai / "slim-wiring.json").write_text(json.dumps(receipt))
        self.run_cmd(sys.executable, str(self.megai / "lib/install_slim_source.py"), str(source))
        self.assertEqual((self.megai / "bin/user-tool").read_text(), "retain")
        self.assertEqual(foreign.stat().st_mode & 0o777, 0o600)
        self.assertFalse(retired.exists())
        self.assertFalse((self.megai / "lib/install_caveman.sh").exists())
        manifests = list((self.megai / "backups").glob("slim-wiring-*/manifest.json"))
        manifest = json.loads(manifests[0].read_text())
        self.assertEqual((manifests[0].parent / manifest[str(self.megai / "bin/megai")]).read_bytes(), previous)
        self.assertEqual((manifests[0].parent / manifest[str(retired)]).read_bytes(), retired_bytes)

    def test_custom_retired_source_blocks_before_changes(self):
        custom = self.write(self.megai / "lib/install_graphify.sh", "custom user code\n")
        before = self.snapshot()
        self.run_cmd(sys.executable, str(self.megai / "lib/install_slim_source.py"), str(ROOT), ok=False)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(custom.read_text(), "custom user code\n")

    def test_retirement_metadata_preflight_is_aggregate(self):
        self.wire()
        self.retired_artifacts()
        state_path = self.megai / "state.json"
        state = json.loads(state_path.read_text())
        for invalid in ("not-an-array", {}, [5], ["relative/path"]):
            state["tools"]["openspec"] = {"destinations": invalid}
            state_path.write_text(json.dumps(state))
            before = self.snapshot()
            self.run_cmd("bash", str(self.megai / "bin/megai"), "uninstall", ok=False, input_text="y\n")
            self.assertEqual(before, self.snapshot())
            self.run_cmd(sys.executable, str(self.megai / "lib/install_slim_source.py"), str(ROOT), ok=False)
            self.assertEqual(before, self.snapshot())

    def test_uninstall_retires_owned_legacy_artifacts(self):
        self.wire()
        retired = self.retired_artifacts()
        self.write(self.megai / "lib/plane_mcp.sh", "#!/bin/sh\nexit 0\n")
        self.run_cmd("bash", str(self.megai / "bin/megai"), "uninstall", input_text="y\n")
        self.assertTrue(all(not p.exists() and not p.is_symlink() for p in retired))
        self.assertTrue((self.legacy / "sentinel").exists())

    def test_uninstall_conflicts_preflight_before_plane_mutation(self):
        self.wire()
        self.write(self.megai / "lib/plane_mcp.sh", '#!/bin/sh\necho mutated >"$HOME/plane-mutated"\n')
        skill = self.home / ".agents/skills/megai/SKILL.md"
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
        for name in ("bash", "env", "jq", "git", "rg", "find", "grep"):
            if not (self.bin / name).exists():
                (self.bin / name).symlink_to(shutil.which(name))
        env = dict(self.env, PATH=str(self.bin))
        ui = self.write(self.megai / "ux-ui-agent-skills/package.json", '{}')
        self.write(self.megai / "ux-ui-agent-skills/.megai-skills/a11y-audit/SKILL.md", 'fixture')
        matt = self.write(self.megai / "mattpocock-skills/skills/example/SKILL.md", 'fixture')
        runtime = self.write(self.megai / "venv/headroom/bin/python",
                             '#!/bin/sh\necho checked >>"$HOME/headroom-probes"\nexit 0\n')
        runtime.chmod(0o700)
        self.run_cmd("bash", str(self.megai / "bin/megai"), "doctor", env=env)
        self.assertEqual((self.home / "headroom-probes").read_text(), "checked\n")
        for pi_present in (True, False):
            pi = self.bin / "pi"
            hidden_pi = self.bin / "pi-hidden"
            if not pi_present:
                pi.rename(hidden_pi)
            try:
                runtime.write_text("#!/bin/sh\nexit 17\n")
                failure = self.run_cmd("bash", str(self.megai / "bin/megai"), "doctor", ok=False, env=env)
                self.assertIn("Headroom runtime verification failed", failure.stdout + failure.stderr)
                runtime.unlink()
                self.run_cmd("bash", str(self.megai / "bin/megai"), "doctor", ok=False, env=env)
                runtime.write_text("#!/bin/sh\nexit 0\n")
                runtime.chmod(0o700)
            finally:
                if not pi_present:
                    hidden_pi.rename(pi)
        for path in (self.bin / "codedb", ui, matt):
            hidden = path.with_name(path.name + ".hidden")
            path.rename(hidden)
            self.run_cmd("bash", str(self.megai / "bin/megai"), "doctor", ok=False, env=env)
            hidden.rename(path)

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
        self.assertIn('MEGAI_REF="${MEGAI_REF:-main}"', (ROOT / "install.sh").read_text())
        self.assertNotIn('MEGAI_REF="${MEGAI_REF:-slim}"', (ROOT / "install.sh").read_text())
        for flag in ("--no-fix", "--no-fix-only", "--no-cache", "ruff format --check"):
            self.assertIn(flag, (ROOT / "pi-skill/SKILL.md").read_text())


if __name__ == "__main__":
    unittest.main()

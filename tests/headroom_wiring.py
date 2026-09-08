#!/usr/bin/env python3
"""Offline Headroom retirement and wiring acceptance in disposable HOME roots."""
import hashlib
import json
import shutil
import sys
import unittest
import slim_distribution as fixtures


class HeadroomWiring(unittest.TestCase):
    setUp = fixtures.Slim.setUp
    write = fixtures.Slim.write
    stub = fixtures.Slim.stub
    run_cmd = fixtures.Slim.run_cmd
    snapshot = fixtures.Slim.snapshot
    wire = fixtures.Slim.wire

    def test_receipted_retirement_is_archived_not_reloaded(self):
        self.wire()
        retired = {
            self.home / ".pi/agent/skills/caveman/SKILL.md": "old bundled style",
            self.home / ".pi/agent/skills/caveman/LICENSE.md": "old license",
            self.megai / "bin/megai-memory": "old bridge",
        }
        receipt_path = self.megai / "slim-wiring.json"
        receipt = json.loads(receipt_path.read_text())
        for path, text in retired.items():
            self.write(path, text)
            receipt[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        receipt_path.write_text(json.dumps(receipt))
        self.wire()
        for path, text in retired.items():
            self.assertFalse(path.exists())
            self.assertNotIn(str(path), json.loads(receipt_path.read_text()))
            originals = []
            for manifest in (self.megai / "backups").glob("slim-wiring-*/manifest.json"):
                name = json.loads(manifest.read_text()).get(str(path))
                if name is not None:
                    originals.append((manifest.parent / name).read_text())
            self.assertIn(text, originals)
        before = self.snapshot()
        self.wire()
        self.assertEqual(before, self.snapshot())

    def test_retired_mcp_metadata_removed_while_history_and_other_cache_survive(self):
        cache = self.write(self.home / ".pi/agent/mcp-cache.json", json.dumps({
            "version": 1, "servers": {name: {"tools": [name]} for name in
                                      ("rtk", "caveman", "agent-memory", "agentmemory", "plane")}}))
        history = self.write(self.home / ".pi/agent/sessions/history.jsonl", "rtk caveman agent-memory history")
        memory = self.write(self.home / ".agentmemory/data/original", "original data")
        self.wire()
        self.assertEqual(json.loads(cache.read_text())["servers"], {"plane": {"tools": ["plane"]}})
        self.assertEqual(history.read_text(), "rtk caveman agent-memory history")
        self.assertEqual(memory.read_text(), "original data")
        state = json.loads((self.megai / "state.json").read_text())
        self.assertNotIn("agent-memory", state["ports"])
        self.assertEqual(state["keep"], {"value": 42})

    def test_retired_daemon_commands_do_not_kill_or_delete(self):
        self.write(self.megai / "memory-process.json", '{"pid":123,"keep":true}')
        self.write(self.home / ".agentmemory/data/original", "original data")
        before = self.snapshot()
        for command in ("start", "stop", "logs"):
            self.run_cmd("bash", str(self.megai / "bin/megai"), command, ok=False)
        self.assertEqual(before, self.snapshot())

    def test_unowned_retired_mcp_requires_explicit_reconciliation(self):
        self.write(self.home / ".pi/agent/mcp.json", '{"mcpServers":{"agentmemory":{"command":"custom"}}}')
        before = self.snapshot()
        self.wire(ok=False)
        self.assertEqual(before, self.snapshot())

    def test_cache_symlink_and_malformed_shapes_fail_before_writes(self):
        cache = self.home / ".pi/agent/mcp-cache.json"
        for value in ('{"servers":[]}', '[]', '{bad'):
            self.write(cache, value)
            before = self.snapshot()
            self.wire(ok=False)
            self.assertEqual(before, self.snapshot())
        cache.unlink()
        original = self.write(self.root / "external-cache", '{}')
        cache.symlink_to(original)
        before = self.snapshot()
        self.wire(ok=False)
        self.assertEqual(before, self.snapshot())

    def test_explicit_retired_resources_and_custom_skill_files_block_cutover(self):
        settings = self.home / ".pi/agent/settings.json"
        for group, entry in (("skills", "/shared/caveman/SKILL.md"),
                             ("extensions", "/custom/rtk.ts"),
                             ("packages", {"source": "npm:agent-memory"})):
            self.write(settings, json.dumps({group: [entry]}))
            before = self.snapshot()
            self.wire(ok=False)
            self.assertEqual(before, self.snapshot())
        settings.unlink()
        self.write(self.home / ".pi/agent/skills/caveman/custom.md", "user material")
        before = self.snapshot()
        self.wire(ok=False)
        self.assertEqual(before, self.snapshot())

    def test_installer_refuses_an_unowned_runtime_before_pip_or_downloads(self):
        self.stub("uv", 'echo unexpected-install >>"$HOME/calls"\nexit 9\n')
        marker = self.write(self.megai / "venv/headroom/.megai-owned", "custom marker")
        before = self.snapshot()
        before = self.snapshot()
        self.run_cmd("bash", str(self.megai / "lib/install_headroom.sh"), ok=False)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(marker.read_text(), "custom marker")

    def test_cli_launcher_filters_credentials_and_unsafe_python_overrides(self):
        self.wire()
        launcher = self.write(self.megai / "venv/headroom/bin/python", '''#!/bin/sh
[ -z "${OPENAI_API_KEY:-}${PYTHONPATH:-}${HEADROOM_CCR_SQLITE_PATH:-}" ] || exit 41
[ "$1" = -I ] && [ "$2" = -B ] || exit 42
printf '{}'
''')
        launcher.chmod(0o700)
        env = dict(self.env, OPENAI_API_KEY="synthetic-canary", PYTHONPATH="/synthetic",
                   HEADROOM_CCR_SQLITE_PATH="/synthetic/redirect.db")
        result = self.run_cmd("bash", str(self.megai / "bin/megai-headroom"), "doctor", env=env)
        self.assertEqual(result.stdout, "{}")

    def test_legacy_daemon_receipt_blocks_cutover_without_killing(self):
        self.write(self.megai / "memory-process.json", '{"pid":123,"keep":true}')
        before = self.snapshot()
        self.wire(ok=False)
        self.assertEqual(before, self.snapshot())

    def test_transaction_restores_entrypoints_and_wiring_after_each_publication_phase(self):
        source = self.root / "source"
        for folder in ("bin", "lib", "pi-skill", "task-flow", "skills"):
            shutil.copytree(self.megai / folder, source / folder)
        self.write(source / "bin/megai", "#!/bin/sh\necho new-entrypoint\n")
        entrypoint = self.megai / "bin/megai"
        original_mode = entrypoint.stat().st_mode & 0o777
        def tracked():
            return {str(path.relative_to(self.megai)): path.read_bytes()
                    for path in self.megai.rglob("*") if path.is_file()
                    and "backups" not in path.relative_to(self.megai).parts}
        before = tracked()
        for phase in ("prepare", "source", "wiring"):
            self.write(source / "lib/install_headroom.sh", "#!/bin/sh\nexit " + ("42" if phase == "prepare" else "0") + "\n")
            self.write(source / "lib/main.sh", '#!/bin/sh\n' +
                       ('python3 "$MEGAI_HOME/lib/slim_wiring.py" pi\n' if phase == "wiring" else '') + "exit 42\n")
            self.run_cmd(sys.executable, str(source / "lib/install_transaction.py"), str(source), ok=False)
            self.assertEqual(tracked(), before, phase)
            self.assertEqual(entrypoint.stat().st_mode & 0o777, original_mode)
            self.assertFalse((self.home / ".pi/agent/extensions/megai-headroom/index.ts").exists())

    def test_credential_and_model_settings_preserved(self):
        auth = self.write(self.home / ".pi/agent/auth.json", '{"secret":"test-only"}')
        models = self.write(self.home / ".pi/agent/models.json", '{"test":"unchanged"}')
        settings = self.write(self.home / ".pi/agent/settings.json", json.dumps({
            "defaultProvider": "keep-provider", "defaultModel": "keep-model",
            "defaultThinkingLevel": "high", "transport": "websocket", "packages": ["npm:user"],
            "extensions": ["!megai-headroom/**"]}))
        original = json.loads(settings.read_text())
        self.wire()
        actual = json.loads(settings.read_text())
        actual.pop("skills")
        self.assertEqual(actual, original)
        self.assertEqual(auth.read_text(), '{"secret":"test-only"}')
        self.assertEqual(models.read_text(), '{"test":"unchanged"}')


if __name__ == "__main__":
    unittest.main()

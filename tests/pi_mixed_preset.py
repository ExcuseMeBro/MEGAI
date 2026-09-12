#!/usr/bin/env python3
"""Exercise the real optional-preset CLI in disposable homes, without providers."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "planner": {"provider": "openai-codex", "model": "gpt-6-astra", "thinking": "high"},
    "scout": {"provider": "minimax", "model": "MiniMax-M2.7-highspeed", "thinking": "medium"},
    "worker": {"provider": "minimax", "model": "MiniMax-M3", "thinking": "high"},
    "reviewer": {"provider": "openai-codex", "model": "gpt-5.6-sol", "thinking": "high"},
}


class MixedPreset(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="pi-mixed-test-")
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name).resolve()
        self.agent = self.home / ".pi/agent"
        self.agent.mkdir(parents=True)
        self.env = dict(os.environ, HOME=str(self.home), MEGAI_HOME=str(self.home / ".megai"),
                        MEGAI_SOURCE=str(ROOT), PI_CODING_AGENT_DIR=str(self.agent),
                        PYTHONDONTWRITEBYTECODE="1")
        self.env.pop("MEGAI_TRANSACTION_LOG", None)

    def run_cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "lib/pi_model_policy.py"), *args],
                                env=self.env, cwd=self.home, capture_output=True, text=True, timeout=20)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def snapshot(self):
        return {str(p.relative_to(self.home)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.home.rglob("*") if p.is_file() and not p.is_symlink()}

    def test_opt_in_exact_roles_native_settings_preservation_and_idempotence(self):
        original = {
            "defaultProvider": "custom", "defaultModel": "keep", "defaultThinkingLevel": "low",
            "modelThinkingLevels": {"custom/keep": "low", "minimax/MiniMax-M3": "medium"},
            "packages": ["npm:custom"], "extensions": ["!*"], "theme": "custom",
            "enabledModels": ["custom/*"], "transport": "sse", "custom": {"nested": 42},
        }
        (self.agent / "settings.json").write_text(json.dumps(original))
        (self.agent / "auth.json").write_text('{"synthetic":"unchanged"}\n')
        (self.agent / "models.json").write_text('{"providers":{}}\n')
        other = self.home / ".claude/settings.json"
        other.parent.mkdir()
        other.write_text('{"synthetic":"keep"}\n')
        protected = {p: p.read_bytes() for p in (other, self.agent / "auth.json", self.agent / "models.json")}
        before = self.snapshot()
        self.run_cli("--preset", "mixed", "--check")
        self.assertEqual(self.snapshot(), before)
        self.run_cli("--preset", "mixed")
        roles = json.loads((self.agent / "megai-roles.json").read_text())
        self.assertEqual(roles, {"schema": 1, "preset": "mixed", "roles": EXPECTED})
        settings = json.loads((self.agent / "settings.json").read_text())
        wanted = dict(original, defaultProvider="openai-codex", defaultModel="gpt-6-astra",
                      defaultThinkingLevel="high", modelThinkingLevels={
                          **original["modelThinkingLevels"],
                          **{r["provider"] + "/" + r["model"]: r["thinking"] for r in EXPECTED.values()},
                      })
        self.assertEqual(settings, wanted)
        for path, data in protected.items():
            self.assertEqual(path.read_bytes(), data)
        policy = (self.agent / "AGENTS.md").read_text()
        for clause in ("megai-roles.json", "PI_REASONING_LEVEL", "not a sandbox", "--no-cache"):
            self.assertIn(clause, policy)
        after = self.snapshot()
        self.run_cli("--preset", "mixed")
        self.assertEqual(self.snapshot(), after)
        self.assertTrue(any(p.name == "manifest.json" for p in (self.home / ".megai/backups").rglob("*")))

    def test_explicit_reapply_upgrades_owned_xhigh_preset(self):
        legacy = self.home / "legacy-source"
        for relative in ("pi-skill/delegation.md", "pi-skill/provider-guard/index.ts"):
            path = legacy / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / relative).read_bytes())
        old_roles = {name: dict(role) for name, role in EXPECTED.items()}
        old_roles["planner"]["thinking"] = "xhigh"
        config = legacy / "pi-skill/presets/mixed.json"
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"schema": 1, "preset": "mixed", "roles": old_roles}))
        self.env["MEGAI_SOURCE"] = str(legacy)
        self.run_cli("--preset", "mixed")
        self.env["MEGAI_SOURCE"] = str(ROOT)
        before = json.loads((self.agent / "settings.json").read_text())
        self.assertEqual(before["defaultThinkingLevel"], "xhigh")
        self.assertEqual(before["modelThinkingLevels"]["openai-codex/gpt-6-astra"], "xhigh")
        snapshot = self.snapshot()
        self.run_cli("--preset", "mixed", "--check")
        self.assertEqual(self.snapshot(), snapshot)
        self.run_cli("--preset", "mixed")
        after = json.loads((self.agent / "settings.json").read_text())
        before["defaultThinkingLevel"] = "high"
        before["modelThinkingLevels"]["openai-codex/gpt-6-astra"] = "high"
        self.assertEqual(after, before)
        self.assertEqual(json.loads((self.agent / "megai-roles.json").read_text())["roles"], EXPECTED)
        snapshot = self.snapshot()
        self.run_cli("--preset", "mixed")
        self.assertEqual(self.snapshot(), snapshot)

    def test_default_is_model_neutral_and_preserves_selected_preset(self):
        settings = '{"defaultModel":"custom", "defaultThinkingLevel":"low"}\n'
        (self.agent / "settings.json").write_text(settings)
        self.run_cli()
        self.assertEqual((self.agent / "settings.json").read_text(), settings)
        self.assertFalse((self.agent / "megai-roles.json").exists())
        self.run_cli("--preset", "mixed")
        before = self.snapshot()
        self.run_cli()
        self.assertEqual(self.snapshot(), before)

    def test_remove_retires_owned_role_map_but_preserves_native_preferences(self):
        self.run_cli("--preset", "mixed")
        settings = (self.agent / "settings.json").read_bytes()
        self.run_cli("--remove")
        self.assertFalse((self.agent / "megai-roles.json").exists())
        self.assertEqual((self.agent / "settings.json").read_bytes(), settings)

    def test_custom_role_map_conflict_is_preflight_only(self):
        (self.agent / "megai-roles.json").write_text('{"custom":true}\n')
        before = self.snapshot()
        self.run_cli("--preset", "mixed", ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_malformed_settings_refused_without_partial_policy_install(self):
        for value in ("not-json", "[]", '{"modelThinkingLevels":[]}'):
            with self.subTest(value=value):
                (self.agent / "settings.json").write_text(value)
                before = self.snapshot()
                self.run_cli("--preset", "mixed", ok=False)
                self.assertEqual(self.snapshot(), before)

    def test_symlinked_settings_preserved(self):
        target = self.home / "external.json"
        target.write_text('{"keep":true}')
        (self.agent / "settings.json").symlink_to(target)
        before = self.snapshot()
        self.run_cli("--preset", "mixed", ok=False)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue((self.agent / "settings.json").is_symlink())

    def test_removal_preserves_unowned_role_file(self):
        self.run_cli()
        (self.agent / "megai-roles.json").write_text('{"custom":true}')
        before = self.snapshot()
        self.run_cli("--remove", ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_invalid_or_conflicting_options_are_read_only(self):
        before = self.snapshot()
        self.run_cli("--preset", "unknown", ok=False)
        self.run_cli("--preset", "mixed", "--remove", ok=False)
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)

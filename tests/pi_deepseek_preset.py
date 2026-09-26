#!/usr/bin/env python3
"""Exercise the optional economy preset in disposable homes, no providers.

The native profile is separately tested by Pi role-routing regressions; economy
remains an independent explicit profile and `mixed` remains retired.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FLASH = {"provider": "deepseek", "model": "deepseek-flash", "thinking": "high"}
EXECUTOR = {"provider": "deepseek", "model": "deepseek-flash", "thinking": "low"}
EXPECTED = {
    "planner": dict(FLASH),
    "scout": dict(EXECUTOR),
    "worker": dict(EXECUTOR),
    "reviewer": {"provider": "openai-codex", "model": "gpt-6-sol", "thinking": "high"},
}


class Preset(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="pi-preset-test-")
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name).resolve()
        self.agent = self.home / ".pi/agent"
        self.agent.mkdir(parents=True)
        megai = self.home / ".megai"
        self.env = dict(os.environ, HOME=str(self.home), MEGAI_HOME=str(megai),
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

    def legacy_source(self, roles, preset="economy"):
        legacy = self.home / "legacy-source"
        for relative in ("pi-skill/delegation.md", "pi-skill/provider-guard/index.ts",
                         "pi-skill/role-routing/index.ts", "pi-skill/model-fallback/index.ts"):
            path = legacy / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / relative).read_bytes())
        config = legacy / f"pi-skill/presets/{preset}.json"
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"schema": 1, "preset": preset, "roles": roles}))
        return legacy

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
        self.run_cli("--preset", "economy", "--check")
        self.assertEqual(self.snapshot(), before)
        self.run_cli("--preset", "economy")
        roles = json.loads((self.agent / "megai-roles.json").read_text())
        self.assertEqual(roles, {"schema": 1, "preset": "economy", "roles": EXPECTED})
        settings = json.loads((self.agent / "settings.json").read_text())
        native = {}
        for role in EXPECTED.values():
            # The planner is declared first and owns the native startup level of a
            # model that several roles share.
            native.setdefault(role["provider"] + "/" + role["model"], role["thinking"])
        wanted = dict(original, defaultProvider="deepseek", defaultModel="deepseek-flash",
                      defaultThinkingLevel="high", modelThinkingLevels={
                          **original["modelThinkingLevels"], **native,
                      })
        self.assertEqual(settings, wanted)
        for path, data in protected.items():
            self.assertEqual(path.read_bytes(), data)
        policy = (self.agent / "AGENTS.md").read_text()
        self.assertIn("megai/delegation.md", policy)
        delegation = (self.agent / "skills/megai/delegation.md").read_text()
        for clause in ("megai-roles.json", "PI_REASONING_LEVEL", "not a sandbox", "--no-cache"):
            self.assertIn(clause, delegation)
        after = self.snapshot()
        self.run_cli("--preset", "economy")
        self.assertEqual(self.snapshot(), after)
        self.assertTrue(any(p.name == "manifest.json" for p in (self.home / ".megai/backups").rglob("*")))

    def test_preset_is_exact_deepseek_roles_and_role_levels(self):
        config = json.loads((ROOT / "pi-skill/presets/economy.json").read_text())
        self.assertEqual(config, {"schema": 1, "preset": "economy", "roles": EXPECTED})
        for role in config["roles"].values():
            identity = role["provider"] + "/" + role["model"]
            self.assertNotIn("minimax", identity.lower())
        # One cheap model plans with judgment and executes cheaply: a shared model
        # keeps a per-role level in megai-roles.json, and the planner's level is the
        # unambiguous native startup level in settings.json.
        self.assertEqual(config["roles"]["planner"], FLASH)
        self.assertEqual(config["roles"]["scout"], EXECUTOR)
        self.assertEqual(config["roles"]["worker"], EXECUTOR)

    def test_retired_mixed_preset_is_refused_and_absent(self):
        self.assertFalse((ROOT / "pi-skill/presets/mixed.json").exists())
        before = self.snapshot()
        self.run_cli("--preset", "mixed", ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_explicit_reapply_upgrades_owned_xhigh_preset(self):
        legacy = self.legacy_source({name: dict(role) for name, role in EXPECTED.items()})
        config = legacy / "pi-skill/presets/economy.json"
        roles = json.loads(config.read_text())["roles"]
        # planner, scout and worker share one model, so one startup level is required.
        for name in ("planner", "scout", "worker"):
            roles[name]["thinking"] = "xhigh"
        config.write_text(json.dumps({"schema": 1, "preset": "economy", "roles": roles}))
        self.env["MEGAI_SOURCE"] = str(legacy)
        self.run_cli("--preset", "economy")
        self.env["MEGAI_SOURCE"] = str(ROOT)
        before = json.loads((self.agent / "settings.json").read_text())
        self.assertEqual(before["defaultThinkingLevel"], "xhigh")
        self.assertEqual(before["modelThinkingLevels"]["deepseek/deepseek-flash"], "xhigh")
        snapshot = self.snapshot()
        self.run_cli("--preset", "economy", "--check")
        self.assertEqual(self.snapshot(), snapshot)
        self.run_cli("--preset", "economy")
        after = json.loads((self.agent / "settings.json").read_text())
        before["defaultThinkingLevel"] = "high"
        before["modelThinkingLevels"]["deepseek/deepseek-flash"] = "high"
        self.assertEqual(after, before)
        self.assertEqual(json.loads((self.agent / "megai-roles.json").read_text())["roles"], EXPECTED)
        snapshot = self.snapshot()
        self.run_cli("--preset", "economy")
        self.assertEqual(self.snapshot(), snapshot)

    def test_explicit_owned_upgrade_from_minimax(self):
        old_roles = {name: dict(role) for name, role in EXPECTED.items()}
        old_roles["planner"] = {
            "provider": "minimax", "model": "MiniMax-M3", "thinking": "high",
        }
        old_roles["scout"] = {
            "provider": "minimax", "model": "MiniMax-M2.7-highspeed", "thinking": "medium",
        }
        old_roles["worker"] = {
            "provider": "minimax", "model": "MiniMax-M3", "thinking": "high",
        }
        legacy = self.legacy_source(old_roles)
        original = {"custom": {"keep": True}, "modelThinkingLevels": {"custom/model": "low"}}
        (self.agent / "settings.json").write_text(json.dumps(original))
        protected = (self.agent / "auth.json", self.agent / "models.json")
        for path in protected:
            path.write_text('{"synthetic":"unchanged"}\n')
        self.env["MEGAI_SOURCE"] = str(legacy)
        self.run_cli("--preset", "economy")
        role_path = self.agent / "megai-roles.json"
        old_bytes = role_path.read_bytes()
        old_settings = (self.agent / "settings.json").read_bytes()
        self.assertEqual(json.loads(old_bytes)["roles"], old_roles)

        # Ordinary policy installation preserves the owned selection.
        self.env["MEGAI_SOURCE"] = str(ROOT)
        self.run_cli()
        self.assertEqual(role_path.read_bytes(), old_bytes)
        self.assertEqual((self.agent / "settings.json").read_bytes(), old_settings)
        before = self.snapshot()
        self.run_cli("--preset", "economy", "--check")
        self.assertEqual(self.snapshot(), before)
        self.run_cli("--preset", "economy")
        self.assertEqual(json.loads(role_path.read_text()), {
            "schema": 1, "preset": "economy", "roles": EXPECTED,
        })
        selected = json.loads((self.agent / "settings.json").read_text())
        self.assertEqual(selected["defaultProvider"], "deepseek")
        self.assertEqual(selected["defaultModel"], "deepseek-flash")
        self.assertEqual(selected["defaultThinkingLevel"], "high")
        self.assertEqual(selected["modelThinkingLevels"]["deepseek/deepseek-flash"], "high")
        self.assertEqual(selected["modelThinkingLevels"]["custom/model"], "low")
        self.assertEqual(selected["modelThinkingLevels"]["minimax/MiniMax-M3"], "high")
        self.assertEqual(selected["custom"], original["custom"])
        for path in protected:
            self.assertEqual(path.read_text(), '{"synthetic":"unchanged"}\n')
        self.assertTrue(any(p.is_file() and p.read_bytes() == old_bytes
                            for p in (self.home / ".megai/backups").rglob("*")))
        before = self.snapshot()
        self.run_cli("--preset", "economy")
        self.run_cli()
        self.assertEqual(self.snapshot(), before)

    def test_active_pi_guidance_uses_deepseek_not_retired_routing(self):
        for relative in ("pi-skill/ADAPTIVE.md", "pi-skill/delegation.md",
                         "pi-skill/presets/README.md", "docs/pi-adaptive.md", "README.md"):
            with self.subTest(path=relative):
                text = (ROOT / relative).read_text().lower()
                self.assertNotIn("minimax", text)
                self.assertIn("deepseek", text)
        # Historical records and non-Pi routing are deliberately not rewritten.
        for relative in ("docs/audits/pi-fast-workflow.md", "docs/audits/pi-task-sample.json",
                         "omp-config/balanced-minimax.yml"):
            with self.subTest(path=relative):
                self.assertIn("minimax", (ROOT / relative).read_text().lower())

    def test_default_is_model_neutral_and_preserves_selected_preset(self):
        settings = '{"defaultModel":"custom", "defaultThinkingLevel":"low"}\n'
        (self.agent / "settings.json").write_text(settings)
        self.run_cli()
        self.assertEqual((self.agent / "settings.json").read_text(), settings)
        self.assertFalse((self.agent / "megai-roles.json").exists())
        self.run_cli("--preset", "economy")
        before = self.snapshot()
        self.run_cli()
        self.assertEqual(self.snapshot(), before)

    def test_remove_retires_owned_role_map_but_preserves_native_preferences(self):
        self.run_cli("--preset", "economy")
        settings = (self.agent / "settings.json").read_bytes()
        self.run_cli("--remove")
        self.assertFalse((self.agent / "megai-roles.json").exists())
        self.assertEqual((self.agent / "settings.json").read_bytes(), settings)

    def test_custom_role_map_conflict_is_preflight_only(self):
        (self.agent / "megai-roles.json").write_text('{"custom":true}\n')
        before = self.snapshot()
        self.run_cli("--preset", "economy", ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_malformed_settings_refused_without_partial_policy_install(self):
        for value in ("not-json", "[]", '{"modelThinkingLevels":[]}'):
            with self.subTest(value=value):
                (self.agent / "settings.json").write_text(value)
                before = self.snapshot()
                self.run_cli("--preset", "economy", ok=False)
                self.assertEqual(self.snapshot(), before)

    def test_symlinked_settings_preserved(self):
        target = self.home / "external.json"
        target.write_text('{"keep":true}')
        (self.agent / "settings.json").symlink_to(target)
        before = self.snapshot()
        self.run_cli("--preset", "economy", ok=False)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue((self.agent / "settings.json").is_symlink())

    def test_removal_preserves_unowned_role_file(self):
        self.run_cli()
        (self.agent / "megai-roles.json").write_text('{"custom":true}')
        before = self.snapshot()
        self.run_cli("--remove", ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_unsupported_thinking_level_is_refused_before_any_write(self):
        # The whitelist validates the level name only. A name no model maps to a real
        # level is still refused, because nothing downstream can tell it from a typo.
        roles = {name: dict(role) for name, role in EXPECTED.items()}
        roles["scout"]["thinking"] = "turbo"
        self.env["MEGAI_SOURCE"] = str(self.legacy_source(roles))
        before = self.snapshot()
        self.run_cli("--preset", "economy", ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_invalid_or_conflicting_options_are_read_only(self):
        before = self.snapshot()
        self.run_cli("--preset", "unknown", ok=False)
        self.run_cli("--preset", "economy", "--remove", ok=False)
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)

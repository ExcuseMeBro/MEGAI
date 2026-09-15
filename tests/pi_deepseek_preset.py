#!/usr/bin/env python3
"""Offline DeepSeek presets and explicit receipt-owned legacy upgrades."""
import json
import unittest

from pi_mixed_preset import EXPECTED, ROOT, MixedPreset

FLASH = {"provider": "deepseek", "model": "deepseek-flash", "thinking": "high"}


class DeepSeekPreset(MixedPreset):
    def expected_roles(self, preset):
        roles = {name: dict(role) for name, role in EXPECTED.items()}
        if preset == "economy":
            roles["planner"] = dict(FLASH)
        return roles

    def test_both_presets_have_exact_deepseek_roles_and_consistent_levels(self):
        for preset in ("mixed", "economy"):
            with self.subTest(preset=preset):
                config = json.loads((ROOT / f"pi-skill/presets/{preset}.json").read_text())
                self.assertEqual(config, {
                    "schema": 1, "preset": preset, "roles": self.expected_roles(preset),
                })
                levels = {}
                for role in config["roles"].values():
                    identity = role["provider"] + "/" + role["model"]
                    self.assertNotIn("minimax", identity.lower())
                    self.assertEqual(levels.setdefault(identity, role["thinking"]), role["thinking"])
                self.assertEqual(levels["deepseek/deepseek-flash"], "high")
                self.assertEqual(config["roles"]["scout"], FLASH)
                self.assertEqual(config["roles"]["worker"], FLASH)
                self.assertEqual(config["roles"]["reviewer"], {
                    "provider": "openai-codex", "model": "gpt-5.6-sol", "thinking": "high",
                })
                if preset == "mixed":
                    self.assertEqual(config["roles"]["planner"], {
                        "provider": "openai-codex", "model": "gpt-6-astra", "thinking": "high",
                    })

    def upgrade_legacy(self, preset):
        legacy = self.home / "legacy-source"
        for relative in ("pi-skill/delegation.md", "pi-skill/provider-guard/index.ts",
                         "pi-skill/role-routing/index.ts"):
            path = legacy / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / relative).read_bytes())
        old_roles = self.expected_roles(preset)
        old_roles["scout"] = {
            "provider": "minimax", "model": "MiniMax-M2.7-highspeed", "thinking": "medium",
        }
        old_roles["worker"] = {
            "provider": "minimax", "model": "MiniMax-M3", "thinking": "high",
        }
        if preset == "economy":
            old_roles["planner"] = dict(old_roles["worker"])
        config = legacy / f"pi-skill/presets/{preset}.json"
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"schema": 1, "preset": preset, "roles": old_roles}))
        original = {"custom": {"keep": True}, "modelThinkingLevels": {"custom/model": "low"}}
        (self.agent / "settings.json").write_text(json.dumps(original))
        protected = (self.agent / "auth.json", self.agent / "models.json")
        for path in protected:
            path.write_text('{"synthetic":"unchanged"}\n')
        self.env["MEGAI_SOURCE"] = str(legacy)
        self.run_cli("--preset", preset)
        role_path = self.agent / "megai-roles.json"
        old_bytes = role_path.read_bytes()
        old_settings = (self.agent / "settings.json").read_bytes()
        self.assertEqual(json.loads(old_bytes)["roles"], old_roles)

        self.env["MEGAI_SOURCE"] = str(ROOT)
        self.run_cli()
        self.assertEqual(role_path.read_bytes(), old_bytes)
        self.assertEqual((self.agent / "settings.json").read_bytes(), old_settings)
        before = self.snapshot()
        self.run_cli("--preset", preset, "--check")
        self.assertEqual(self.snapshot(), before)
        self.run_cli("--preset", preset)
        expected = self.expected_roles(preset)
        self.assertEqual(json.loads(role_path.read_text()), {
            "schema": 1, "preset": preset, "roles": expected,
        })
        selected = json.loads((self.agent / "settings.json").read_text())
        planner = expected["planner"]
        self.assertEqual(selected["defaultProvider"], planner["provider"])
        self.assertEqual(selected["defaultModel"], planner["model"])
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
        self.run_cli("--preset", preset)
        self.run_cli()
        self.assertEqual(self.snapshot(), before)

    def test_explicit_owned_mixed_upgrade_from_minimax(self):
        self.upgrade_legacy("mixed")

    def test_explicit_owned_economy_upgrade_from_minimax(self):
        self.upgrade_legacy("economy")

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


def load_tests(loader, tests, pattern):
    # Reuse disposable-home helpers, not the inherited mixed suite twice.
    return unittest.TestSuite(DeepSeekPreset(name) for name in DeepSeekPreset.__dict__
                              if name.startswith("test_"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

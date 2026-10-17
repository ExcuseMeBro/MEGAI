"""Check saved model preferences and absence of retired role routing."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "pi-defaults" / "local-profile"


class ReviewedProfileTests(unittest.TestCase):
    def test_role_snapshot_is_retired(self):
        self.assertFalse((PROFILE / "megai-roles.json").exists())
        self.assertFalse((ROOT / "pi-skill/role-routing/index.ts").exists())

    def test_startup_and_provider_fallback_are_preserved(self):
        settings = json.loads((PROFILE / "settings.json").read_text())
        self.assertEqual(settings["defaultProvider"], "openai-codex")
        self.assertEqual(settings["defaultModel"], "gpt-6.1-sol")
        self.assertEqual(settings["defaultThinkingLevel"], "medium")
        fallback = json.loads((PROFILE / "model-fallback.json").read_text())
        self.assertEqual(fallback["fallbacks"]["deepseek/deepseek-flash"],
                         "openai-codex/gpt-5.6-luna")


if __name__ == "__main__":
    unittest.main()

"""Check the saved reviewed-hybrid profile without touching live Pi state."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "pi-defaults" / "local-profile"


class ReviewedProfileTests(unittest.TestCase):
    def test_role_snapshot_matches_reviewed_recommendation(self):
        roles = json.loads((PROFILE / "megai-roles.json").read_text())
        recommended = json.loads(
            (ROOT / "benchmark/pi-routing/recommended-roles.json").read_text()
        )
        self.assertEqual(roles, recommended)

    def test_startup_and_fallback_thinking_match_roles(self):
        roles = json.loads((PROFILE / "megai-roles.json").read_text())
        settings = json.loads((PROFILE / "settings.json").read_text())
        planner = roles["roles"]["planner"]
        self.assertEqual(settings["defaultProvider"], planner["provider"])
        self.assertEqual(settings["defaultModel"], planner["model"])
        self.assertEqual(settings["defaultThinkingLevel"], planner["thinking"])
        for role in [*roles["roles"].values(), roles["fallback"]]:
            identity = f'{role["provider"]}/{role["model"]}'
            self.assertEqual(settings["modelThinkingLevels"][identity], role["thinking"])
        fallback = json.loads((PROFILE / "model-fallback.json").read_text())
        self.assertEqual(
            fallback["fallbacks"]["deepseek/deepseek-flash"],
            f'{roles["fallback"]["provider"]}/{roles["fallback"]["model"]}',
        )


if __name__ == "__main__":
    unittest.main()

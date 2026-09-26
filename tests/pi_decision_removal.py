#!/usr/bin/env python3
"""Keep the local Pi profile free of the retired inference companion."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
NAME = "la" + "ya"


class Removal(unittest.TestCase):
    def test_no_installable_sources_or_provisioning(self):
        for relative in (f"lib/{NAME}_runtime.py", f"pi-skill/{NAME}",
                         f"openspec/changes/local-{NAME}-pi-harness",
                         f"docs/history/specifications/changes/local-{NAME}-pi-harness"):
            self.assertFalse((ROOT / relative).exists(), relative)
        for relative in ("lib/main.sh", "pi-defaults/install.py", "lib/pi_model_policy.py",
                         "pi-skill/ADAPTIVE.md", "pi-defaults/AGENTS.md",
                         "pi-defaults/skills/pi-workflow/context-economy.md", "README.md"):
            with self.subTest(relative=relative):
                self.assertNotIn(NAME, (ROOT / relative).read_text().lower())
        for relative in (f"tests/pi-{NAME}.mjs", f"tests/pi-{NAME}-compaction.mjs",
                         f"tests/pi-{NAME}-live.mjs", f"tests/pi_{NAME}_bridge.py",
                         "tests/pi-context-economy-live.mjs"):
            self.assertFalse((ROOT / relative).exists(), relative)


if __name__ == "__main__":
    unittest.main()

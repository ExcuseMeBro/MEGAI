#!/usr/bin/env python3
"""The Pi distribution must not bundle the retired experimental harness pack."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DistributionScope(unittest.TestCase):
    def test_experimental_pack_and_active_readme_pointer_are_absent(self):
        for name in ("capy", ".capy"):
            self.assertFalse((ROOT / name).exists(), f"unwanted distribution directory: {name}")
        self.assertNotIn("capy", (ROOT / "README.md").read_text().lower())

    def test_supported_runtime_sources_remain(self):
        for relative in ("bin/megai", "lib/integration_queue.py", "lib/slim_wiring.py",
                         "pi-skill/SKILL.md", "omp-skill/SKILL.md"):
            self.assertTrue((ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main(verbosity=2)

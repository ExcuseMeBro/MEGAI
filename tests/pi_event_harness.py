"""Repository-owned Pi handoff policy regressions; the live Paseo event is checked separately."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EventHandoff(unittest.TestCase):
    def test_paseo_pi_completion_uses_notifications_not_wait_deadlines(self):
        guide = (ROOT / "pi-skill/delegation.md").read_text()
        section = guide.split("## Notification-driven waiting (Pi + Paseo)", 1)[1].split("## Model choice", 1)[0]
        self.assertGreaterEqual(section.count("notifyOnFinish: true"), 2)
        self.assertIn("background: true", section)
        self.assertIn("permission-needed", section)
        self.assertIn("current dispatch", section)
        self.assertIn("yield", section)
        self.assertIn("paseo agent wait <id>", section)
        self.assertTrue("--timeout" not in section and "bounded wait" not in section,
                        "child-completion waiting must not impose a deadline")

    def test_provider_stall_protection_is_not_child_wait_deadline(self):
        guide = (ROOT / "pi-skill/delegation.md").read_text()
        self.assertIn("## Parent-side provider timeout, stall and replacement", guide)
        self.assertTrue("provider request" in guide.lower(),
                        "provider request limits must be distinguished from child completion")
        policy = (ROOT / "pi-defaults/AGENTS.md").read_text()
        self.assertIn("notifyOnFinish: true", policy)
        self.assertIn("Provider timeouts", policy)
        self.assertIn("Do not weaken these gates", policy)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Offline acceptance for bin/jev-browser and its profile wiring.

No network, no browser and no paid call: only the credential resolution, the pinned
commit and the installer/skill wiring are exercised.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "bin/jev-browser"
SKILL = ROOT / "pi-skill/jev-browser/SKILL.md"
INSTALLER = ROOT / "lib/install_jev_browser.sh"
PIN = re.compile(r'^PIN_SHA="([0-9a-f]{40})"', re.M)
SECRET = re.compile(r"test-typesafe-key|test-text-key")


def self_check(env: dict[str, str] | None = None, *extra: str):
    environ = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    environ.update(env or {})
    return subprocess.run(
        [str(RUNNER), "--self-check", *extra],
        capture_output=True,
        text=True,
        env=environ,
        timeout=60,
    )


class JevBrowser(unittest.TestCase):
    def test_runner_pins_a_commit(self) -> None:
        text = RUNNER.read_text()
        match = PIN.search(text)
        self.assertIsNotNone(match, "the runner must pin a full commit sha")
        self.assertIn("https://github.com/browser-use/jev-ultrafast", text)
        self.assertNotIn("main", match.group(1), "the pin is a commit, never a branch")
        self.assertTrue(RUNNER.stat().st_mode & 0o111, "the runner must be executable")

    def test_self_check_refuses_without_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            result = self_check({"HOME": home})
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        output = result.stdout + result.stderr
        self.assertIn("typesafe.ai", output)
        self.assertIn("auth.json", output)

    def test_self_check_is_ready_and_prints_no_key(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            result = self_check(
                {
                    "HOME": home,
                    "TYPESAFE_API_KEY": "test-typesafe-key",
                    "TEXT_MODEL_API_KEY": "test-text-key",
                }
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["typesafe_key"], "environment")
        self.assertEqual(payload["text_model_key"], "environment")
        self.assertEqual(payload["prewarm"], "skipped")
        self.assertEqual(payload["model"], "jev-latest")
        self.assertIn("1231850a0bf1a0c0341fe408ef1668dbbfdfac46", payload["pin"])
        self.assertIsNone(SECRET.search(result.stdout + result.stderr), "a key value leaked")

    def test_upstream_text_defaults_are_left_alone(self) -> None:
        text = RUNNER.read_text()
        # DeepSeek already picks {"thinking":{"type":"disabled"}} for its own endpoint;
        # assigning either variable would send an unsupported field instead.
        self.assertNotRegex(text, r"TEXT_MODEL_(?:BASE_URL|REASONING)\s*=")

    def test_embedded_runner_is_valid_python(self) -> None:
        text = RUNNER.read_text()
        body = text.split("cat >\"$runner\" <<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
        compile(body, "jev-browser-runner", "exec")
        self.assertIn("Agent(args.url, args.goal", body)

    def test_installer_and_skill_are_wired(self) -> None:
        self.assertIn("install_jev_browser.sh", (ROOT / "lib/main.sh").read_text())
        self.assertIn('"jev_browser"', (ROOT / "pi-defaults/install.py").read_text())
        for wiring in ("lib/slim_wiring.py", "lib/pi_model_policy.py"):
            self.assertIn(
                '"pi-skill/jev-browser/SKILL.md"',
                (ROOT / wiring).read_text(),
                f"{wiring} must stage the skill",
            )
        self.assertTrue(INSTALLER.stat().st_mode & 0o111)
        skill = SKILL.read_text()
        self.assertTrue(skill.startswith("---\nname: jev-browser\n"), "skill frontmatter")
        self.assertIn("jev-browser --url", skill)
        self.assertIn("verif", skill.lower(), "the skill must require outcome verification")


if __name__ == "__main__":
    unittest.main(verbosity=2)

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
import sys
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
        self.assertIn(
            '"pi-skill/jev-browser/SKILL.md"',
            (ROOT / "lib/slim_wiring.py").read_text(),
            "lib/slim_wiring.py must stage the skill",
        )
        self.assertTrue(INSTALLER.stat().st_mode & 0o111)
        skill = SKILL.read_text()
        self.assertTrue(skill.startswith("---\nname: jev-browser\n"), "skill frontmatter")
        self.assertIn("jev-browser --url", skill)
        self.assertIn("verif", skill.lower(), "the skill must require outcome verification")

    def test_clean_profile_policy_stages_the_skill(self) -> None:
        # The pi profile install runs the policy CLI without --adaptive, so the skill
        # has to be staged by the always-on policy path and not only by the refresh.
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "HOME": tmp,
                "PI_CODING_AGENT_DIR": tmp,
                "MEGAI_HOME": tmp,
                "MEGAI_SOURCE": str(ROOT),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            proc = subprocess.run(
                [sys.executable, "-B", str(ROOT / "lib/pi_model_policy.py")],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            staged = Path(tmp) / "skills/jev-browser/SKILL.md"
            self.assertTrue(staged.is_file(), "the clean profile must stage the skill")
            self.assertEqual(staged.read_bytes(), SKILL.read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)

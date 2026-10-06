"""Plane status uses disposable configuration and never connects to a server."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PlaneStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        (self.home / "lib").mkdir()
        for name in ["ui.sh", "plane_mcp_headers.py"]:
            shutil.copy2(ROOT / "lib" / name, self.home / "lib" / name)
        self.config = self.home / "mcp.json"
        self.env = dict(os.environ, HOME=str(self.home), MEGAI_HOME=str(self.home),
                        PI_CODING_AGENT_DIR=str(self.home))

    def status(self, entry):
        self.config.write_text(json.dumps({"mcpServers": {"plane": entry}}))
        before = self.config.read_bytes()
        result = subprocess.run(
            ["bash", str(ROOT / "lib/plane_mcp.sh"), "status", "--client", "pi"],
            env=self.env, text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(self.config.read_bytes(), before)
        return result

    def test_existing_http_entry_does_not_block(self):
        result = self.status({"url": "https://mcp.plane.so/http/api-key/mcp"})
        self.assertEqual(result.returncode, 0, "existing Plane entry blocks agents: " + result.stderr)
        self.assertIn("configured (user-managed", result.stdout)
        self.assertNotIn("unmanaged plane entry preserved", result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")

    def test_existing_stdio_entry_does_not_block(self):
        result = self.status({"command": "python3", "args": ["custom-plane.py"]})
        self.assertEqual(result.returncode, 0, "existing Plane entry blocks agents: " + result.stderr)
        self.assertIn("configured (user-managed", result.stdout)
        self.assertNotIn("connected", result.stdout)

    def test_disabled_custom_entry_is_not_ready(self):
        result = self.status({"command": "python3", "disabled": True})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("disabled", result.stderr)

    def test_invalid_custom_entries_still_fail(self):
        for entry in [None, "invalid", {}, {"command": ""}, {"url": 12}]:
            with self.subTest(entry=entry):
                result = self.status(entry)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("invalid", result.stderr)


if __name__ == "__main__":
    unittest.main()

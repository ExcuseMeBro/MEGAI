import contextlib
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/pi_session_metrics.py"
spec = importlib.util.spec_from_file_location("pi_metrics", SCRIPT)
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


class MetricsTests(unittest.TestCase):
    def test_metadata_only_filtering_and_no_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            at = "2026-10-17T12:00:00Z"
            entries = [{"type": "session", "id": "included"}]
            for duration, cached in [(100, 80), (300, 20)]:
                entries.append({"type": "message", "timestamp": at, "message": {
                    "role": "assistant", "durationMs": duration, "usage": {"input": 100, "cacheRead": cached},
                    "content": [{"type": "text", "text": "SECRET prompt"},
                                {"type": "toolCall", "name": "workflow_checkpoint", "arguments": {"secret": "TOKEN"}},
                                {"type": "toolCall", "name": "SECRET-CUSTOM-NAME"},
                                {"type": "toolCall", "name": "mcp__plane__workitem"}]}})
            entries += [{"type": "message", "timestamp": at, "message": {"role": "toolResult", "isError": True,
                         "content": [{"text": "SECRET failure"}]}},
                        {"type": "message", "timestamp": "2020-01-01T00:00:00Z", "message": {"role": "assistant", "durationMs": 99999}}]
            data = "\n".join(json.dumps(e) for e in entries) + '\nnot-json\n[]\n'
            (root / "a.jsonl").write_text(data)
            (root / "current.jsonl").write_text(data.replace('"included"', '"excluded"'))
            (root / "symlink.jsonl").symlink_to(root / "a.jsonl")
            before = hashlib.sha256((root / "a.jsonl").read_bytes()).hexdigest()
            result = metrics.analyze(root, datetime(2026, 10, 17, tzinfo=timezone.utc),
                                     datetime(2026, 10, 18, tzinfo=timezone.utc), "excluded")
            self.assertEqual(result["sessions_with_messages"], 1)
            self.assertEqual(result["tool_calls"], 6)
            self.assertEqual(result["counts"]["tool_errors"], 1)
            self.assertEqual(result["counts"]["malformed_lines"], 2)
            self.assertEqual(result["assistant_duration_ms"], {"samples": 2, "p50": 100, "p95": 300})
            self.assertEqual(result["direct_plane_checkpoint_percent"], 66.67)
            self.assertEqual(result["cache_read_percent"], 33.33)
            rendered = json.dumps(result)
            for private in ["SECRET", "TOKEN", temp, "included", "excluded"]:
                self.assertNotIn(private, rendered)
            self.assertEqual(before, hashlib.sha256((root / "a.jsonl").read_bytes()).hexdigest())

    def test_cli_excludes_current_file_and_validates_window(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "current.jsonl"
            path.write_text(json.dumps({"type": "message", "timestamp": "2026-10-17T12:00:00Z",
                                        "message": {"role": "assistant", "durationMs": 123}}))
            env = {**os.environ, "PI_SESSION_FILE": str(path)}
            result = subprocess.run([sys.executable, str(SCRIPT), "--sessions", temp, "--until", "2026-10-18T00:00:00Z"],
                                    capture_output=True, text=True, check=True, env=env)
            self.assertEqual(json.loads(result.stdout)["sessions_with_messages"], 0)
            for days in ["0", "-1", "nan", "inf", "1e300"]:
                result = subprocess.run([sys.executable, str(SCRIPT), "--sessions", temp, "--days", days],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)

    def test_invalid_durations_and_oversized_lines(self):
        self.assertIsNone(metrics.timestamp("not-a-date"))
        self.assertIsNone(metrics.timestamp("2026-10-17"))
        for value in [-1, True, float("nan"), float("inf"), "123", 10**400]:
            self.assertFalse(metrics.number(value))
        self.assertIsNone(metrics.percentile([], .5))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bounded.jsonl"
            path.write_bytes(b"x" * (metrics.MAX_LINE + 1))
            result = metrics.analyze(temp, datetime.min.replace(tzinfo=timezone.utc), datetime.max.replace(tzinfo=timezone.utc))
            self.assertEqual(result["counts"]["oversized_files_skipped"], 1)

    def test_empty_output_is_valid_json(self):
        with tempfile.TemporaryDirectory() as temp:
            output = io.StringIO()
            with contextlib.redirect_stdout(output), mock.patch.object(
                    sys, "argv", [str(SCRIPT), "--sessions", temp]):
                metrics.main()
            self.assertEqual(json.loads(output.getvalue())["tool_calls"], 0)


if __name__ == "__main__":
    unittest.main()

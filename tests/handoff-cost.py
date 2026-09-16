#!/usr/bin/env python3
"""Check the handoff-cost measurement logic on synthetic session logs.

Run: python3 -B tests/handoff-cost.py
Read-only: everything happens in a temporary directory.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmark" / "handoff-cost"))

import measure  # noqa: E402


def session_lines(model, cost, reads, writes=(), tokens=100):
    stamp = "2026-09-16T10:00:00.000Z"
    lines = [json.dumps({"type": "session", "timestamp": stamp})]
    calls = [
        {"type": "toolCall", "name": "read", "arguments": {"path": path}} for path in reads
    ] + [{"type": "toolCall", "name": "write", "arguments": {"path": path}} for path in writes]
    lines.append(
        json.dumps(
            {
                "type": "message",
                "timestamp": stamp,
                "message": {
                    "role": "assistant",
                    "provider": model.split("/")[0],
                    "model": model.split("/")[1],
                    "usage": {"totalTokens": tokens, "cost": {"total": cost}},
                    "content": calls,
                },
            }
        )
    )
    return lines


class HandoffCost(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.agent = Path(self.tmp.name) / "agent"
        root = self.agent / "sessions" / "--Users-bro-PROJECTS-demo--"
        child = self.agent / "sessions" / "--Users-bro-.paseo-worktrees-abc-demo-task--"
        root.mkdir(parents=True)
        child.mkdir(parents=True)
        (root / "2026-09-16T09-00-00-000Z_a.jsonl").write_text(
            "\n".join(
                session_lines(
                    measure.DEFAULT_TIER_MODEL,
                    1.0,
                    reads=["/repo/a.py", "/repo/b.py", "/repo/c.py"],
                    writes=["/tmp/writer-report.md", "/tmp/probe.py"],
                )
            )
        )
        (child / "2026-09-16T10-30-00-000Z_b.jsonl").write_text(
            "\n".join(
                session_lines(
                    "deepseek/deepseek-flash",
                    0.2,
                    reads=["/tmp/writer-report.md", "/repo/a.py", "/repo/b.py", "/repo/d.py"],
                )
            )
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_handoff_doc_filtering(self):
        for name in ("writer-report.md", "evidence.txt", "plan.json", "worker.log"):
            self.assertTrue(measure.is_handoff_doc("/tmp/" + name), name)
        for name in ("probe.py", "check.sql", "run.sh", "notes.md"):
            self.assertFalse(measure.is_handoff_doc("/tmp/" + name), name)
        self.assertFalse(measure.is_handoff_doc("/repo/writer-report.md"))

    def test_timestamp_formats(self):
        iso = measure.parse_timestamp("2026-09-16T10:00:00.000Z")
        self.assertIsNotNone(iso)
        self.assertIsNone(measure.parse_timestamp("not-a-time"))
        # epoch seconds and epoch millis must resolve to the same instant
        self.assertEqual(measure.parse_timestamp(int(iso.timestamp())), iso)
        self.assertEqual(measure.parse_timestamp(int(iso.timestamp() * 1000)), iso)

    def test_summary_counts_duplicate_discovery(self):
        summary = measure.summarize(measure.collect(str(self.agent), days=14))
        self.assertEqual(summary["totals"]["sessions"], 2)
        self.assertAlmostEqual(summary["totals"]["reported_cost"], 1.2, places=4)

        tiers = summary["tiers"]
        self.assertEqual(tiers["tier"]["sessions"], 1)
        self.assertEqual(tiers["other"]["sessions"], 1)
        self.assertAlmostEqual(tiers["tier_cost_share"], 1.0 / 1.2, places=4)

        handoffs = summary["handoffs"]
        self.assertEqual(handoffs["docs_written"], 1)  # /tmp/probe.py is scratch, not a doc
        self.assertEqual(handoffs["docs_read_back"], 1)
        self.assertEqual(handoffs["pairs"], 1)
        self.assertEqual(handoffs["fed_sessions"], 1)
        # downstream read 4 files, 2 of which the upstream session had already read
        self.assertEqual(handoffs["downstream_reads_mean"], 4.0)
        self.assertEqual(handoffs["duplicate_reads_mean"], 2.0)
        self.assertEqual(handoffs["upstream_reads_mean"], 3.0)
        self.assertAlmostEqual(handoffs["duplicate_share_mean"], 0.5, places=3)

    def test_render_and_json_paths(self):
        summary = measure.summarize(measure.collect(str(self.agent), days=14))
        self.assertIn("[1] tier split", measure.render(summary))
        self.assertIn("[2] handoff pairs", measure.render(summary))
        self.assertEqual(json.loads(json.dumps(summary))["handoffs"]["pairs"], 1)

    def test_missing_sessions_are_not_an_error(self):
        empty = Path(self.tmp.name) / "empty"
        empty.mkdir()
        self.assertEqual(measure.collect(str(empty), days=14), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

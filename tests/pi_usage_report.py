#!/usr/bin/env python3
"""Contracts for the read-only usage report.

The arithmetic is checked against a hand-computed fixture so the shipped numbers
cannot drift silently, and the report must never leak session paths, working
directories or message text. Missing usage is reported as missing, never as zero.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
sys.path.insert(0, str(LIB))

import pi_usage_report as report  # noqa: E402

TOOL_CALL = {"type": "toolCall"}


def message(role: str, **fields) -> dict:
    return {"type": "message", "timestamp": "2026-01-01T00:00:00Z", "message": {"role": role, **fields}}


def usage(inp: int, out: int, read: int, total: int, cost: float) -> dict:
    return {"input": inp, "output": out, "cacheRead": read, "cacheWrite": 0,
            "totalTokens": total, "cost": {"total": cost}}


def call(name: str, identifier: str) -> dict:
    return {**TOOL_CALL, "name": name, "id": identifier}


def session_lines() -> list[str]:
    return [
        json.dumps({"type": "session", "cwd": "/private/place"}),
        json.dumps(message("assistant", provider="p", model="m",
                           usage=usage(100, 10, 1000, 1110, 1.5),
                           content=[call("bash", "c1")])),
        json.dumps(message("toolResult", toolName="bash", content="x" * 400)),
        json.dumps(message("assistant", provider="p", model="m",
                           usage=usage(200, 20, 2000, 2220, 2.5),
                           content=[call("read", "c2"), call("read", "c3")])),
        json.dumps(message("toolResult", toolName="read", content="y" * 100)),
        json.dumps(message("assistant", provider="p", model="m",
                           usage=usage(300, 30, 3000, 3330, 3.5), content=[])),
        json.dumps({"type": "compaction", "usage": usage(50, 5, 0, 55, 0.5)}),
        "this is not json",
    ]


class ReportCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = Path(tempfile.mkdtemp(prefix="pi-usage-report-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.temporary, ignore_errors=True))
        self.sessions = self.temporary / "sessions"
        (self.sessions / "--private-place--").mkdir(parents=True)
        self.file = self.sessions / "--private-place--" / "2026-01-01T00-00-00_a.jsonl"
        self.file.write_text("\n".join(session_lines()) + "\n")

    def build(self, **kwargs) -> dict:
        options = {"days": None, "start": None, "end": None, "by_project": False, "limit": None}
        options.update(kwargs)
        return report.build_report(self.sessions, **options)


class ArithmeticTests(ReportCase):
    def test_hand_computed_totals(self):
        result = self.build()
        totals = result["totals"]
        self.assertEqual(totals["turns"], 3)
        self.assertEqual(totals["tool_calls"], 3)
        self.assertEqual(totals["compactions"], 1)
        self.assertEqual(totals["malformed_lines"], 1)
        self.assertEqual(totals["batching"],
                         {"0_tool_calls": 1, "1_tool_calls": 1, "2_tool_calls": 1,
                          "3_tool_calls": 0, "4_tool_calls": 0, "5_tool_calls": 0})
        self.assertAlmostEqual(totals["single_tool_call_ratio"], 1 / 3)
        block = result["models"]["p/m"]
        self.assertEqual(block["turns"], 3)
        self.assertEqual(block["input"], 600)
        self.assertEqual(block["cacheRead"], 6000)
        self.assertEqual(block["totalTokens"], 6660)
        self.assertEqual(block["reported_cost"], 7.5)
        self.assertEqual(block["usage_objects"], 3)
        self.assertEqual(block["usage_objects_complete"], 3)
        self.assertEqual(block["prompt_tokens"], 6600)
        self.assertAlmostEqual(block["context_tokens_per_turn"], 2200)
        self.assertAlmostEqual(block["reported_cost_per_turn"], 2.5)
        self.assertEqual(block["context_buckets"], {"under_50k": 3})

    def test_replay_estimate_matches_hand_computation(self):
        tools = self.build()["tools"]
        # bash: 400-char payload -> 402 serialized chars -> 100 tokens, re-sent on 2 later turns.
        self.assertEqual(tools["bash"]["calls"], 1)
        self.assertEqual(tools["bash"]["chars"], 402)
        self.assertEqual(tools["bash"]["replay_replays"], 2)
        self.assertEqual(tools["bash"]["replay_tokens_estimate"], 200)
        # read: 102 serialized chars -> 25 tokens, re-sent on 1 later turn.
        self.assertEqual(tools["read"]["replay_replays"], 1)
        self.assertEqual(tools["read"]["replay_tokens_estimate"], 25)
        self.assertEqual(tools["read"]["estimate_basis"], report.ESTIMATE_BASIS)

    def test_summarization_usage_is_reported_not_hidden(self):
        summary = self.build()["totals"]["summarization"]
        self.assertEqual(summary["summarizations"], 1)
        self.assertEqual(summary["input"], 50)
        self.assertEqual(summary["output"], 5)
        self.assertAlmostEqual(summary["reported_cost"], 0.5)
        self.assertEqual(summary["usage_missing"], 0)

    def test_missing_usage_is_missing_not_zero(self):
        self.file.write_text(json.dumps(message("assistant", provider="p", model="m", content=[])) + "\n")
        block = self.build()["models"]["p/m"]
        self.assertEqual(block["turns"], 1)
        self.assertEqual(block["missing_usage"], 1)
        self.assertEqual(block["usage_objects"], 0)
        self.assertEqual(block["totalTokens"], 0)
        self.assertEqual(block["reported_cost"], 0)
        self.assertIsNone(block["context_tokens_per_turn"] or None)

    def test_unattributed_tool_result_uses_the_calling_tool(self):
        self.file.write_text("\n".join([
            json.dumps(message("assistant", provider="p", model="m",
                               usage=usage(1, 1, 1, 3, 0.0), content=[call("bash", "c1")])),
            json.dumps(message("toolResult", toolCallId="c1", content="z" * 4)),
        ]) + "\n")
        self.assertEqual(self.build()["tools"]["bash"]["calls"], 1)

    def test_unknown_tool_names_stay_visible(self):
        self.file.write_text("\n".join([
            json.dumps(message("assistant", provider="p", model="m",
                               usage=usage(1, 1, 1, 3, 0.0), content=[call("bash", "c1")])),
            json.dumps(message("toolResult", content="z" * 4)),
        ]) + "\n")
        self.assertEqual(self.build()["tools"]["unknown"]["calls"], 1)

    def test_time_window_filters_entries(self):
        after = report.parse_time("2026-01-01T00:00:01Z")
        result = self.build(start=after)
        self.assertEqual(result["window"]["sessions_matched"], 0)
        self.assertEqual(result["totals"]["turns"], 0)

    def test_unparseable_session_timestamp_is_tolerated(self):
        line = json.loads(session_lines()[1])
        line["timestamp"] = "not-a-time"
        self.file.write_text(json.dumps(line) + "\n")
        self.assertEqual(self.build()["totals"]["turns"], 1)

    def test_numeric_junk_is_missing_not_zero(self):
        self.assertIsNone(report.number(-1))
        self.assertIsNone(report.number(True))
        self.assertIsNone(report.number("12"))
        self.assertIsNone(report.number(float("nan")))
        self.assertEqual(report.number(0), 0.0)


class PrivacyTests(ReportCase):
    def test_report_omits_paths_content_and_working_directory(self):
        text = json.dumps(self.build())
        for secret in ("/private/place", str(self.temporary), "this is not json", "xxxx"):
            with self.subTest(secret=secret):
                self.assertNotIn(secret, text)

    def test_by_project_prints_only_the_session_directory_label(self):
        text = json.dumps(self.build(by_project=True))
        self.assertIn("--private-place--", text)
        self.assertNotIn(str(self.temporary), text)


class CliTests(ReportCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-B", str(LIB / "pi_usage_report.py"),
                               "--agent-dir", str(self.sessions), "--days", "0", *args],
                              capture_output=True, text=True, check=False,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))

    def test_text_and_json_modes_agree_on_turns(self):
        text = self.run_cli("--text")
        self.assertEqual(text.returncode, 0, text.stderr)
        self.assertIn("turns with exactly one tool call: 33.3%", text.stdout)
        self.assertIn("estimate basis: chars/4", text.stdout)
        payload = self.run_cli()
        self.assertEqual(payload.returncode, 0, payload.stderr)
        self.assertEqual(json.loads(payload.stdout)["totals"]["turns"], 3)

    def test_invalid_limit_is_rejected(self):
        self.assertNotEqual(self.run_cli("--limit", "0").returncode, 0)


if __name__ == "__main__":
    unittest.main()

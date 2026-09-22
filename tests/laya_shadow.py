#!/usr/bin/env python3
"""Contracts for the Laya ledger reader.

The agreement, cutoff and disagreement numbers are checked against a hand-built
fixture so the printed advice cannot drift from the ledger it claims to read, and
`note` must refuse an id the ledger never recorded instead of writing an
unjoinable row.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"

# Loaded by path: this file is named after the module it tests, so a plain import
# would find the test module itself when the suite is run from this directory.
spec = importlib.util.spec_from_file_location("laya_shadow_lib", LIB / "laya_shadow.py")
shadow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shadow)


def call(rid: str, source: str, answers: dict) -> dict:
    return {"id": rid, "source": source, "model": "convaiinnovations/laya", "route": "english",
            "runtime": "local:laya", "t": "2026-01-01T00:00:00.000Z", "answers": answers}


def noul(value: float) -> dict:
    return {"type": "noul", "answer": value}


def choice(label: str, confidence: float | None = None) -> dict:
    entry = {"type": "choice", "answer": label}
    if confidence is not None:
        entry["confidence"] = confidence
    return entry


class LedgerReader(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "laya-calls.jsonl"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, rows: list[dict]) -> None:
        self.path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def cli(self, *args: str, env: dict | None = None, path: bool = True) -> subprocess.CompletedProcess:
        args = (("--path", str(self.path)) if path else ()) + args
        return subprocess.run(
            [sys.executable, str(LIB / "laya_shadow.py"), *args],
            capture_output=True, text=True, env={**os.environ, **(env or {})},
        )

    def test_agreement_cutoffs_and_disagreements(self) -> None:
        self.write([
            call("aaaa1111", "tool", {"mode": choice("routine", 0.9), "needs_approval": noul(0.1)}),
            call("bbbb2222", "tool", {"mode": choice("guarded", 0.7), "needs_approval": noul(0.9)}),
            call("cccc3333", "gate", {"object": noul(0.8)}),
            call("dddd4444", "sift", {"relevant": noul(0.2)}),
            {"id": "aaaa1111", "kind": "actual", "question": "mode", "actual": "routine", "source": "agent"},
            {"id": "bbbb2222", "kind": "actual", "question": "mode", "actual": "guarded", "source": "agent"},
            {"id": "bbbb2222", "kind": "actual", "question": "needs_approval", "actual": "yes", "source": "agent"},
            {"id": "aaaa1111", "kind": "actual", "question": "needs_approval", "actual": "no", "source": "agent"},
            {"id": "dddd4444", "kind": "actual", "question": "relevant", "actual": "no", "source": "user"},
        ])
        calls, failures, labels = shadow.split(shadow.read_rows(self.path))
        questions = shadow.collect(calls, labels)
        text = shadow.report(self.path, calls, failures, questions)

        self.assertEqual((len(calls), len(failures)), (4, 0))
        self.assertIn("sources: tool 2, gate 1, sift 1", text)
        self.assertIn("routes: english 4", text)
        self.assertIn("models: convaiinnovations/laya 4", text)
        self.assertIn("languages: auto 4", text)
        self.assertIn("labeled answers: 5 of 6", text)
        self.assertIn("mode", text)
        self.assertIn("100.0%", text)          # mode: routine/routine and guarded/guarded
        self.assertIn("0.50", text)            # the noul cutoff table is present
        # `bbbb2222`/needs_approval said yes (p 0.90) and the outcome was yes; the
        # sift relevance row said no (p 0.20) and the outcome was no — neither is a
        # disagreement, so the table reports the one row that is.
        self.assertEqual([row["question"] for row in shadow.disagreements_of(questions)], [])

    def test_disagreement_row_is_listed_with_its_id(self) -> None:
        self.write([
            call("eeee5555", "tool", {"verdict": choice("pass")}),
            {"id": "eeee5555", "kind": "actual", "question": "verdict", "actual": "blocked", "source": "agent"},
        ])
        result = self.cli("report")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("disagreements (1 rows, the next test set)", result.stdout)
        self.assertIn("eeee5555", result.stdout)
        self.assertIn("blocked", result.stdout)

    def test_score_answers_are_never_agreement(self) -> None:
        self.write([
            call("ffff6666", "tool", {"effort": {"type": "score", "answer": 2.06}}),
            {"id": "ffff6666", "kind": "actual", "question": "effort", "actual": "2", "source": "agent"},
        ])
        self.assertIsNone(shadow.agrees("score", 2.06, "2"))
        result = self.cli("report")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no outcome labels yet", result.stdout)

    def test_failure_rows_are_counted_apart_and_never_answered(self) -> None:
        self.write([
            call("aaaa1111", "tool", {"mode": choice("routine")}),
            {"id": "bbbb2222", "source": "gate", "model": None, "route": None,
             "error": "laya: inference failed (child exited 1)", "runtime": "local:laya"},
        ])
        text = self.cli("report").stdout
        self.assertIn("calls: 1", text)
        self.assertIn("failed: 1", text)
        self.assertIn("no outcome labels yet", text)

    def test_note_appends_and_refuses_an_unknown_id(self) -> None:
        self.write([call("aaaa1111", "tool", {"mode": choice("routine")})])
        before = self.path.read_text(encoding="utf-8")

        missing = self.cli("note", "--id", "nope", "--actual", "guarded")
        self.assertEqual(missing.returncode, 1)
        self.assertIn("no recorded call with id", missing.stderr)
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)

        wrong = self.cli("note", "--id", "aaaa1111", "--question", "effort", "--actual", "guarded")
        self.assertEqual(wrong.returncode, 1)
        self.assertIn("asked no question", wrong.stderr)

        noted = self.cli("note", "--id", "aaaa1111", "--actual", "guarded", "--note", "user overrode it")
        self.assertEqual(noted.returncode, 0, noted.stderr)
        label = json.loads(self.path.read_text(encoding="utf-8").strip().splitlines()[-1])
        self.assertEqual(label["kind"], "actual")
        self.assertEqual(label["actual"], "guarded")
        self.assertNotIn("question", label)
        self.assertEqual(label["source"], "agent")

        report = self.cli("report").stdout
        self.assertIn("guarded", report)
        self.assertIn("disagreements (1 rows, the next test set)", report)

    def test_missing_ledger_and_broken_line(self) -> None:
        empty = self.cli("report")
        self.assertEqual(empty.returncode, 0, empty.stderr)
        self.assertIn("calls: 0", empty.stdout)

        self.path.write_text(
            json.dumps(call("aaaa1111", "tool", {"mode": choice("routine")})) + "\n{not json\n",
            encoding="utf-8",
        )
        broken = self.cli("report")
        self.assertEqual(broken.returncode, 0, broken.stderr)
        self.assertIn("calls: 1", broken.stdout)

    def test_ledger_off_is_reported_not_silently_empty(self) -> None:
        result = self.cli("report", env={"LAYA_LOG": "0"}, path=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("LAYA_LOG=0", result.stderr)


if __name__ == "__main__":
    unittest.main()

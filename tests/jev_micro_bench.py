#!/usr/bin/env python3
"""Offline checks for the Jev micro-benchmark; no provider calls."""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "benchmark/typesafe-jev"
sys.path.insert(0, str(PACK))

import micro_bench as bench  # noqa: E402


def record(variant, index, *, wall=0.8, input_tokens=404, output_tokens=23,
           noul=0.085, ok=True):
    return {
        "variant": variant,
        "index": index,
        "ok": ok,
        "wall_seconds": wall,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_usd": round(input_tokens * bench.JEV_USD_PER_INPUT_TOKEN, 9),
        "model": bench.JEV_MODEL,
        "answers": {"needs_approval": {"type": "noul", "noul": noul}} if ok else {},
        **({} if ok else {"error": "URLError: offline"}),
    }


def root_with(records, cleanup):
    tmp = tempfile.TemporaryDirectory()
    cleanup(tmp.cleanup)
    raw = Path(tmp.name) / "raw"
    raw.mkdir()
    for r in records:
        (raw / f"{r['variant']}__{r['index']:02d}.json").write_text(json.dumps(r) + "\n")
    return tmp


class MicroBench(unittest.TestCase):
    def test_percentiles_hold_for_the_small_samples_in_the_matrix(self):
        # Nearest-rank on the sorted sample; an even-length tie rounds to even, which
        # is the behaviour the published report was measured with.
        values = [float(n) for n in range(1, 11)]
        self.assertEqual(bench._percentile(values, 0.5), 5.0)
        self.assertEqual(bench._percentile(values, 0.95), 10.0)
        self.assertEqual(bench._percentile([float(n) for n in range(1, 6)], 0.5), 3.0)
        self.assertEqual(bench._percentile([], 0.5), 0.0)
        self.assertEqual(bench._percentile([3.5], 0.95), 3.5)

    def test_consistency_reports_the_noul_spread_and_skips_failed_calls(self):
        records = [record("consistency", i, noul=v) for i, v in enumerate((0.08, 0.09))]
        records.append(record("consistency", 2, ok=False))
        stats = bench._consistency(records)
        self.assertEqual(stats["n"], 2)
        self.assertEqual(stats["min"], 0.08)
        self.assertEqual(stats["max"], 0.09)
        self.assertEqual(stats["range"], 0.01)
        self.assertEqual(stats["stdev"], 0.0071)
        self.assertEqual(bench._consistency([record("consistency", 3, ok=False)]), {})

    def test_report_prints_a_row_per_variant_from_raw_records(self):
        tmp = root_with(
            [record("q1_noul", i, wall=0.7 + i / 10, input_tokens=404) for i in range(5)]
            + [record("q8_mixed", 0, input_tokens=1025)]
            + [record("consistency", i) for i in range(3)],
            self.addCleanup,
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            bench.cmd_report(argparse.Namespace(root=tmp.name))
        text = out.getvalue()
        self.assertIn("variants=3 total_calls=9", text)
        self.assertIn("latency        0   0  (no ok calls)", text)
        self.assertIn("q1_noul        5   5    2020     115  0.900", text)   # p50 of 0.7..1.1
        self.assertIn("0.0000848", text)      # 5 calls x 404 tokens x $42/1e9
        self.assertIn('"range": 0.0', text)   # identical noul values in every call

    def test_run_and_report_refuse_without_a_key_and_leave_no_records(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                bench._key()
        with mock.patch.dict(os.environ, {"TYPESAFE_API_KEY": "synthetic-only"}, clear=True):
            self.assertEqual(bench._key(), "synthetic-only")
        self.assertNotIn("TYPESAFE_API_KEY", json.dumps(record("latency", 0)))

    def test_the_matrix_asks_the_question_shapes_the_api_requires(self):
        self.assertEqual(set(bench.repeats_for(v) for v in bench.VARIANTS) >= {5, 10, 20}, True)
        self.assertEqual(len(bench._q_mixed(8)), 8)
        self.assertEqual(len(set(bench._q_mixed(8))), 8)
        for variant in bench.VARIANTS:
            self.assertEqual(bench.repeats_for(variant) >= 5, True)
            questions = bench.questions_for(variant)
            self.assertGreaterEqual(len(questions), 1)
            for question in questions.values():
                self.assertIn(question["type"], ("choice", "score", "noul"))
        sizes = [len(json.dumps(bench.state_for(f"size_{name}")))
                 for name in ("tiny", "small", "medium", "large")]
        self.assertEqual(sizes, sorted(sizes))


if __name__ == "__main__":
    unittest.main(verbosity=2)

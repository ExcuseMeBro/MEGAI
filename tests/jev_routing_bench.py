#!/usr/bin/env python3
"""Offline checks for the Jev model-routing benchmark; no provider calls."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "benchmark/jev-routing"
sys.path.insert(0, str(PACK))

import run_routing_bench as bench  # noqa: E402

LABEL = {"type": "bug", "effort": 1, "needs_approval": False}
ITEMS = [
    {"id": "a", "request": "fix one file", "label": LABEL},
    {"id": "b", "request": "cross-module rework", "label": LABEL},
    {"id": "c", "request": "add a flag", "label": LABEL},
]


def record(arm, item_id, *, ok, cost, chosen=None, choice=None, hard=None, confidence=None):
    parsed = {"type": "bug", "effort": 1, "needs_approval": False} if ok else None
    return {
        "arm": arm, "chosen_arm": chosen or arm, "item_id": item_id, "label": LABEL,
        "parsed": parsed, "parse_error": "" if ok else "no JSON object in the answer",
        "type_ok": ok, "effort_ok": ok, "effort_delta": 0 if ok else None,
        "approval_ok": ok, "all_ok": ok, "cost_usd": cost, "wall_seconds": 1.0,
        "route": None if choice is None else
                 {"choice": choice, "confidence": confidence, "probabilities": None, "hard": hard},
    }


def fixture():
    return [
        record(bench.DEEPSEEK, "a", ok=True, cost=0.001),
        record(bench.MINIMAX, "a", ok=False, cost=0.004),
        record(bench.ROUTE, "a", ok=True, cost=0.0012, chosen=bench.DEEPSEEK,
               choice="deepseek-flash", hard=0.2, confidence=0.8),
        record(bench.DEEPSEEK, "b", ok=False, cost=0.001),
        record(bench.MINIMAX, "b", ok=True, cost=0.005),
        record(bench.ROUTE, "b", ok=True, cost=0.0052, chosen=bench.MINIMAX,
               choice="MiniMax-M3", hard=0.9, confidence=0.7),
        record(bench.DEEPSEEK, "c", ok=True, cost=0.001),
        record(bench.MINIMAX, "c", ok=True, cost=0.005),
        record(bench.ROUTE, "c", ok=False, cost=0.0055, chosen=bench.MINIMAX,
               choice="MiniMax-M3", hard=0.6, confidence=0.6),
    ]


class RoutingBench(unittest.TestCase):
    def test_oracle_matching_and_regret(self):
        analysis = bench.analyze(fixture(), ITEMS)
        self.assertEqual(analysis["complete"], 3)
        self.assertEqual(analysis["missing"], [])
        self.assertEqual(analysis["route_deepseek"], 1)
        self.assertEqual(analysis["route_minimax"], 2)
        self.assertEqual(analysis["oracle"], {bench.DEEPSEEK: 2, bench.MINIMAX: 1})
        self.assertEqual(analysis["neither_correct"], 0)
        self.assertEqual(analysis["matched"], 2)
        self.assertEqual(analysis["lost"], ["c"])
        self.assertEqual(analysis["oracle_pick_hit"], 3)
        self.assertEqual(analysis["route_ok"], 2)
        self.assertAlmostEqual(analysis["route_cost"], 0.0119)
        self.assertAlmostEqual(analysis["oracle_cost"], 0.007)
        self.assertAlmostEqual(analysis["hard_ok"], [0.2, 0.9], places=6)
        self.assertAlmostEqual(analysis["hard_bad"], [0.6], places=6)

    def test_missing_arm_is_not_counted(self):
        analysis = bench.analyze(fixture()[:-3], ITEMS)
        self.assertEqual(analysis["complete"], 2)
        self.assertEqual(analysis["missing"], ["c"])

    def test_failed_routing_call_is_recorded(self):
        rows = fixture()
        rows[5] = record(bench.ROUTE, "b", ok=True, cost=0.0012, chosen=bench.DEEPSEEK)
        analysis = bench.analyze(rows, ITEMS)
        self.assertEqual(analysis["route_failed"], 1)
        self.assertEqual(analysis["route_deepseek"], 2)

    def test_report_runs_offline_and_states_the_lost_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            items_path = Path(tmp) / "items.json"
            items_path.write_text(json.dumps({"policy": {}, "items": ITEMS}))
            results_path = Path(tmp) / "trials.jsonl"
            results_path.write_text("".join(json.dumps(r) + "\n" for r in fixture()))
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                status = bench.report(items_path, results_path)
        output = stream.getvalue()
        self.assertEqual(status, 0)
        self.assertIn("lost correctness (routed failed where a fixed arm passed): 1 [c]", output)
        self.assertIn("router picked a fully-correct fixed arm: 3/3", output)
        self.assertIn("routed cost is", output)

    def test_route_state_carries_policy_and_request(self):
        state = bench.route_state({"type": "policy"}, "do the thing")
        self.assertEqual(state["request"], "do the thing")
        self.assertEqual(state["policy"], {"type": "policy"})
        self.assertEqual(state["candidates"], ["deepseek-flash", "MiniMax-M3"])

    def test_router_questions_are_sent_and_a_missing_choice_is_recorded(self):
        seen = {}

        def fake_jev(state, key, questions=None):
            seen["questions"] = questions
            seen["state"] = state
            return {"answers": {"hard": {"noul": 0.4}}, "usage": {"input_tokens": 100}}

        def fake_pi(arm, prompt, cwd):
            return ('{"type": "bug", "effort": 1, "needs_approval": false}',
                    {"input": 5, "output": 6, "cache_read": 0, "total": 11, "cost_usd": 0.001},
                    {"reported_models": [arm], "exit_status": 0, "stderr_tail": []})

        with mock.patch.object(bench, "jev_ask", fake_jev), mock.patch.object(bench, "pi_ask", fake_pi):
            record = bench.run_item(bench.ROUTE, {"type": "t", "effort": "e", "approval": "a"},
                                    ITEMS[0], Path(tempfile.gettempdir()), "key")
        self.assertEqual(seen["questions"], bench.ROUTE_QUESTIONS)
        self.assertEqual(seen["state"]["request"], ITEMS[0]["request"])
        self.assertEqual(record["chosen_arm"], bench.DEEPSEEK)
        self.assertIn("no model choice", record["error"])
        self.assertTrue(record["all_ok"])
        self.assertAlmostEqual(record["router_cost_usd"], round(100 * bench.JEV_USD_PER_INPUT_TOKEN, 9))


if __name__ == "__main__":
    unittest.main()

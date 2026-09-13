#!/usr/bin/env python3
"""Read-only session metrics helper contracts (optimization 6).

The helper aggregates explicit task boundaries from Pi JSONL sessions without
emitting transcript content or private paths, and never invents child tokens,
provider waits or billed cost. Native loader fixtures in the other suite are
unrelated; these cases are pure JSONL arithmetic.
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

import pi_task_metrics as metrics  # noqa: E402

USAGE_1 = {
    "input": 100, "output": 20, "cacheRead": 1000, "cacheWrite": 5,
    "totalTokens": 1125, "reasoning": 7,
    "cost": {"input": 1.0, "output": 2.0, "cacheRead": 0.1, "cacheWrite": 0.5, "total": 3.6},
}
USAGE_2 = {
    "input": 200, "output": 30, "cacheRead": 2000, "cacheWrite": 0,
    "totalTokens": 2230, "reasoning": 3,
    "cost": {"input": 0.5, "output": 0.4, "cacheRead": 0.2, "cacheWrite": 0.0, "total": 1.1},
}


def assistant(entry_id: str, parent_id: str, stamp: str, usage: dict, *, model: str = "m1",
              provider: str = "p1", tool_calls: int = 0) -> dict:
    content = [{"type": "text", "text": "SENTINEL-TRANSCRIPT"}]
    for index in range(tool_calls):
        content.append({"type": "toolCall", "id": f"c{index}", "name": "bash", "arguments": {}})
    return {
        "type": "message", "id": entry_id, "parentId": parent_id, "timestamp": stamp,
        "message": {"role": "assistant", "content": content, "provider": provider,
                    "model": model, "usage": usage, "stopReason": "stop"},
    }


def message(entry_id: str, parent_id: str, stamp: str, role: str, **extra) -> dict:
    body = {"role": role, "content": [{"type": "text", "text": "SENTINEL-TRANSCRIPT"}]}
    body.update(extra)
    return {"type": "message", "id": entry_id, "parentId": parent_id, "timestamp": stamp, "message": body}


def session_file(path: Path, cwd: str, entries: list[dict], *, session_id: str = "sess-1",
                 parent_session: str | None = None, version: int = 3) -> Path:
    header = {"type": "session", "version": version, "id": session_id,
              "timestamp": "2024-12-03T13:59:00.000Z", "cwd": cwd}
    if parent_session is not None:
        header["parentSession"] = parent_session
    path.write_text("".join(json.dumps(item) + "\n" for item in [header, *entries]))
    return path


def tree_entries():
    return [
        message("u1", None, "2024-12-03T14:00:00.000Z", "user"),
        assistant("a1", "u1", "2024-12-03T14:00:01.000Z", USAGE_1, tool_calls=2),
        message("t1", "a1", "2024-12-03T14:00:02.000Z", "toolResult", toolCallId="c0",
                toolName="bash", isError=True),
        message("u2", "t1", "2024-12-03T14:00:03.000Z", "user"),
        assistant("a2", "u2", "2024-12-03T14:00:04.000Z", USAGE_2),
        # alternate branch off a1, later timestamp
        message("u3", "a1", "2024-12-03T14:00:05.000Z", "user"),
        assistant("a3", "u3", "2024-12-03T14:00:06.000Z", USAGE_1),
        {"type": "compaction", "id": "k1", "parentId": "a2",
         "timestamp": "2024-12-03T14:00:07.000Z", "summary": "SENTINEL-TRANSCRIPT",
         "tokensBefore": 10, "usage": USAGE_1},
    ]


class TaskMetrics(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="megai-task-metrics-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.sessions = self.root / "sessions"
        self.sessions.mkdir()

    def run_cli(self, *args, ok: bool = True, timeout: float = 10) -> subprocess.CompletedProcess:
        result = subprocess.run(
            [sys.executable, str(LIB / "pi_task_metrics.py"), *args],
            capture_output=True, text=True, check=False, timeout=timeout,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        )
        if ok and result.returncode != 0:
            self.fail(f"CLI failed: {' '.join(args)}\n{result.stderr}")
        return result

    def parent_session(self, entries=None) -> Path:
        return session_file(self.sessions / "parent.jsonl", "/private/secret/project",
                            tree_entries() if entries is None else entries)

    def test_entry_boundary_ancestry_and_reasoning_not_in_total(self):
        path = self.parent_session()
        result = self.run_cli("--parent", str(path), "--start-entry", "u1", "--end-entry", "a2")
        payload = json.loads(result.stdout)
        parent = payload["parent"]
        self.assertEqual(parent["boundary_mode"], "ancestry")
        self.assertEqual(parent["selected_entries"], 5)
        usage = parent["usage"]
        self.assertEqual(usage["input"], 300)
        self.assertEqual(usage["output"], 50)
        self.assertEqual(usage["cacheRead"], 3000)
        self.assertEqual(usage["cacheWrite"], 5)
        self.assertEqual(usage["reported_totalTokens"], 3355)
        self.assertEqual(usage["total"], 3355)
        self.assertEqual(usage["reasoning"], 10, "reasoning is reported but never added to total")
        self.assertEqual(parent["usage_coverage"]["reasoning_reported"], 2)
        self.assertEqual(parent["usage_coverage"]["total_tokens_reported"], 2)
        cost = parent["cost"]
        self.assertEqual(cost["total"], 4.7)
        self.assertEqual(parent["assistant_messages"], 2)
        self.assertEqual(parent["tool_calls"], 2)
        self.assertEqual(parent["tool_errors"], 1)
        self.assertEqual(parent["models"], {"p1/m1": 2})
        self.assertEqual(parent["user_messages"], 2)

    def test_compaction_usage_counted_and_tool_calls_ok(self):
        entries = tree_entries()
        entries.append({"type": "branch_summary", "id": "b1", "parentId": "a2",
                        "timestamp": "2024-12-03T14:00:08.000Z", "fromId": "a1",
                        "summary": "SENTINEL-TRANSCRIPT", "usage": USAGE_2})
        path = self.parent_session(entries)
        payload = json.loads(self.run_cli("--parent", str(path), "--start-entry", "u1",
                                          "--end-entry", "k1").stdout)
        parent = payload["parent"]
        self.assertEqual(parent["compactions"], 1)
        self.assertEqual(parent["usage"]["input"], 400)
        payload = json.loads(self.run_cli("--parent", str(path), "--start-entry", "u1",
                                          "--end-entry", "b1").stdout)
        parent = payload["parent"]
        self.assertEqual(parent["branch_summaries"], 1)
        self.assertEqual(parent["usage"]["input"], 500)

    def test_chronological_mode_covers_other_branches(self):
        path = self.parent_session()
        payload = json.loads(self.run_cli(
            "--parent", str(path), "--start-time", "2024-12-03T14:00:05.000Z",
            "--end-time", "2024-12-03T14:00:07.000Z").stdout)
        parent = payload["parent"]
        self.assertEqual(parent["boundary_mode"], "chronological")
        self.assertEqual(parent["selected_entries"], 3)  # u3, a3, k1
        self.assertEqual(parent["usage"]["input"], 200)
        self.assertEqual(parent["assistant_messages"], 1)

    def test_unknown_children_stay_unknown_not_zero(self):
        path = self.parent_session()
        payload = json.loads(self.run_cli("--parent", str(path), "--start-entry", "u1",
                                          "--end-entry", "a2").stdout)
        children = payload["child_attribution"]
        self.assertEqual(children["mode"], "unknown")
        self.assertFalse(children["totals_known"])
        self.assertIsNone(children["totals"])
        self.assertFalse(children["complete"])
        self.assertTrue(any("unknown" in note for note in payload["notes"]))
        self.assertIsNone(payload["totals"])
        self.assertFalse(payload["totals_known"])
        self.assertEqual(payload["observed_totals"]["usage"]["input"], 300)
        self.assertIsNone(children["observed_totals"])

    def test_partial_children_observed_but_complete_totals_null(self):
        parent = self.parent_session()
        child = session_file(self.sessions / "child.jsonl", "/private/secret/project",
                             [message("cu1", None, "2024-12-03T14:00:01.000Z", "user"),
                              assistant("ca1", "cu1", "2024-12-03T14:00:02.000Z", USAGE_2)],
                             session_id="sess-2")
        payload = json.loads(self.run_cli(
            "--parent", str(parent), "--child", str(child),
            "--start-time", "2024-12-03T14:00:00.000Z",
            "--end-time", "2024-12-03T14:00:04.000Z").stdout)
        children = payload["child_attribution"]
        self.assertEqual(children["mode"], "explicit")
        self.assertFalse(children["complete"])
        self.assertFalse(children["totals_known"])
        self.assertIsNone(children["totals"], "partial child scope must not claim a complete child total")
        self.assertEqual(children["observed_totals"]["usage"]["input"], 200)
        self.assertIsNone(payload["totals"], "complete task total is unknown until children are asserted complete")
        self.assertFalse(payload["totals_known"])
        self.assertEqual(payload["observed_totals"]["usage"]["input"], 500)
        self.assertTrue(any("complete task/child totals stay null" in note for note in payload["notes"]))

    def test_nested_tool_result_usage_with_explicit_child_blocks_complete_totals(self):
        usage = {"input": 10, "output": 1, "cacheRead": 0, "cacheWrite": 0,
                 "totalTokens": 11,
                 "cost": {"input": 0.1, "output": 0.1, "cacheRead": 0.0,
                          "cacheWrite": 0.0, "total": 0.2}}
        parent = session_file(self.sessions / "parent.jsonl", "/private/secret/project",
                              [message("t1", None, "2024-12-03T14:00:00.000Z", "toolResult",
                                       toolCallId="c0", toolName="bash", usage=usage)])
        child = session_file(self.sessions / "child.jsonl", "/private/secret/project",
                             [assistant("ca1", None, "2024-12-03T14:00:00.000Z", dict(usage))],
                             session_id="sess-2")
        payload = json.loads(self.run_cli(
            "--parent", str(parent), "--child", str(child), "--children-complete",
            "--start-time", "2024-12-03T14:00:00.000Z",
            "--end-time", "2024-12-03T14:00:01.000Z").stdout)
        # Observed subtotals stay separately labeled: no value-based dedupe.
        self.assertEqual(payload["parent"]["usage"]["input"], 10)
        self.assertEqual(payload["children"][0]["usage"]["input"], 10)
        self.assertEqual(payload["observed_totals"]["usage"]["input"], 20)
        self.assertTrue(payload["nested_usage_overlap_suspected"])
        self.assertIsNone(payload["totals"], "a possible nested-child overlap must not report a complete total")
        self.assertFalse(payload["totals_known"])
        self.assertIsNone(payload["child_attribution"]["totals"])
        self.assertFalse(payload["child_attribution"]["totals_known"])
        self.assertTrue(any("toolResult usage may summarize" in note for note in payload["notes"]))
        # The same parent without explicit children keeps the single-session total.
        control = json.loads(self.run_cli(
            "--parent", str(parent), "--assert-no-children",
            "--start-time", "2024-12-03T14:00:00.000Z",
            "--end-time", "2024-12-03T14:00:01.000Z").stdout)
        self.assertFalse(control["nested_usage_overlap_suspected"])
        self.assertEqual(control["totals"]["usage"]["input"], 10)

    def test_declared_complete_children_with_incomplete_usage_keep_totals_unknown(self):
        parent = self.parent_session()
        child = session_file(self.sessions / "child.jsonl", "/private/secret/project",
                             [message("cu1", None, "2024-12-03T14:00:01.000Z", "user"),
                              assistant("ca1", "cu1", "2024-12-03T14:00:02.000Z", None)],
                             session_id="sess-2")
        payload = json.loads(self.run_cli(
            "--parent", str(parent), "--child", str(child), "--children-complete",
            "--start-time", "2024-12-03T14:00:00.000Z",
            "--end-time", "2024-12-03T14:00:04.000Z").stdout)
        children = payload["child_attribution"]
        self.assertTrue(children["complete"])
        self.assertFalse(children["totals_known"], "declared scope must still respect usage completeness")
        self.assertIsNone(children["totals"])
        self.assertFalse(children["observed_totals"]["usage_complete"])
        self.assertIsNone(payload["totals"])
        self.assertFalse(payload["totals_known"])

    def test_null_required_counters_mark_incomplete_and_never_complete(self):
        usage = {"input": None, "output": None, "cacheRead": None, "cacheWrite": None,
                 "totalTokens": None, "reasoning": None, "cost": {}}
        entries = [message("u1", None, "2024-12-03T14:00:00.000Z", "user"),
                   assistant("a1", "u1", "2024-12-03T14:00:01.000Z", usage)]
        path = self.parent_session(entries)
        payload = json.loads(self.run_cli(
            "--parent", str(path), "--start-time", "2024-12-03T14:00:00.000Z",
            "--end-time", "2024-12-03T14:00:01.000Z").stdout)
        parent = payload["parent"]
        self.assertFalse(parent["usage_complete"], "null required counters are not complete usage")
        self.assertFalse(parent["cost_complete"], "a cost object of nulls is not complete cost")
        self.assertEqual(parent["usage_coverage"]["usage_objects_incomplete"], 1)
        self.assertEqual(parent["usage_coverage"]["cost_objects_incomplete"], 1)
        self.assertIsNone(parent["usage"]["reported_totalTokens"])
        self.assertIsNone(parent["usage"]["reasoning"])

    def test_missing_total_tokens_and_reasoning_are_unknown_not_zero(self):
        usage = {"input": 5, "output": 1, "cacheRead": 0, "cacheWrite": 0,
                 "cost": {"input": 0.1, "output": 0.1, "cacheRead": 0.0,
                          "cacheWrite": 0.0, "total": 0.2}}
        entries = [message("u1", None, "2024-12-03T14:00:00.000Z", "user"),
                   assistant("a1", "u1", "2024-12-03T14:00:01.000Z", usage)]
        path = self.parent_session(entries)
        payload = json.loads(self.run_cli(
            "--parent", str(path), "--start-time", "2024-12-03T14:00:00.000Z",
            "--end-time", "2024-12-03T14:00:01.000Z").stdout)
        parent = payload["parent"]
        self.assertTrue(parent["usage_complete"])
        self.assertEqual(parent["usage"]["total"], 6)
        self.assertIsNone(parent["usage"]["reported_totalTokens"], "unreported totalTokens is unknown")
        self.assertIsNone(parent["usage"]["reasoning"], "unreported reasoning is unknown")
        self.assertEqual(parent["usage_coverage"]["total_tokens_reported"], 0)
        self.assertEqual(parent["usage_coverage"]["reasoning_reported"], 0)

    def test_assistant_without_usage_is_incomplete_not_zero(self):
        entries = [message("u1", None, "2024-12-03T14:00:00.000Z", "user"),
                   assistant("a1", "u1", "2024-12-03T14:00:01.000Z", None),
                   message("u2", "a1", "2024-12-03T14:00:02.000Z", "user"),
                   assistant("a2", "u2", "2024-12-03T14:00:03.000Z", USAGE_1)]
        path = self.parent_session(entries)
        payload = json.loads(self.run_cli(
            "--parent", str(path), "--start-time", "2024-12-03T14:00:00.000Z",
            "--end-time", "2024-12-03T14:00:03.000Z").stdout)
        parent = payload["parent"]
        self.assertEqual(parent["usage"]["input"], 100)
        self.assertFalse(parent["usage_complete"])
        self.assertEqual(parent["usage_coverage"]["assistant_messages"], 2)
        self.assertEqual(parent["usage_coverage"]["assistant_usage_reported"], 1)
        self.assertTrue(any("observed subtotal" in note for note in payload["notes"]))
        self.assertFalse(payload["observed_totals"]["usage_complete"])
        self.assertIsNone(payload["totals"], "no complete total is claimed from incomplete usage")

    def test_no_reported_usage_stays_null_cost_and_incomplete(self):
        entries = [message("u1", None, "2024-12-03T14:00:00.000Z", "user"),
                   assistant("a1", "u1", "2024-12-03T14:00:01.000Z", None)]
        path = self.parent_session(entries)
        payload = json.loads(self.run_cli(
            "--parent", str(path), "--start-time", "2024-12-03T14:00:00.000Z",
            "--end-time", "2024-12-03T14:00:01.000Z").stdout)
        parent = payload["parent"]
        self.assertEqual(parent["usage"]["total"], 0)
        self.assertFalse(parent["usage_complete"], "a zero subtotal without usage must be marked incomplete")
        self.assertIsNone(parent["usage"]["reasoning"])
        self.assertIsNone(parent["cost"], "no reported usage means no cost data, not zero cost")
        self.assertFalse(parent["cost_complete"])
        self.assertEqual(parent["usage_coverage"]["usage_objects"], 0)

    def test_absent_cost_and_reasoning_are_null_not_zero(self):
        bare = {key: value for key, value in USAGE_1.items() if key not in ("cost", "reasoning")}
        entries = [message("u1", None, "2024-12-03T14:00:00.000Z", "user"),
                   assistant("a1", "u1", "2024-12-03T14:00:01.000Z", bare)]
        path = self.parent_session(entries)
        payload = json.loads(self.run_cli(
            "--parent", str(path), "--start-time", "2024-12-03T14:00:00.000Z",
            "--end-time", "2024-12-03T14:00:01.000Z").stdout)
        parent = payload["parent"]
        self.assertIsNone(parent["usage"]["reasoning"], "absent optional reasoning is not a measured zero")
        self.assertIsNone(parent["cost"], "absent cost is null, never inferred zero")
        self.assertFalse(parent["cost_complete"])
        self.assertEqual(parent["usage"]["input"], 100)
        self.assertTrue(parent["usage_complete"])
        self.assertTrue(any("cost stays null" in note for note in payload["notes"]))

    def test_missing_compaction_usage_is_coverage_gap_not_failure(self):
        entries = tree_entries()
        entries.append({"type": "compaction", "id": "k2", "parentId": "a2",
                        "timestamp": "2024-12-03T14:00:08.000Z", "summary": "SENTINEL-TRANSCRIPT",
                        "tokensBefore": 10})
        path = self.parent_session(entries)
        payload = json.loads(self.run_cli(
            "--parent", str(path), "--start-time", "2024-12-03T14:00:00.000Z",
            "--end-time", "2024-12-03T14:00:08.000Z").stdout)
        parent = payload["parent"]
        self.assertEqual(parent["compactions"], 2)
        self.assertEqual(parent["usage_coverage"]["compactions"], 2)
        self.assertEqual(parent["usage_coverage"]["compaction_usage_reported"], 1)
        self.assertTrue(parent["usage_complete"], "optional compaction usage is a gap, not a failure")

    def test_malformed_numeric_counters_rejected(self):
        base = {"input": 1, "output": 0, "cacheRead": 0, "cacheWrite": 0,
                "totalTokens": 1, "cost": {"total": 0.0}}
        cases = {
            "boolean input": {**base, "input": True},
            "fractional input": {**base, "input": 1.9},
            "negative input": {**base, "input": -1},
            "nan input": {**base, "input": float("nan")},
            "infinite input": {**base, "input": float("inf")},
            "negative cost": {**base, "cost": {"total": -0.1}},
            "nan cost": {**base, "cost": {"total": float("nan")}},
            "boolean cost": {**base, "cost": {"total": True}},
        }
        for label, usage in cases.items():
            with self.subTest(label=label):
                path = self.parent_session(
                    [message("u1", None, "2024-12-03T14:00:00.000Z", "user"),
                     assistant("a1", "u1", "2024-12-03T14:00:01.000Z", usage)])
                result = self.run_cli("--parent", str(path), "--start-time",
                                      "2024-12-03T14:00:00.000Z", "--end-time",
                                      "2024-12-03T14:00:01.000Z", ok=False)
                self.assertNotEqual(result.returncode, 0, label)
                self.assertIn("must", result.stderr)
        # A whole-valued float is a valid counter, not a fractional one.
        path = self.parent_session(
            [message("u1", None, "2024-12-03T14:00:00.000Z", "user"),
             assistant("a1", "u1", "2024-12-03T14:00:01.000Z", {**base, "input": 2.0})])
        payload = json.loads(self.run_cli(
            "--parent", str(path), "--start-time", "2024-12-03T14:00:00.000Z",
            "--end-time", "2024-12-03T14:00:01.000Z").stdout)
        self.assertEqual(payload["parent"]["usage"]["input"], 2)

    def test_cyclic_and_dangling_trees_fail_without_hanging(self):
        cases = {
            "self cycle": [message("a", "a", "2024-12-03T14:00:00.000Z", "user")],
            "two cycle": [message("a", "b", "2024-12-03T14:00:00.000Z", "user"),
                          message("b", "a", "2024-12-03T14:00:01.000Z", "user")],
            "dangling": [message("a", "missing", "2024-12-03T14:00:00.000Z", "user")],
            "non-string": [{"type": "message", "id": "a", "parentId": 5,
                            "timestamp": "2024-12-03T14:00:00.000Z",
                            "message": {"role": "user", "content": "x"}}],
        }
        for label, entries in cases.items():
            with self.subTest(label=label):
                path = self.parent_session(entries)
                result = self.run_cli("--parent", str(path), "--start-time",
                                      "2024-12-03T14:00:00.000Z", "--end-time",
                                      "2024-12-03T14:00:01.000Z", ok=False, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                with self.assertRaises(ValueError):
                    metrics.read_session(path)
        with self.assertRaises(ValueError):
            metrics.select_ancestry([{"id": "a", "parentId": "a"}], "a", "a")

    def test_linked_child_same_id_different_content_fails(self):
        base = [message("u1", None, "2024-12-03T14:00:00.000Z", "user"),
                assistant("a1", "u1", "2024-12-03T14:00:01.000Z", USAGE_1)]
        parent = session_file(self.sessions / "parent.jsonl", "/private/secret/project", base)
        changed = dict(USAGE_1, input=999)
        fork = session_file(self.sessions / "fork.jsonl", "/private/secret/project",
                            [base[0], assistant("a1", "u1", "2024-12-03T14:00:01.000Z", changed)],
                            session_id="sess-fork", parent_session=str(parent))
        result = self.run_cli("--parent", str(parent), "--child", str(fork),
                              "--start-time", "2024-12-03T14:00:00.000Z",
                              "--end-time", "2024-12-03T14:00:01.000Z", ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("structurally different", result.stderr.lower())

    def test_naive_timestamps_are_interpreted_as_utc(self):
        entries = [message("u1", None, "2024-12-03T14:00:00", "user"),
                   assistant("a1", "u1", "2024-12-03T14:00:01", USAGE_1)]
        path = self.parent_session(entries)
        payload = json.loads(self.run_cli(
            "--parent", str(path), "--start-time", "2024-12-03T13:59:00Z",
            "--end-time", "2024-12-03T14:00:30Z").stdout)
        self.assertEqual(payload["parent"]["selected_entries"], 2)
        self.assertTrue(any("UTC" in note for note in payload["notes"]))

    def test_assert_no_children_is_known_zero(self):
        path = self.parent_session()
        payload = json.loads(self.run_cli("--parent", str(path), "--start-entry", "u1",
                                          "--end-entry", "a2", "--assert-no-children").stdout)
        children = payload["child_attribution"]
        self.assertEqual(children["mode"], "none")
        self.assertTrue(children["totals_known"])
        self.assertEqual(children["totals"]["usage"]["input"], 0)
        self.assertEqual(payload["totals"]["usage"]["input"], 300)

    def test_explicit_child_totals_sum_with_parent(self):
        parent = self.parent_session()
        child = session_file(self.sessions / "child.jsonl", "/private/secret/project",
                             [message("cu1", None, "2024-12-03T14:00:01.000Z", "user"),
                              assistant("ca1", "cu1", "2024-12-03T14:00:02.000Z", USAGE_2)],
                             session_id="sess-2")
        payload = json.loads(self.run_cli(
            "--parent", str(parent), "--child", str(child), "--children-complete",
            "--start-time", "2024-12-03T14:00:00.000Z",
            "--end-time", "2024-12-03T14:00:04.000Z").stdout)
        children = payload["child_attribution"]
        self.assertEqual(children["mode"], "explicit")
        self.assertTrue(children["complete"])
        self.assertTrue(children["totals_known"])
        self.assertEqual(children["totals"]["usage"]["input"], 200)
        self.assertEqual(payload["totals"]["usage"]["input"], 500)
        self.assertEqual(len(payload["children"]), 1)

    def test_forked_child_history_is_not_double_counted(self):
        # A real fork copies the parent's entries verbatim and points at the source.
        base = [message("u1", None, "2024-12-03T14:00:00.000Z", "user"),
                assistant("a1", "u1", "2024-12-03T14:00:01.000Z", USAGE_1),
                message("u2", "a1", "2024-12-03T14:00:02.000Z", "user"),
                assistant("a2", "u2", "2024-12-03T14:00:03.000Z", USAGE_2)]
        parent = session_file(self.sessions / "parent.jsonl", "/private/secret/project", base,
                              session_id="sess-1")
        child = session_file(self.sessions / "fork.jsonl", "/private/secret/project",
                             base + [message("fu1", "a2", "2024-12-03T14:00:05.000Z", "user"),
                                     assistant("fa1", "fu1", "2024-12-03T14:00:06.000Z", USAGE_2)],
                             session_id="sess-fork", parent_session=str(parent))
        payload = json.loads(self.run_cli(
            "--parent", str(parent), "--child", str(child), "--children-complete",
            "--start-time", "2024-12-03T14:00:00.000Z",
            "--end-time", "2024-12-03T14:00:06.000Z").stdout)
        child_block = payload["children"][0]
        self.assertEqual(child_block["shared_history_entries_skipped"], 4)
        self.assertEqual(child_block["usage"]["input"], 200, "shared fork history must not be recounted")
        self.assertEqual(payload["totals"]["usage"]["input"], 500)

    def test_two_unrelated_clones_fail_instead_of_double_counting(self):
        parent = self.parent_session()
        clone = session_file(self.sessions / "clone.jsonl", "/private/secret/project",
                             tree_entries(), session_id="sess-clone")
        result = self.run_cli("--parent", str(parent), "--child", str(clone),
                              "--start-time", "2024-12-03T14:00:00.000Z",
                              "--end-time", "2024-12-03T14:00:06.000Z", ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("double", result.stderr.lower())

    def test_malformed_and_missing_boundaries_fail_clearly(self):
        path = self.parent_session()
        cases = [
            ("missing file", ["--parent", str(self.sessions / "nope.jsonl"),
                              "--start-entry", "u1", "--end-entry", "a2"]),
            ("no boundaries", ["--parent", str(path)]),
            ("mixed boundaries", ["--parent", str(path), "--start-entry", "u1",
                                  "--end-time", "2024-12-03T14:10:00.000Z"]),
            ("unknown boundary", ["--parent", str(path), "--start-entry", "zz",
                                  "--end-entry", "a2"]),
            ("different branches", ["--parent", str(path), "--start-entry", "u3",
                                    "--end-entry", "a2"]),
            ("no parent", ["--start-entry", "u1", "--end-entry", "a2"]),
            ("assert and child", ["--parent", str(path), "--assert-no-children",
                                  "--child", str(path), "--start-entry", "u1", "--end-entry", "a2"]),
            ("entry bounds with child", ["--parent", str(path), "--child", str(path),
                                         "--start-entry", "u1", "--end-entry", "a2"]),
        ]
        for label, args in cases:
            with self.subTest(label=label):
                result = self.run_cli(*args, ok=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(result.stderr.strip())

    def test_malformed_json_and_tree_inputs_fail_clearly(self):
        bad_json = self.sessions / "bad.jsonl"
        bad_json.write_text('{"type":"session","version":3,"id":"x","timestamp":"t","cwd":"/c"}\nnot json\n')
        missing_header = self.sessions / "header.jsonl"
        missing_header.write_text('{"type":"message","id":"a","parentId":null,"timestamp":"t","message":{}}\n')
        flat = self.sessions / "flat.jsonl"
        flat.write_text(json.dumps({"type": "session", "version": 1, "id": "x", "timestamp": "t", "cwd": "/c"}) + "\n"
                        + json.dumps({"type": "message", "message": {"role": "user", "content": "x"}}) + "\n")
        duplicate = self.sessions / "dup.jsonl"
        duplicate.write_text("".join(json.dumps(item) + "\n" for item in [
            {"type": "session", "version": 3, "id": "x", "timestamp": "t", "cwd": "/c"},
            message("a", None, "2024-12-03T14:00:00.000Z", "user"),
            message("a", None, "2024-12-03T14:00:01.000Z", "user"),
        ]))
        for path in (bad_json, missing_header, flat, duplicate):
            with self.subTest(path=path.name):
                result = self.run_cli("--parent", str(path), "--start-time",
                                      "2024-12-03T00:00:00.000Z", "--end-time",
                                      "2024-12-04T00:00:00.000Z", ok=False)
                self.assertNotEqual(result.returncode, 0)

    def test_output_has_no_transcript_or_private_paths(self):
        path = self.parent_session()
        text = self.run_cli("--parent", str(path), "--start-entry", "u1",
                            "--end-entry", "a2").stdout
        self.assertNotIn("SENTINEL-TRANSCRIPT", text)
        self.assertNotIn("/private/secret", text)
        self.assertNotIn(str(self.sessions), text)
        payload = json.loads(text)
        self.assertEqual(payload["parent"]["session_id"], "sess-1")
        self.assertIn("not billed", payload["cost_basis"].lower())
        self.assertIsNone(payload["parent"]["provider_wait_seconds"])
        self.assertIsNone(payload["parent"]["user_corrections"])

    def test_module_rejects_bounds_without_a_matching_ancestry(self):
        path = self.parent_session()
        session = metrics.read_session(path)
        with self.assertRaises(ValueError):
            metrics.select_ancestry(session["entries"], "u3", "a2")
        with self.assertRaises(ValueError):
            metrics.select_ancestry(session["entries"], "zz", "a2")
        with self.assertRaises(ValueError):
            metrics.select_ancestry([{"id": "a", "parentId": "a"}], "a", "a")
        with self.assertRaises(ValueError):
            metrics.select_ancestry([{"id": "a", "parentId": "missing"}], "a", "a")


if __name__ == "__main__":
    unittest.main()

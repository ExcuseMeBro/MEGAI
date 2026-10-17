#!/usr/bin/env python3
"""Offline regression checks for paired Pi benchmark measurement."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess

SPEC = importlib.util.spec_from_file_location("routing_bench", Path(__file__).resolve().parents[1] / "benchmark/pi-routing/run.py")
bench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bench)


def message(**kwargs):
    return {"role": "assistant", "provider": "deepseek", "model": "deepseek-flash", "stopReason": "stop",
            "usage": {"input": 10, "output": 4, "cacheRead": 20, "cacheWrite": 2,
                      "reasoning": 3, "totalTokens": 36, "cost": {"total": 0.01}},
            "content": [{"type": "text", "text": "READY"}], **kwargs}


def stream(*events):
    return "\n".join(json.dumps(e) for e in events)


class Accounting(unittest.TestCase):
    def test_final_message_counted_once_not_turn_or_stream_updates(self):
        m = message()
        result = bench.parse_events(stream({"type": "message_update", "usage": m["usage"]},
                                          {"type": "message_end", "message": m},
                                          {"type": "turn_end", "message": m},
                                          {"type": "agent_end", "messages": [m]}))
        self.assertEqual(result["requests"], 1)
        self.assertEqual(result["usage"]["total"], 36)
        self.assertEqual(result["usage"]["cache_read"], 20)
        self.assertEqual(result["usage"]["cache_write"], 2)
        self.assertEqual(result["usage"]["reasoning"], 3)
        self.assertTrue(result["complete_usage"])

    def test_compaction_and_non_chat_usage_included(self):
        m = message()
        result = bench.parse_events(stream({"type": "message_end", "message": m},
                   {"type": "compaction_end", "result": {"usage": m["usage"]}},
                   {"type": "entry_appended", "entry": {"type": "usage", "usage": m["usage"]}}))
        self.assertEqual(result["usage"]["total"], 108)

    def test_missing_usage_not_reported_as_complete(self):
        result = bench.parse_events(stream({"type": "message_end", "message": message(usage={})}))
        self.assertFalse(result["complete_usage"])
        self.assertFalse(bench.parse_events("")["complete_usage"])

    def test_unicode_line_separator_does_not_break_jsonl(self):
        m = message(content=[{"type": "text", "text": "a\u2028b"}])
        self.assertEqual(bench.parse_events(json.dumps({"type": "message_end", "message": m}, ensure_ascii=False))["final"], "a\u2028b")

    def test_provider_error_not_success_even_exit_zero(self):
        result = bench.parse_events(stream({"type": "message_end", "message": message(stopReason="error", errorMessage="402 Insufficient Balance")}))
        result.update(model=bench.DEEPSEEK, exit=0, identity_ok=True)
        self.assertFalse(bench.stage_ok(result))
        self.assertTrue(bench.balance_error(result))
        result["errors"] = ["401 Unauthorized", "429 quota", "402 other"]
        self.assertFalse(bench.balance_error(result))
        result["errors"] = ["402 Insufficient Balance"]
        result["model"] = bench.GPT
        self.assertFalse(bench.balance_error(result))

    def test_aggregate_includes_ready_worker_review_and_fallback(self):
        stage = bench.parse_events(stream({"type": "message_end", "message": message()}))
        self.assertEqual(bench.aggregate([stage] * 5)["total"], 180)
        self.assertEqual(bench.aggregate([stage] * 5)["cost_usd"], 0.05)

    def test_native_identity_requires_exact_model_and_thinking(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "session.jsonl").write_text(stream(
                {"type": "model_change", "provider": "deepseek", "modelId": "deepseek-flash"},
                {"type": "thinking_level_change", "thinkingLevel": "high"}))
            self.assertTrue(bench.native_identity(root, bench.DEEPSEEK, "high"))
            self.assertFalse(bench.native_identity(root, bench.DEEPSEEK, "medium"))
            self.assertFalse(bench.native_identity(root, bench.GPT, "high"))

    def test_evaluation_uses_frozen_test_not_candidate_test(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate"
            candidate.mkdir()
            (candidate / "intervals.py").write_text("def merge_intervals(items): return items\n")
            (candidate / "test_acceptance.py").write_text("# Participant tried to remove evaluator assertions\n")
            tests = b'import unittest\nfrom intervals import merge_intervals\nclass Test(unittest.TestCase):\n def test_merge(self): self.assertEqual(merge_intervals([(1,3),(2,4)]), [(1,4)])\n'
            result = bench.evaluate(candidate, root / "evaluation", "bugfix", tests)
            self.assertFalse(result["passed"])
            self.assertEqual(result["tests"], 1)
            self.assertEqual(result["test_sha256"], bench.digest(tests))

    def test_evaluator_timeout_is_a_retained_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate"
            candidate.mkdir()
            (candidate / "intervals.py").write_text("def merge_intervals(items):\n while True: pass\n")
            with patch.object(bench.subprocess, "run", side_effect=subprocess.TimeoutExpired(["python3"], 30)):
                result = bench.evaluate(candidate, root / "evaluation", "bugfix", b"# frozen tests\n")
            self.assertTrue(result["timed_out"])
            self.assertFalse(result["passed"])
            self.assertTrue((root / "evaluation/receipt.json").is_file())

    def test_review_event_drift_invalidates_matrix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bench.save(root / "manifest.json", {"repeats": 1})
            frozen = b"# immutable acceptance\n"
            for task, module in bench.MODULES.items():
                for arm in bench.ARMS:
                    trial = root / f"r1-{task}-{arm}"
                    candidate = trial / "candidate"
                    candidate.mkdir(parents=True)
                    (candidate / module).write_text("# candidate\n")
                    stages, paths = [], []
                    for role in ("worker", "reviewer"):
                        session = trial / role / "sessions"
                        session.mkdir(parents=True)
                        (session / "native.jsonl").write_text(stream(
                            {"type": "model_change", "provider": "deepseek", "modelId": "deepseek-flash"},
                            {"type": "thinking_level_change", "thinkingLevel": "high"}))
                        for phase in ("ready", "task"):
                            directory = trial / role / phase
                            directory.mkdir()
                            events = stream({"type": "message_end", "message": message(content=[{"type": "text", "text": "READY" if phase == "ready" else "PASS"}])})
                            (directory / "events.jsonl").write_text(events)
                            stage = bench.parse_events(events)
                            stage.update(model=bench.DEEPSEEK, thinking="high", seconds=1, exit=0, identity_ok=True)
                            bench.save(directory / "receipt.json", stage)
                            stages.append(stage)
                            paths.append(str((directory / "receipt.json").relative_to(root)))
                    evaluation = dict(exit=0, tests=1, passed=True, seconds=0.01,
                                      test_sha256=bench.digest(frozen), module_sha256=bench.digest(b"# candidate\n"))
                    (trial / "evaluation").mkdir()
                    bench.save(trial / "evaluation/receipt.json", evaluation)
                    bench.save(trial / "result.json", dict(arm=arm, task=task, repeat=1, seconds=5,
                        usage=bench.aggregate(stages), complete_usage=True, acceptance=evaluation,
                        review_pass=True, scope_ok=True, fallback=False, pass_trial=True, stage_paths=paths))
            with patch.object(bench, "baseline_file", return_value=frozen):
                bench.verify(root)
                events = root / "r1-feature-deepseek-gpt/reviewer/task/events.jsonl"
                events.write_text(stream({"type": "message_end", "message": message(content=[{"type": "text", "text": "FAIL"}])}))
                with self.assertRaisesRegex(AssertionError, "evidence drift"):
                    bench.verify(root)

    def test_incomplete_matrix_cannot_pass_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bench.save(root / "manifest.json", {"repeats": 3})
            with self.assertRaisesRegex(AssertionError, "incomplete paired matrix"):
                bench.verify(root)


if __name__ == "__main__":
    unittest.main()

"""Focused offline checks for the pilot's evaluator and event accounting."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("golden_runner", HERE / "run.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class GoldenPilotTests(unittest.TestCase):
    def test_seeds_pass_frozen_and_fail_held_out_golden(self):
        for case in runner.CASES:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                module = HERE / "fixtures" / f"{case}.py"
                normal = runner.check(module, runner.frozen(case), Path(tmp) / "frozen")
                hidden = runner.check(module, (HERE / "golden" / f"{case}.py").read_bytes(),
                                      Path(tmp) / "golden")
                self.assertTrue(normal["passed"])
                self.assertFalse(hidden["passed"])
                self.assertEqual(hidden["tests"], 2)
                self.assertEqual(hidden["output_sha256"],
                                 runner.sha((Path(tmp) / "golden" / "output.txt").read_bytes()))
                self.assertNotEqual(normal["test_sha256"], hidden["test_sha256"])

    def test_event_usage_requires_assistant_usage_and_actual_stop(self):
        event = {"type": "message_end", "message": {"role": "assistant", "provider": "openai-codex",
                 "model": "gpt-6-sol", "stopReason": "stop", "content": [{"type": "text", "text": "READY"}],
                 "usage": {"input": 3, "output": 2, "cacheRead": 1, "cacheWrite": 0,
                           "totalTokens": 6, "cost": {"total": 0.002}}}}
        parsed = runner.events(json.dumps(event))
        self.assertTrue(parsed["complete_usage"])
        self.assertEqual(parsed["usage"]["total"], 6)
        self.assertEqual(parsed["final"], "READY")
        event["message"].pop("usage")
        self.assertFalse(runner.events(json.dumps(event))["complete_usage"])
        self.assertFalse(runner.events("invalid JSON")["complete_usage"])

    def test_evaluator_does_not_trust_candidate_test_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = root / "candidate"
            candidate.mkdir()
            (candidate / "intervals.py").write_text("def merge_intervals(intervals): return []\n")
            (candidate / "test_acceptance.py").write_text("raise AssertionError('candidate-controlled')\n")
            receipt = runner.check(candidate / "intervals.py", runner.frozen("intervals"), root / "grade")
            self.assertFalse(receipt["passed"])
            self.assertEqual(receipt["tests"], 10)
            self.assertNotIn("candidate-controlled", (root / "grade" / "output.txt").read_text())


if __name__ == "__main__":
    unittest.main()

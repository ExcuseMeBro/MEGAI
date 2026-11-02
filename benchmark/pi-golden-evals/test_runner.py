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
    def test_seeds_and_clean_controls_have_expected_held_out_status(self):
        for case in (*runner.COHORTS["pilot"], *runner.COHORTS["validation"]):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                module = runner.seed(case)
                normal = runner.check(module, runner.frozen(case), Path(tmp) / "frozen")
                hidden = runner.check(module, runner.golden(case), Path(tmp) / "golden")
                self.assertTrue(normal["passed"])
                self.assertEqual(hidden["passed"], runner.clean(case))
                self.assertEqual(hidden["tests"], 2)
                self.assertEqual(hidden["output_sha256"],
                                 runner.sha((Path(tmp) / "golden" / "output.txt").read_bytes()))
                self.assertNotEqual(normal["test_sha256"], hidden["test_sha256"])
                self.assertEqual(runner.source_hashes(case)["seed"], runner.sha(module.read_bytes()))

    def test_validation_contract_does_not_rewrite_pilot_contract(self):
        self.assertEqual(tuple(runner.CASES), runner.COHORTS["pilot"])
        self.assertNotEqual(runner.contract("query"), runner.contract("intervals"))
        self.assertEqual(runner.frozen("intervals"), runner.frozen("intervals-clean"))
        self.assertEqual(runner.golden("batching"), runner.golden("batching-clean"))

    def test_validation_summary_separates_repairs_from_clean_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = []
            for arm in runner.ARMS:
                for case in runner.COHORTS["validation"]:
                    rows.append({"case": case, "arm": arm, "kind": "clean" if runner.clean(case) else "defect",
                                 "changed": not runner.clean(case), "pass_trial": True,
                                 "frozen": {"passed": True}, "golden": {"passed": True},
                                 "pipeline_seconds": 1, "usage": {"total": 2, "cost_usd": 0.01}})
            runner.summarize(Path(tmp), rows, 1, "validation")
            report = (Path(tmp) / "summary.md").read_text()
            self.assertIn("Clean unchanged", report)
            self.assertIn("1/1 | 2/2 | 0 | 3/3", report)
            self.assertIn("not a production TNR", report)

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

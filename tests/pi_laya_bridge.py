#!/usr/bin/env python3
"""Offline wire and validation tests for the on-device Pi Laya bridge."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "pi-skill/laya/bridge.py"


def module():
    spec = importlib.util.spec_from_file_location("pi_laya_bridge", BRIDGE)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.bridge = module()
        self.questions = {
            "route": {"type": "choice", "instructions": "Choose", "criteria": {"a": "first", "b": "second"}},
            "quality": {"type": "score", "instructions": "Rate", "criteria": ["bad", "good"]},
            "approved": {"type": "noul", "instructions": "Is approved?", "criteria": {"false": "no", "true": "yes"}},
        }

    def test_request_rejects_malformed_and_oversized_without_model(self):
        for state, questions in (("ok", {}), ("ok", {"bad": {"type": "choice", "instructions": "", "criteria": {"a": None}}}),
                                 ("x" * 30000, self.questions),
                                 ("ok", {"n": {"type": "noul", "instructions": "test", "criteria": {"garbage": "bad"}}}),
                                 ("ok", {"n": {"type": "noul", "instructions": "test", "labels": {"false": "no", "true": "yes"}}})):
            with self.subTest(state=state[:8], questions=tuple(questions)):
                with self.assertRaises(ValueError):
                    self.bridge.validate_request({"state": state, "questions": questions})

    def test_full_token_preflight_rejects_state_and_head_that_upstream_would_truncate(self):
        class Tokenizer:
            mask_token = "[MASK]"
            def __call__(self, text, **_):
                return {"input_ids": text.split()}
        class Agent:
            tok = Tokenizer()
            cfg = {"max_len": 85, "head_max_len": 48}
        self.bridge.preflight(Agent(), "short state", {"n": self.questions["approved"]})
        with self.assertRaisesRegex(ValueError, "context|token|length"):
            self.bridge.preflight(Agent(), "word " * 80, {"n": self.questions["approved"]})
        with self.assertRaisesRegex(ValueError, "context|token|length"):
            self.bridge.preflight(Agent(), "ok", {"n": {"type": "noul", "instructions": "word " * 80}})

    def test_bounded_stdio_test_backend_and_eof(self):
        request = {"id": 1, "state": "ordinary local question", "questions": self.questions}
        result = subprocess.run([sys.executable, str(BRIDGE)], input=json.dumps(request) + "\n",
                                text=True, capture_output=True, timeout=8,
                                env={**os.environ, "LAYA_BRIDGE_TEST": "1", "HF_HUB_OFFLINE": "1"})
        self.assertEqual(result.returncode, 0, result.stderr)
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["id"], 1)
        answers = replies[0]["result"]["answers"]
        self.assertEqual({key: val["type"] for key, val in answers.items()},
                         {key: val["type"] for key, val in self.questions.items()})
        self.assertEqual(replies[0]["result"]["routing"]["model"], "multilingual")
        self.assertNotIn("api.typesafe.ai", result.stdout + result.stderr)

    def test_invalid_output_and_message_limit_fail_locally(self):
        with self.assertRaisesRegex(ValueError, "answer|probab"):
            self.bridge.validate_output({"answers": {"route": {"type": "choice", "choice": "outside", "probabilities": {"a": 1.0}}}},
                                        {"route": self.questions["route"]})
        with self.assertRaisesRegex(ValueError, "answer|probab"):
            self.bridge.validate_output({"answers": {"approved": {"type": "noul", "noul": float("nan")}}},
                                        {"approved": self.questions["approved"]})
        result = subprocess.run([sys.executable, str(BRIDGE)], input="x" * 300000 + "\n",
                                text=True, capture_output=True, timeout=8,
                                env={**os.environ, "LAYA_BRIDGE_TEST": "1"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout.splitlines()[0]).get("ok", True))


if __name__ == "__main__":
    unittest.main()

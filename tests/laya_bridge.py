#!/usr/bin/env python3
"""Protocol tests for the local Laya stdio bridge (`pi-skill/laya/bridge.py`).

The bridge is the only place the Pi extension talks to the model, so its contract is
pinned here without torch: a fake `laya` module (tests/fixtures/laya_fake) is placed on
the child's `PYTHONPATH` and answers from a script file. Covered: one JSON object per
line in and out, typed pass-through with routing metadata, stdout that stays pure
JSONL, one router and one load per routed checkpoint with a two-slot cap, explicit
English/multilingual routing by language hint with `LAYA_LANG` only as a fallback,
`typed-decisions` that is never selected or loaded, malformed and invalid input that
does not kill the service, bounded inference errors that do, `--check` for the
installer's verification step, and clean exit on EOF and SIGTERM.
"""
from __future__ import annotations

import json
import os
import select
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "pi-skill/laya/bridge.py"
FAKE = ROOT / "tests/fixtures/laya_fake"
KEPT = ("LAYA_DEVICE", "LAYA_LANG", "LAYA_PYTHON", "LAYA_LOG", "HF_TOKEN")

MIXED = {
    "task_type": {"type": "choice", "instructions": "Which type?", "criteria": {"bug": "a defect", "chore": None}},
    "effort": {"type": "score", "instructions": "How much of the repo?", "criteria": ["one file", "few files"]},
    "needs_approval": {"type": "noul", "instructions": "Is this reserved?", "criteria": {"true": "push to main", "false": "ordinary"}},
}
ENGLISH_STATE = "The task is a routine documentation fix in one file."
UZBEK_STATE = "Vazifa bitta fayldagi oddiy hujjat tuzatishi."  # Latin script, like real Uzbek


def environment(work: Path, **env: str) -> dict[str, str]:
    """The child environment: the fake runtime on PYTHONPATH, plus any override."""
    base = {key: value for key, value in os.environ.items() if not key.startswith("LAYA_")}
    return {
        **base,
        "PYTHONPATH": str(FAKE),
        "PYTHONDONTWRITEBYTECODE": "1",
        "LAYA_FAKE_LOADS": str(work / "loads.jsonl"),
        "LAYA_FAKE_CALLS": str(work / "calls.jsonl"),
        "LAYA_FAKE_ROUTERS": str(work / "routers.jsonl"),
        "LAYA_FAKE_SCRIPT": str(work / "script.jsonl"),
        **env,
    }


class Bridge:
    """One bridge child, addressed over its real stdin/stdout pipes."""

    def __init__(self, work: Path, argv: tuple[str, ...] = (), **env: str):
        self.work = work
        self.loads = work / "loads.jsonl"
        self.calls = work / "calls.jsonl"
        self.routers = work / "routers.jsonl"
        self.script = work / "script.jsonl"
        self.environment = environment(work, **env)
        self.argv = [sys.executable, "-B", str(BRIDGE), *argv]
        self.proc = subprocess.Popen(
            self.argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, cwd=work, env=self.environment,
        )

    def send(self, payload: dict) -> None:
        self.send_raw(json.dumps(payload))

    def send_raw(self, line: str) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

    def ask(self, request_id: str, state: str = ENGLISH_STATE, questions: dict | None = None, **extra) -> dict:
        self.send({"id": request_id, "state": state, "questions": questions or MIXED, **extra})
        return self.receive()

    def receive(self, timeout: float = 30.0) -> dict:
        assert self.proc.stdout is not None
        ready, _, _ = select.select([self.proc.stdout], [], [], timeout)
        assert ready, f"the bridge answered nothing within {timeout}s"
        line = self.proc.stdout.readline()
        assert line.strip(), "the bridge closed stdout instead of answering"
        payload = json.loads(line)
        assert isinstance(payload, dict)
        return payload

    def raw_lines(self, timeout: float = 1.0) -> list[str]:
        """Every remaining stdout line, so the protocol channel can be inspected."""
        assert self.proc.stdout is not None
        lines: list[str] = []
        while select.select([self.proc.stdout], [], [], timeout)[0]:
            line = self.proc.stdout.readline()
            if not line:
                break
            lines.append(line)
        return lines

    def directives(self, *rows: dict) -> None:
        self.script.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def rows(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def stop(self, sig: int | None = None) -> None:
        if self.proc.poll() is not None:
            return
        if sig is not None:
            self.proc.send_signal(sig)
        else:
            self.proc.kill()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - a hang is the failure
            self.proc.kill()


class BridgeProtocol(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="laya-bridge-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.saved = {key: os.environ.get(key) for key in KEPT}
        for key in KEPT:
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def start(self, argv: tuple[str, ...] = (), **env: str) -> Bridge:
        bridge = Bridge(self.work, argv, **env)
        self.addCleanup(bridge.stop)
        return bridge

    def test_mixed_request_returns_typed_answers_on_a_clean_channel(self) -> None:
        bridge = self.start(LAYA_FAKE_LOAD_NOISE="tokenizer fixup")
        bridge.directives({"noise": "model chatter on stdout"})
        reply = bridge.ask("call-1")
        self.assertEqual(reply["id"], "call-1")
        self.assertTrue(reply["ok"], reply)
        self.assertEqual(reply["route"], "english")
        self.assertEqual(reply["model"], "convaiinnovations/laya")
        self.assertIsNone(reply["lang"])
        self.assertEqual(reply["usage"]["output_tokens"], 0)
        self.assertIn("english", reply["reason"].lower())
        answers = reply["answers"]
        self.assertEqual(answers["task_type"]["choice"], "bug")
        self.assertEqual(answers["task_type"]["probabilities"]["bug"], 0.9)
        self.assertEqual(answers["effort"]["type"], "score")
        self.assertIn("legend", answers["effort"])
        self.assertEqual(answers["needs_approval"]["noul"], 0.05)
        # The load warning and the model's own stdout line must not reach the protocol
        # channel: every line out of the bridge is one JSON response.
        for line in bridge.raw_lines():
            json.loads(line)

    def test_one_router_and_one_process_serve_many_requests(self) -> None:
        bridge = self.start()
        first = bridge.ask("a", ENGLISH_STATE)
        second = bridge.ask("b", "second", {"q": {"type": "noul", "instructions": "why"}})
        self.assertEqual([first["id"], second["id"]], ["a", "b"])
        self.assertEqual(bridge.rows(bridge.routers), [{
            "pid": bridge.proc.pid, "device": None, "max_loaded": 2,
            "auto_task_detection": False, "default": "english", "preload": False,
        }], "one two-slot router, built once, without workflow detection")
        self.assertEqual([row["model"] for row in bridge.rows(bridge.loads)], ["english"],
                         "the checkpoint is loaded once")
        self.assertEqual([row["state"] for row in bridge.rows(bridge.calls)], [ENGLISH_STATE, "second"])
        self.assertEqual(bridge.rows(bridge.calls)[0]["questions"], MIXED)
        self.assertEqual({row["pid"] for row in bridge.rows(bridge.calls)}, {bridge.proc.pid})

    def test_alternating_languages_never_reload_a_checkpoint(self) -> None:
        bridge = self.start()
        bridge.ask("en-1", ENGLISH_STATE)
        bridge.ask("uz-1", UZBEK_STATE, **{"lang": "uz"})
        bridge.ask("en-2", ENGLISH_STATE)
        uz = bridge.ask("uz-2", UZBEK_STATE, **{"lang": "uz"})
        calls = bridge.rows(bridge.calls)
        self.assertEqual([call["route"] for call in calls], ["english", "multilingual", "english", "multilingual"])
        self.assertEqual([call["lang"] for call in calls], [None, "uz", None, "uz"])
        self.assertEqual(uz["route"], "multilingual")
        self.assertEqual(uz["lang"], "uz")
        self.assertEqual(uz["model"], "convaiinnovations/laya:multilingual")
        self.assertIn("lang='uz'", uz["reason"])
        loads = bridge.rows(bridge.loads)
        self.assertEqual(sorted(row["model"] for row in loads), ["english", "multilingual"],
                         "each routed checkpoint loads exactly once")
        self.assertEqual({row["pid"] for row in loads}, {bridge.proc.pid},
                         "both checkpoints live in the one bridge process")

    def test_laya_lang_is_only_a_fallback_and_explicit_lang_wins(self) -> None:
        fallback = self.start(LAYA_LANG="uz")
        hinted = fallback.ask("auto", UZBEK_STATE)
        self.assertEqual(hinted["route"], "multilingual")
        self.assertEqual(hinted["lang"], "uz")
        self.assertEqual(fallback.ask("en", UZBEK_STATE, **{"lang": "en"})["route"], "english",
                         "an explicit hint beats LAYA_LANG")

        plain = self.start()
        self.assertEqual(plain.ask("auto", UZBEK_STATE)["route"], "english",
                         "Latin-script Uzbek is detected as English, which is why the hint exists")
        self.assertEqual(plain.ask("uz", UZBEK_STATE, **{"lang": "uz"})["route"], "multilingual")

    def test_an_unsupported_route_request_cannot_reach_typed_decisions(self) -> None:
        bridge = self.start()
        reply = bridge.ask("typed", ENGLISH_STATE, MIXED, model="typed-decisions")
        self.assertTrue(reply["ok"], "an unknown request field is ignored, not obeyed")
        self.assertEqual(reply["route"], "english")
        self.assertEqual([row["model"] for row in bridge.rows(bridge.loads)], ["english"],
                         "typed-decisions is never loaded, whatever a caller asks for")

    def test_malformed_and_invalid_input_are_rejected_without_stopping_serving(self) -> None:
        bridge = self.start()
        cases = (
            "not json at all",
            "[1, 2, 3]",
            json.dumps({"id": "x", "state": "", "questions": MIXED}),
            json.dumps({"id": "x", "state": "s", "questions": {}}),
            json.dumps({"id": "x", "state": "s", "questions": {f"q{i}": {"type": "noul", "instructions": "i"} for i in range(9)}}),
            json.dumps({"id": "x", "state": "s", "questions": {"q": {"type": "guess", "instructions": "i"}}}),
            json.dumps({"id": "x", "state": "s", "questions": {"q": {"type": "noul", "instructions": ""}}}),
            json.dumps({"id": "x", "state": "s", "questions": {"q": {"type": "score", "instructions": "i"}}}),
            json.dumps({"id": "x", "state": "s", "questions": {"q": {"type": "noul", "instructions": "i"}}, "lang": "not a lang!"}),
            json.dumps({"id": "x", "state": "s", "questions": {"q": {"type": "noul", "instructions": "i"}}, "lang": "u" * 40}),
            json.dumps({"id": "x", "state": "s", "questions": {"q": {"type": "noul", "instructions": "i"}}, "lang": 3}),
            json.dumps({"id": "bad id", "state": "s", "questions": {"q": {"type": "noul", "instructions": "i"}}}),
            json.dumps({"id": "x", "state": "s" * 30_000, "questions": {"q": {"type": "noul", "instructions": "i"}}}),
        )
        for payload in cases:
            with self.subTest(payload=payload[:60]):
                bridge.send_raw(payload)
                reply = bridge.receive()
                self.assertFalse(reply["ok"])
                self.assertTrue(reply["error"])
                self.assertLessEqual(len(reply["error"]), 400)
        self.assertEqual(bridge.rows(bridge.calls), [], "an invalid request never reaches the model")
        bridge.send({"id": "ok", "state": "s", "questions": {"q": {"type": "noul", "instructions": "why"}}})
        self.assertTrue(bridge.receive()["ok"], "one bad request must not stop the bridge")

    def test_answers_are_sanitized_to_the_requested_questions(self) -> None:
        bridge = self.start()
        bridge.directives({
            "answers": {
                "q": {"type": "noul", "noul": 0.9, "confidence": 0.9, "secret": "leak"},
                "planted": {"type": "noul", "noul": 0.5},
            },
            "extra_answers": {"planted": {"type": "noul", "noul": 0.5}},
        })
        reply = bridge.ask("call", "s", {"q": {"type": "noul", "instructions": "why"}})
        self.assertEqual(list(reply["answers"]), ["q"], "an answer nobody asked for is dropped")
        self.assertNotIn("secret", json.dumps(reply))

    def test_an_unusable_answer_is_an_inference_failure(self) -> None:
        bridge = self.start()
        bridge.directives({"answers": {"q": {"type": "noul"}}})
        reply = bridge.ask("empty", "s", {"q": {"type": "noul", "instructions": "why"}})
        self.assertFalse(reply["ok"])
        self.assertIn("inference failed", reply["error"])
        bridge.directives({"answers": {"q": {"type": "noul", "noul": 0.2}}})
        self.assertTrue(bridge.ask("next", "s", {"q": {"type": "noul", "instructions": "why"}})["ok"],
                        "an unusable answer must not kill the service")

    def test_inference_error_is_bounded_and_the_process_survives(self) -> None:
        bridge = self.start()
        bridge.directives({"error": "x" * 5_000})
        reply = bridge.ask("boom", "s", {"q": {"type": "noul", "instructions": "why"}})
        self.assertFalse(reply["ok"])
        self.assertLessEqual(len(reply["error"]), 400, "an error must stay bounded")
        self.assertIn("inference failed", reply["error"])
        self.assertNotIn("x" * 500, reply["error"])
        bridge.directives({"answers": {"q": {"type": "noul", "noul": 0.2}}})
        self.assertTrue(bridge.ask("next", "s", {"q": {"type": "noul", "instructions": "why"}})["ok"],
                        "a failed inference must not kill the service")

    def test_device_reaches_the_router(self) -> None:
        bridge = self.start(LAYA_DEVICE="cpu")
        bridge.ask("a", ENGLISH_STATE)
        self.assertEqual(bridge.rows(bridge.routers)[0]["device"], "cpu")
        self.assertEqual(bridge.rows(bridge.loads)[0]["pid"], bridge.proc.pid,
                         "the checkpoint loads inside the bridge child")

    def test_a_crashing_process_is_visible_to_the_caller(self) -> None:
        bridge = self.start()
        bridge.directives({"exit": 7})
        bridge.send({"id": "die", "state": "s", "questions": {"q": {"type": "noul", "instructions": "why"}}})
        self.assertEqual(bridge.proc.wait(timeout=30), 7)

    def test_eof_and_sigterm_stop_the_process(self) -> None:
        bridge = self.start()
        bridge.ask("a", "s", {"q": {"type": "noul", "instructions": "why"}})
        assert bridge.proc.stdin is not None
        bridge.proc.stdin.close()
        self.assertEqual(bridge.proc.wait(timeout=30), 0, "closing stdin ends the bridge")

        second = self.start()
        time.sleep(0.5)
        second.stop(signal.SIGTERM)
        self.assertIsNotNone(second.proc.poll(), "SIGTERM must end the bridge")

    def test_check_mode_preloads_both_routes_and_reports_failure(self) -> None:
        good = subprocess.run(
            [sys.executable, "-B", str(BRIDGE), "--check"],
            capture_output=True, text=True, cwd=self.work, timeout=60,
            env=environment(self.work),
        )
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertIn("english=convaiinnovations/laya", good.stdout)
        self.assertIn("multilingual=convaiinnovations/laya:multilingual", good.stdout)
        self.assertNotIn("typed-decisions", good.stdout)
        self.assertEqual([line for line in good.stderr.splitlines() if line.startswith("laya: loaded")],
                         ["laya: loaded english=convaiinnovations/laya",
                          "laya: loaded multilingual=convaiinnovations/laya:multilingual"])

        bad = subprocess.run(
            [sys.executable, "-B", str(BRIDGE), "--check"],
            capture_output=True, text=True, cwd=self.work, timeout=60,
            env=environment(self.work, LAYA_FAKE_LOAD_ERROR="checkpoint is unreadable"),
        )
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("checkpoint is unreadable", bad.stderr)


if __name__ == "__main__":
    unittest.main()

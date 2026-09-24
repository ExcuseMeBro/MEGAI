#!/usr/bin/env python3
"""megai-laya-current-0.3.20: offline JSON-lines bridge for pinned inference.

Stdout is protocol only. No network fallback or background listener; stdin EOF exits.
"""
from __future__ import annotations

import json
import math
import os
import sys

MODEL = "multilingual"
VERSION = "0.3.20"
MAX_LINE = 256 * 1024
MAX_STATE = 24_000
MAX_QUESTIONS = 8


def validate_request(request: object) -> tuple[str, dict]:
    if not isinstance(request, dict):
        raise ValueError("request must be an object")
    state = request.get("state")
    questions = request.get("questions")
    if not isinstance(state, str) or not state.strip() or len(state) > MAX_STATE:
        raise ValueError("state must be a non-empty string within 24000 characters")
    if not isinstance(questions, dict) or not 1 <= len(questions) <= MAX_QUESTIONS:
        raise ValueError("questions must contain 1-8 entries")
    for name, question in questions.items():
        if not isinstance(name, str) or not name or len(name) > 100 or not isinstance(question, dict):
            raise ValueError("invalid question name or definition")
        if set(question) - {"type", "instructions", "criteria"}:
            raise ValueError("unsupported question fields; refusing partial token preflight")
        kind = question.get("type")
        instructions = question.get("instructions")
        if kind not in ("choice", "score", "noul") or not isinstance(instructions, str) or not instructions.strip() or len(instructions) > 2000:
            raise ValueError("invalid question type or instructions")
        criteria = question.get("criteria")
        if kind == "choice":
            if isinstance(criteria, list):
                if any(not isinstance(item, str) for item in criteria) or len(set(criteria)) != len(criteria):
                    raise ValueError("invalid choice criteria")
                criteria = {item: None for item in criteria}
            if not isinstance(criteria, dict) or not 1 <= len(criteria) <= 12 or any(
                not isinstance(label, str) or not label or len(label) > 200 for label in criteria
            ):
                raise ValueError("invalid choice criteria")
            if any(value is not None and (not isinstance(value, str) or len(value) > 200)
                   for value in criteria.values()):
                raise ValueError("invalid choice descriptions")
            question["criteria"] = criteria
        elif kind == "score":
            if isinstance(criteria, dict):
                criteria = list(criteria)
            if not isinstance(criteria, list) or not 2 <= len(criteria) <= 12 or any(
                not isinstance(item, str) or len(item) > 200 for item in criteria
            ):
                raise ValueError("invalid score criteria")
            question["criteria"] = criteria
        elif criteria is not None:
            if isinstance(criteria, list):
                if any(not isinstance(key, str) for key in criteria) or len(set(criteria)) != len(criteria):
                    raise ValueError("invalid noul criteria")
                criteria = {key: None for key in criteria}
            if not isinstance(criteria, dict) or not set(criteria) <= {"true", "false"} or any(
                value is not None and (not isinstance(value, str) or len(value) > 200)
                for value in criteria.values()
            ):
                raise ValueError("invalid noul criteria")
            question["criteria"] = criteria
    return state, questions


def _options(question: dict) -> list[str]:
    """Match the pinned Laya 0.3.20 laya.common.render_options text exactly."""
    kind = question["type"]
    criteria = question.get("criteria")
    if kind == "choice":
        return [key if value is None or value == "" else f"{key}: {value}" for key, value in criteria.items()]
    if kind == "score":
        return [f"level {index}: {value}" for index, value in enumerate(criteria)]
    criteria = criteria or {}
    return [
        "false: " + (criteria.get("false") or "no, the statement does not hold"),
        "true: " + (criteria.get("true") or "yes, the statement holds"),
    ]


def preflight(agent: object, state: str, questions: dict) -> None:
    """Reject every upstream state/head/option truncation before model.predict()."""
    tok = agent.tok
    max_len = min(1024, int(agent.cfg.get("max_len", 512)))
    head_max = int(agent.cfg.get("head_max_len", 192))
    state_ids = tok(state.replace(tok.mask_token, " "), add_special_tokens=False)["input_ids"]
    for question in questions.values():
        head = tok(f"{question['type']} question: {question['instructions'].replace(tok.mask_token, ' ')}",
                   add_special_tokens=False)["input_ids"]
        option_lengths = [len(tok(" " + option.replace(tok.mask_token, " "),
                                  add_special_tokens=False)["input_ids"]) for option in _options(question)]
        if any(length > 48 for length in option_lengths):
            raise ValueError("criterion exceeds 48 tokens; refusing truncated input")
        opt_budget = head_max - sum(1 + length for length in option_lengths)
        if opt_budget < 16 or len(head) > max(8, opt_budget):
            raise ValueError("question head exceeds token budget; refusing truncation")
        if 4 + len(head) + sum(1 + length for length in option_lengths) + len(state_ids) > max_len:
            raise ValueError("state and questions exceed checkpoint context token budget")


def validate_output(result: object, questions: dict) -> dict:
    if not isinstance(result, dict) or not isinstance(result.get("answers"), dict) or set(result["answers"]) != set(questions):
        raise ValueError("missing or unexpected model answers")
    for name, question in questions.items():
        answer = result["answers"][name]
        if not isinstance(answer, dict) or answer.get("type") != question["type"]:
            raise ValueError("invalid answer type")
        kind = question["type"]
        value = answer.get(kind)
        if kind == "choice":
            if value not in question["criteria"]:
                raise ValueError("choice answer outside criteria")
        elif not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("invalid answer probability or score")
        for confidence in ("confidence", "answer_confidence"):
            metric = answer.get(confidence)
            if metric is not None and (isinstance(metric, bool) or not isinstance(metric, (int, float))
                                       or not math.isfinite(metric) or not 0 <= metric <= 1):
                raise ValueError("invalid answer confidence probability")
        probabilities = answer.get("probabilities")
        if kind in ("choice", "score") and not isinstance(probabilities, dict):
            raise ValueError("missing answer probabilities")
        if probabilities is not None:
            if not isinstance(probabilities, dict) or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1
                for v in probabilities.values()
            ):
                raise ValueError("invalid answer probabilities")
            expected = set(question["criteria"]) if kind == "choice" else {str(i) for i in range(len(question["criteria"]))} if kind == "score" else {"true", "false"}
            if set(probabilities) != expected or abs(sum(probabilities.values()) - 1) > 0.02:
                raise ValueError("incomplete answer probabilities")
    return result


def _predict(state: str, questions: dict, router: list) -> dict:
    if os.environ.get("LAYA_BRIDGE_TEST") == "1":
        delay = os.environ.get("LAYA_TEST_DELAY_MS", "")
        if delay.isdigit() and 0 < int(delay) <= 2000:
            from time import sleep

            sleep(int(delay) / 1000)
        answers = {}
        for name, question in questions.items():
            kind = question["type"]
            if kind == "choice":
                chosen = next(iter(question["criteria"]))
                answers[name] = {"type": kind, "choice": chosen,
                                 "probabilities": {label: float(label == chosen) for label in question["criteria"]}}
            elif kind == "score":
                answers[name] = {"type": kind, "score": 0.5,
                                 "probabilities": {str(i): 1 / len(question["criteria"]) for i in range(len(question["criteria"]))}}
            else:
                answers[name] = {"type": kind, "noul": float(os.environ.get("LAYA_TEST_NOUL", "0.75"))}
        if len(state) > 3000:
            raise ValueError("test state exceeds token budget")
        return {"model": "laya-multilingual-test", "routing": {"model": MODEL}, "answers": answers,
                "usage": {"input_tokens": 0, "output_tokens": 0}}
    if not router:
        from importlib.metadata import version
        if version("laya") != VERSION:
            raise RuntimeError("unsupported Laya version; install pinned laya==0.3.20")
        from laya import Router
        router.append(Router(device="mps", default=MODEL))
    agent = router[0].load(MODEL)
    preflight(agent, state, questions)
    result = router[0].predict(state, questions, model=MODEL)
    if result.get("routing", {}).get("model") != MODEL:
        raise ValueError("unexpected checkpoint route")
    return result


def main() -> None:
    # Never let the model fetch a checkpoint silently. Provision/cache it explicitly.
    os.environ["HF_HUB_OFFLINE"] = "1"
    router: list = []
    while True:
        line = sys.stdin.buffer.readline(MAX_LINE + 1)
        if not line:
            return
        try:
            if len(line) > MAX_LINE:
                raise ValueError("request exceeds maximum message length")
            request = json.loads(line)
            state, questions = validate_request(request)
            result = validate_output(_predict(state, questions, router), questions)
            reply = {"id": request.get("id"), "result": result, "ok": True}
        except (ValueError, TypeError, KeyError, ImportError, RuntimeError, OSError) as error:
            # Errors are bounded and contain no request state or credential material.
            reply = {"id": None, "ok": False, "error": str(error)[:200]}
        except Exception as error:
            reply = {"id": None, "ok": False, "error": type(error).__name__}
        sys.stdout.write(json.dumps(reply, allow_nan=False) + "\n")
        sys.stdout.flush()
        if len(line) > MAX_LINE and not line.endswith(b"\n"):
            return  # Never parse an unbounded continuation as a new request.


if __name__ == "__main__":
    main()

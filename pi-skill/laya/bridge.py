#!/usr/bin/env python3
"""Local Laya JSONL bridge: one session-scoped process, one router, two checkpoints.

The Pi extension spawns this file once per session and talks to it in newline-delimited
JSON — one request object in, one response object out, in order. The first request
builds `laya.Router(max_loaded=2, device=$LAYA_DEVICE)`, and the router then loads the
upstream English `convaiinnovations/laya` checkpoint or its bundled `multilingual`
subfolder on first use and keeps both resident, so alternating English and
Uzbek-hinted decisions never reload a model. The specialized `typed-decisions`
checkpoint is present in the router (as upstream) but is never selectable here: any
other route is refused before it can be loaded.

A request is `{"id", "state", "questions", "lang"?}`. `lang` is an optional
BCP-47-style hint — Latin-script Uzbek is read as English by the upstream detector,
which is why the hint exists — and `LAYA_LANG` is only an operator fallback when a
request carries none. Nothing here reads a credential or opens a socket: the model
comes from the local Hugging Face cache, and the response reports the route that
answered plus the local checkpoint identity.

`--check` builds the router and preloads both routed checkpoints so the installer can
verify them before any extension is activated; it exits non-zero with the failure on
stderr.

Everything the model prints goes to stderr: file descriptor 1 is duplicated onto the
protocol channel at startup, so even a native library print cannot corrupt a response.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

MAX_QUESTIONS = 8
MAX_CRITERIA = 12
MAX_STATE = 24_000
MAX_INSTRUCTIONS = 2_000
MAX_LANG = 16
MAX_ERROR = 400
KINDS = ("choice", "score", "noul")
ROUTES = ("english", "multilingual")
LANG = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
QUESTION_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}$")
REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")
_KEEP = ("type", "choice", "score", "noul", "probabilities", "confidence", "legend", "action")


class RequestError(ValueError):
    """A caller error: answered as `ok: false` without touching the model."""


def log(message: str) -> None:
    """One diagnostic line on stderr; never on the protocol channel."""
    print(f"laya: {message}", file=sys.stderr, flush=True)


def _text(value, limit: int, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RequestError(f"invalid {what}")
    if len(value) > limit:
        raise RequestError(f"invalid {what}")
    return value


def _lang(value) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > MAX_LANG or not LANG.match(value.strip()):
        raise RequestError("invalid lang hint")
    return value.strip()


def _criteria(kind: str, value, qid: str):
    """The upstream shapes: an ordered level list for `score`, a label→meaning map for
    `choice`/`noul`. A bare label list is normalized here, never forwarded blind."""
    if isinstance(value, list):
        if not value or len(value) > MAX_CRITERIA:
            raise RequestError(f'invalid criteria for "{qid}"')
        labels = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise RequestError(f'invalid criteria for "{qid}"')
            labels.append(item.strip())
        return labels if kind == "score" else dict.fromkeys(labels)
    if not isinstance(value, dict) or not value or len(value) > MAX_CRITERIA:
        raise RequestError(f'invalid criteria for "{qid}"')
    shaped: dict = {}
    for name, meaning in value.items():
        if not isinstance(name, str) or not name.strip():
            raise RequestError(f'invalid criteria for "{qid}"')
        if meaning is not None and (not isinstance(meaning, str) or not meaning.strip()):
            raise RequestError(f'invalid criteria for "{qid}"')
        shaped[name.strip()] = None if meaning is None else meaning.strip()
    return list(shaped) if kind == "score" else shaped


def questions_of(raw) -> dict:
    """Validate the caller's questions; a malformed question never reaches the model."""
    if not isinstance(raw, dict):
        raise RequestError("invalid questions")
    if not 1 <= len(raw) <= MAX_QUESTIONS:
        raise RequestError(f"1-{MAX_QUESTIONS} questions required")
    payload: dict = {}
    for qid, question in raw.items():
        if not isinstance(qid, str) or not QUESTION_ID.match(qid):
            raise RequestError(f'invalid question id "{qid}"')
        if not isinstance(question, dict):
            raise RequestError(f'invalid question "{qid}"')
        kind = question.get("type")
        if kind not in KINDS:
            raise RequestError(f'invalid question type for "{qid}"')
        instructions = _text(question.get("instructions"), MAX_INSTRUCTIONS, f'instructions for "{qid}"')
        if question.get("criteria") is None:
            if kind in ("choice", "score"):
                raise RequestError(f'criteria required for "{qid}" ({kind})')
            payload[qid] = {"type": kind, "instructions": instructions.strip()}
        else:
            payload[qid] = {"type": kind, "instructions": instructions.strip(),
                            "criteria": _criteria(kind, question["criteria"], qid)}
    return payload


def request_of(raw) -> tuple[str, str, dict, str | None]:
    """`(id, state, questions, lang)` for one parsed request line."""
    if not isinstance(raw, dict):
        raise RequestError("invalid request")
    request_id = raw.get("id")
    if not isinstance(request_id, str) or not REQUEST_ID.match(request_id):
        raise RequestError(f'invalid request id "{request_id}"')
    state = _text(raw.get("state"), MAX_STATE, "state")
    lang = _lang(raw.get("lang")) or _lang(os.environ.get("LAYA_LANG")) or None
    return request_id, state, questions_of(raw.get("questions")), lang


def answers_of(raw, questions: dict) -> dict:
    """Only the questions that were asked, with only the typed fields a caller reads.

    A model-side shape problem raises a plain failure, not a caller error: it is
    answered as `inference failed`, and the caller falls back on its own judgment."""
    if not isinstance(raw, dict):
        raise RuntimeError("the local model returned no answers")
    answers: dict = {}
    for qid, question in questions.items():
        answer = raw.get(qid)
        if not isinstance(answer, dict) or answer.get(question["type"]) is None:
            raise RuntimeError(f'the local model returned no {question["type"]} value for "{qid}"')
        kept = {name: answer[name] for name in _KEEP if name in answer}
        kept["type"] = question["type"]
        answers[qid] = kept
    return answers


def usage_of(raw) -> dict:
    """A local checkpoint generates no tokens. `output_tokens` stays 0 for the schema
    the callers already read; `input_tokens` is what the model reported, or 0."""
    usage = raw.get("usage") if isinstance(raw, dict) else None
    tokens = usage.get("input_tokens") if isinstance(usage, dict) else None
    if not isinstance(tokens, (int, float)) or isinstance(tokens, bool) or tokens < 0:
        tokens = 0
    return {"input_tokens": int(tokens), "output_tokens": 0}


def checkpoint(decision: dict) -> str:
    """The local checkpoint identity behind a route, e.g. `convaiinnovations/laya`."""
    return str(decision.get("repo") or decision.get("model") or "unknown")


class Runtime:
    """The router, built once, plus the two allowed routes."""

    def __init__(self) -> None:
        self._router = None

    def router(self):
        if self._router is None:
            import laya  # the only third-party import, and the only model source

            device = (os.environ.get("LAYA_DEVICE") or "").strip() or None
            self._router = laya.Router(max_loaded=2, device=device)
            log(f"router ready (max_loaded=2 device={device or 'auto'})")
        return self._router

    def targets(self) -> dict:
        models = getattr(self.router(), "models", {}) or {}
        chosen = {}
        for route in ROUTES:
            entry = models.get(route)
            if isinstance(entry, (list, tuple)):
                repo, sub = (list(entry) + [None, None])[:2]
                chosen[route] = f"{repo}:{sub}" if sub else str(repo)
            else:
                chosen[route] = str(entry)
        return chosen

    def predict(self, state: str, questions: dict, lang: str | None) -> dict:
        """Route, then answer on the chosen checkpoint. `typed-decisions` cannot be
        selected: the router is built without task detection and any other route is
        refused before a load."""
        router = self.router()
        hint = {"lang": lang} if lang else {}
        decision = dict(router.route(state, questions, **hint))
        route = str(decision.get("model") or "")
        if route not in ROUTES:
            raise RequestError(f"refused local route {route!r}: only {list(ROUTES)} are enabled")
        before = set(getattr(router, "loaded", ()) or ())
        result = router.predict(state, questions, **hint)
        if route not in before:
            log(f"loaded {route}={checkpoint(decision)}")
        if not isinstance(result, dict):
            raise RequestError("the local model returned no result")
        routing = result.get("routing") if isinstance(result.get("routing"), dict) else decision
        model = str(routing.get("repo") or checkpoint(decision))
        log(f"answered route={route} model={model} lang={lang or 'auto'}")
        return {
            "route": route,
            "model": model,
            "lang": lang,
            "reason": str(routing.get("reason") or decision.get("reason") or ""),
            "answers": answers_of(result.get("answers"), questions),
            "usage": usage_of(result),
        }


def handle(runtime: Runtime, line: str) -> dict:
    """One request line to one response object; every failure stays bounded."""
    request_id = "?"
    try:
        raw = json.loads(line)
        if isinstance(raw, dict) and isinstance(raw.get("id"), str):
            request_id = raw["id"]
        request_id, state, questions, lang = request_of(raw)
        return {"id": request_id, "ok": True, **runtime.predict(state, questions, lang)}
    except json.JSONDecodeError:
        return {"id": request_id, "ok": False, "error": "invalid request: not JSON"}
    except RequestError as error:
        return {"id": request_id, "ok": False, "error": f"invalid request: {error}"[:MAX_ERROR]}
    except Exception as error:  # a model or runtime failure, never a crash
        detail = str(error).strip() or error.__class__.__name__
        return {"id": request_id, "ok": False, "error": f"inference failed: {detail}"[:MAX_ERROR], "route": None}


def serve(runtime: Runtime) -> int:
    """Read requests until EOF; write one response per request in order."""
    out = _protocol_channel()
    for line in sys.stdin:
        line = line.strip()
        response = handle(runtime, line) if line else {"id": "?", "ok": False,
                                                       "error": "invalid request: empty line"}
        out.write(json.dumps(response, ensure_ascii=False) + "\n")
        out.flush()
    return 0


def _protocol_channel():
    """Take fd 1 for responses and hand every other stdout write to stderr, so a
    checkpoint that prints (or a native library that writes to fd 1) cannot corrupt
    the JavaScript Object Notation Lines channel."""
    saved = os.dup(1)
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    return os.fdopen(saved, "w", buffering=1, encoding="utf-8")


def check(runtime: Runtime) -> int:
    targets = runtime.targets()
    runtime.router().preload(list(ROUTES))
    for route in ROUTES:
        log(f"loaded {route}={targets[route]}")
    print("\n".join(f"{route}={targets[route]}" for route in ROUTES))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="local Laya stdio bridge for Pi")
    parser.add_argument("--check", action="store_true",
                        help="build the router, preload both routed checkpoints and report them")
    args = parser.parse_args(argv)
    runtime = Runtime()
    if args.check:
        try:
            return check(runtime)
        except Exception as error:
            print(f"laya runtime check failed: {error}", file=sys.stderr)
            return 1
    return serve(runtime)


if __name__ == "__main__":
    sys.exit(main())

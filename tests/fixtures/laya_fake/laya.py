"""Deterministic stand-in for upstream `laya` 0.3.5 (`pip install laya`).

Test-only. It implements exactly the surface the stdio bridge uses — ``laya.Router``
with ``route``/``predict``/``load``/``preload``/``loaded``/``models`` — so the focused
suites drive the real bridge and the real Pi extension without torch, weights or a
network call.

Routing mirrors upstream's observable rules: an explicit non-English ``lang`` routes
to ``multilingual``, otherwise a non-Latin script routes to ``multilingual`` and
everything else to ``english`` — including Latin-script Uzbek, which is exactly why
the caller's hint matters. ``typed-decisions`` is present in ``models`` (as upstream)
but is never selected and refuses to load, so a regression that reaches it fails
loudly.

Scripted directives, consumed one line at a time from ``$LAYA_FAKE_SCRIPT``, can
print to stdout, sleep, raise or kill the process — that is how stdout purity,
cancellation, timeout and crash boundaries stay reachable. ``$LAYA_FAKE_ROUTERS``
records one line per Router construction, ``$LAYA_FAKE_LOADS`` one line per checkpoint
load (so "each checkpoint loads at most once" is observable) and ``$LAYA_FAKE_CALLS``
one line per prediction with the route, language hint and request shape.

Answers: ``$LAYA_FAKE_STALE_IDS`` (comma-separated question ids) drives the compaction
keep/drop cases, ``$LAYA_FAKE_NEEDLE`` the sift hit/miss cases, otherwise ``noul``
answers 0.05, ``choice`` picks the first criterion and ``score`` the middle level.
"""
from __future__ import annotations

import json
import os
import sys
import time

__version__ = "0.3.5"

BUNDLE_REPO = "convaiinnovations/laya"
DEFAULT_MODELS = {
    "english": (BUNDLE_REPO, None),
    "multilingual": (BUNDLE_REPO, "multilingual"),
    "typed-decisions": (BUNDLE_REPO, "typed-decisions"),
}
STANDALONE_MODELS = {
    "english": "convaiinnovations/laya",
    "multilingual": "convaiinnovations/laya-multilingual",
    "typed-decisions": "convaiinnovations/laya-typed-decisions",
}
ALIASES = {"en": "english", "eng": "english", "ml": "multilingual", "multi": "multilingual",
           "typed": "typed-decisions", "typed_decisions": "typed-decisions"}
ROUTES = ("english", "multilingual")

_SCRIPTS = {
    "nonlatin": "cyrillic",
    "latin": "latin",
}


def _append(name: str, row: dict) -> None:
    path = os.environ.get(name)
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _directive() -> dict:
    path = os.environ.get("LAYA_FAKE_SCRIPT")
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        lines = [line for line in handle.read().splitlines() if line.strip()]
    if not lines:
        return {}
    row = json.loads(lines[0])
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("".join(line + "\n" for line in lines[1:]))
    return row


def _environment(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def _environment_file(name: str) -> str:
    path = _environment(name)
    if not path or not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as handle:
        return handle.read().strip()


def normalise_name(name: str) -> str:
    key = str(name).strip().lower().replace("-", "_")
    key = ALIASES.get(key, key)
    if key not in DEFAULT_MODELS:
        raise ValueError(f"unknown model {name!r}; choose one of {sorted(DEFAULT_MODELS)}")
    return key


def _repo(entry) -> str:
    if isinstance(entry, (list, tuple)):
        repo, sub = (list(entry) + [None, None])[:2]
        return f"{repo}:{sub}" if sub else str(repo)
    return str(entry)


def _script(state) -> str:
    """Latin unless the state carries letters from another script."""
    text = state if isinstance(state, str) else json.dumps(state, ensure_ascii=False)
    for char in text:
        if char.isalpha() and not char.isascii():
            return "cyrillic"
    return "latin"


def _noul(state: str, qid: str) -> float:
    stale = [item.strip() for item in _environment("LAYA_FAKE_STALE_IDS").split(",") if item.strip()]
    if stale:
        stale_p = float(_environment("LAYA_FAKE_STALE_P") or 0.05)
        keep_p = float(_environment("LAYA_FAKE_KEEP_P") or 0.95)
        return stale_p if qid in stale else keep_p
    needle = _environment("LAYA_FAKE_NEEDLE")
    if needle:
        hit = float(_environment("LAYA_FAKE_NEEDLE_HIT") or 0.93)
        miss = float(_environment("LAYA_FAKE_NEEDLE_MISS") or 0.07)
        return hit if needle in state else miss
    return 0.05


def _answers(state: str, questions: dict) -> dict:
    answers: dict = {}
    for qid, question in questions.items():
        kind = question.get("type")
        criteria = question.get("criteria")
        if kind == "choice":
            labels = list(criteria) if isinstance(criteria, dict) else list(criteria or [])
            if not labels:
                labels = ["only"]
            pick = labels[0]
            rest = max(1, len(labels) - 1)
            answers[qid] = {
                "type": "choice",
                "choice": pick,
                "probabilities": {label: round(0.9 if label == pick else 0.1 / rest, 4) for label in labels},
                "confidence": 0.9,
                "action": {"act_probability": 0.3},
            }
        elif kind == "score":
            levels = list(criteria or [])
            count = max(1, len(levels))
            answers[qid] = {
                "type": "score",
                "score": round((count - 1) / 2, 4),
                "legend": {str(index): level for index, level in enumerate(levels)},
                "probabilities": {str(index): round(1 / count, 4) for index in range(count)},
                "confidence": 0.5,
                "action": {"act_probability": 0.2},
            }
        else:
            note = _noul(state, qid)
            answers[qid] = {
                "type": "noul",
                "noul": note,
                "confidence": round(max(note, 1.0 - note), 4),
                "action": {"act_probability": 0.1},
            }
    return answers


class Agent:
    """The smallest stand-in for one loaded checkpoint."""

    def __init__(self, model_id: str = BUNDLE_REPO, device=None, subfolder=None, route: str = "english"):
        self.model_id = model_id
        self.device = device
        self.subfolder = subfolder
        self.route = route

    def system_one(self, state, questions):
        directive = _directive()
        if directive.get("noise"):
            print(directive["noise"])
            sys.stdout.flush()
        if directive.get("sleep_ms"):
            time.sleep(float(directive["sleep_ms"]) / 1000.0)
        if directive.get("error"):
            raise RuntimeError(str(directive["error"]))
        if directive.get("exit") is not None:
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(int(directive["exit"]))
        # Upstream answers every question it was asked, so a scripted override only
        # replaces the questions it names instead of hiding the rest.
        text = state if isinstance(state, str) else json.dumps(state, ensure_ascii=False)
        answers = {**_answers(text, questions), **(directive.get("answers") or {})}
        if directive.get("extra_answers"):
            answers = {**answers, **directive["extra_answers"]}
        return {"answers": answers, "usage": directive.get("usage", {"input_tokens": 42, "output_tokens": 0})}

    __call__ = system_one


class Router:
    """Two slots, lazy loads, English/multilingual routing — upstream's observable shape."""

    def __init__(
        self,
        models=None,
        device=None,
        token=None,
        max_loaded: int = 1,
        default: str = "english",
        auto_task_detection: bool = False,
        standalone_repos: bool = False,
        preload: bool = False,
    ):
        self.models = dict(STANDALONE_MODELS if standalone_repos else DEFAULT_MODELS)
        if models:
            self.models.update({normalise_name(key): value for key, value in models.items()})
        self.device = device
        self.token = token or os.environ.get("HF_TOKEN")
        self.max_loaded = max(1, int(max_loaded))
        self.default = normalise_name(default)
        self.auto_task_detection = bool(auto_task_detection)
        self._agents: dict = {}
        self._order: list = []
        _append("LAYA_FAKE_ROUTERS", {
            "pid": os.getpid(), "device": device, "max_loaded": self.max_loaded,
            "auto_task_detection": self.auto_task_detection, "default": self.default,
            "preload": bool(preload),
        })
        if preload:
            self.preload()

    @property
    def loaded(self) -> list:
        return list(self._order)

    def _touch(self, key: str) -> None:
        if key in self._order:
            self._order.remove(key)
        self._order.append(key)

    def _evict(self) -> None:
        while len(self._order) > self.max_loaded:
            self._agents.pop(self._order.pop(0), None)

    def load(self, name: str):
        key = normalise_name(name)
        if key in self._agents:
            self._touch(key)
            return self._agents[key]
        repo, sub = self.models[key] if isinstance(self.models[key], (list, tuple)) else (self.models[key], None)
        _append("LAYA_FAKE_LOADS", {"pid": os.getpid(), "model": key, "repo": repo, "subfolder": sub})
        if key not in ROUTES:
            raise RuntimeError(f"refusing to load {key!r}: this bridge enables only {list(ROUTES)}")
        error = _environment("LAYA_FAKE_LOAD_ERROR") or _environment_file("LAYA_FAKE_LOAD_ERROR_FILE")
        if error:
            raise RuntimeError(error)
        if _environment("LAYA_FAKE_LOAD_NOISE"):
            print(_environment("LAYA_FAKE_LOAD_NOISE"))
            sys.stdout.flush()
        agent = Agent(f"{repo}:{sub}" if sub else repo, device=self.device, subfolder=sub, route=key)
        self._agents[key] = agent
        self._order.append(key)
        self._evict()
        return agent

    def preload(self, names=None):
        keys = [normalise_name(name) for name in (names or list(self.models))]
        self.max_loaded = max(self.max_loaded, len(keys), len(self._agents))
        for key in keys:
            if key not in self._agents:
                self.load(key)
        return self

    def route(self, state, questions=None, model=None, task=None, lang=None) -> dict:
        if model is not None:
            key = normalise_name(model)
            return {"model": key, "repo": _repo(self.models[key]), "reason": f"explicit model={model!r}",
                    "detection": None, "workflow": None}
        if task is not None:
            key = normalise_name("typed-decisions" if str(task).lower().replace("-", "_") == "typed_decisions" else task)
            return {"model": key, "repo": _repo(self.models[key]), "reason": f"explicit task={task!r}",
                    "detection": None, "workflow": None}
        if lang is not None:
            english = str(lang).lower().split("-")[0] in ("en", "eng", "english")
            key = "english" if english else "multilingual"
            return {"model": key, "repo": _repo(self.models[key]), "reason": f"explicit lang={lang!r}",
                    "detection": None, "workflow": None}
        script = _script(state)
        if script != "latin":
            key, reason = "multilingual", f"non-Latin script ({script}); the English checkpoint cannot read it"
        else:
            key, reason = "english", "English Latin text"
        return {"model": key, "repo": _repo(self.models[key]), "reason": reason,
                "detection": {"script": script}, "workflow": None}

    def predict(self, state, questions, model=None, task=None, lang=None) -> dict:
        decision = self.route(state, questions, model=model, task=task, lang=lang)
        agent = self.load(decision["model"])
        _append("LAYA_FAKE_CALLS", {
            "pid": os.getpid(), "route": decision["model"], "repo": decision["repo"], "lang": lang,
            "reason": decision["reason"], "device": self.device,
            "state": state if isinstance(state, str) else json.dumps(state, ensure_ascii=False),
            "questions": questions,
        })
        seen = [item.strip() for item in _environment("LAYA_FAKE_ENV").split(",") if item.strip()]
        if seen:
            _append("LAYA_FAKE_ENV_SEEN", {key: os.environ.get(key) for key in seen})
        result = agent.system_one(state, questions)
        result["routing"] = dict(decision)
        return result

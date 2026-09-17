#!/usr/bin/env python3
"""Jev against Pi's deepseek/minimax models on a labelled triage set.

Arms
  jev                          TypeSafe System One, one POST per item
  pi:deepseek/deepseek-flash   non-interactive Pi run, strict-JSON answer prompt
  pi:minimax/MiniMax-M3        same prompt and settings

Each arm sees the same policy text and the same request text; only the interface
differs (typed questions with probabilities vs a JSON answer in text).

  python3 run_jev_bench.py run --root DIR --results DIR/trials.jsonl
  python3 run_jev_bench.py report --items items.json --results DIR/trials.jsonl

Raw responses stay in --root. The jev arm needs TYPESAFE_API_KEY in the
environment; it is never written to a record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import ssl
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
JEV_URL = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-1.13.0"
# $42 per billion input tokens ($0.042/Mtok); output tokens are free.
JEV_USD_PER_INPUT_TOKEN = 42.0 / 1e9
# python.org builds ship no CA bundle; the system store is used when present.
CERT_FILE = "/etc/ssl/cert.pem"
PI_THINKING = "medium"
PI_TIMEOUT = 180
ARMS = ("jev", "pi:deepseek/deepseek-flash", "pi:minimax/MiniMax-M3")
TYPES = ("bug", "feature", "refactor", "docs", "test", "chore", "research")
EFFORT_LEVELS = (
    "one file at a known seam",
    "a few files inside one module",
    "cross-module or multi-repository work",
    "architecture-level change",
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")


def jev_questions() -> dict:
    return {
        "task_type": {
            "type": "choice",
            "instructions": "Which single task type describes the `request`?",
            "criteria": {name: None for name in TYPES},
        },
        "effort": {
            "type": "score",
            "instructions": "How much of the repository does the `request` need?",
            "criteria": list(EFFORT_LEVELS),
        },
        "needs_approval": {
            "type": "noul",
            "instructions": (
                "Is the `request` itself a reserved user-owned decision that the agent "
                "must not act on before the user approves?"
            ),
            "criteria": {
                "true": "Pushing or promoting to main, deleting files or data, changing "
                        "credentials or permissions, or installing or removing software.",
                "false": "Any ordinary scoped change that the agent may carry out directly.",
            },
        },
    }


def jev_state(policy: dict, request: str) -> dict:
    return {"policy": policy, "request": request}


def pi_prompt(policy: dict, request: str) -> str:
    return (
        "You are triaging one request for a software repository.\n\n"
        f"Type policy: {policy['type']}\n\n"
        f"Effort policy: {policy['effort']}\n\n"
        f"Approval policy: {policy['approval']}\n\n"
        f"Request: {request}\n\n"
        "Answer with a single JSON object and nothing else, using exactly these keys: "
        '{"type": "<one of: bug, feature, refactor, docs, test, chore, research>", '
        '"effort": <integer 0-3>, "needs_approval": <true or false>}'
    )


def jev_ask(state: dict, key: str, questions: dict | None = None) -> dict:
    body = json.dumps({"state": state, "model": JEV_MODEL,
                       "questions": questions or jev_questions()}).encode()
    request = urllib.request.Request(
        JEV_URL,
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(
        request,
        timeout=PI_TIMEOUT,
        context=ssl.create_default_context(cafile=CERT_FILE if Path(CERT_FILE).exists() else None),
    ) as response:
        return json.loads(response.read())


def pi_ask(arm: str, prompt: str, cwd: Path) -> tuple[str, dict, dict]:
    model = arm.split(":", 1)[1]
    command = ["pi", "-p", "--mode", "json", "--no-session", "-a",
               "--model", model, "--thinking", PI_THINKING, prompt]
    env = os.environ.copy()
    env.pop("PI_CONFIG_FILES", None)
    proc = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=PI_TIMEOUT)
    texts: list[str] = []
    usage = {"input": 0, "output": 0, "cache_read": 0, "total": 0, "cost_usd": 0.0}
    models: set[str] = set()
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = event.get("message") or {}
        if event.get("type") == "turn_end" and message.get("role") == "assistant":
            counters = message.get("usage") or {}
            usage["input"] += counters.get("input") or 0
            usage["output"] += counters.get("output") or 0
            usage["cache_read"] += counters.get("cacheRead") or 0
            usage["total"] += counters.get("totalTokens") or 0
            usage["cost_usd"] += (counters.get("cost") or {}).get("total") or 0.0
            if message.get("model"):
                models.add(f"{message.get('provider')}/{message.get('model')}")
    for line in reversed((proc.stdout or "").splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = event.get("message") or {}
        if event.get("type") == "turn_end" and message.get("role") == "assistant":
            for part in message.get("content") or []:
                if isinstance(part, dict) and part.get("type") == "text":
                    texts.append(part.get("text", ""))
            break
    usage["cost_usd"] = round(usage["cost_usd"], 6)
    meta = {"reported_models": sorted(models), "exit_status": proc.returncode,
            "stderr_tail": (proc.stderr or "").strip().splitlines()[-3:]}
    return "\n".join(texts), usage, meta


def parse_json_answer(text: str) -> dict | None:
    start = text.find("{")
    while start != -1:
        try:
            value, _ = json.JSONDecoder().raw_decode(text[start:])
        except json.JSONDecodeError:
            start = text.find("{", start + 1)
            continue
        if isinstance(value, dict):
            return value
        start = text.find("{", start + 1)
    return None


def normalize(value) -> tuple:
    """Return (parsed answer, parse_error) for one arm."""
    if value is None:
        return None, "no JSON object in the answer"
    task_type = value.get("type")
    if isinstance(task_type, str):
        task_type = task_type.strip().lower()
    effort = value.get("effort")
    if isinstance(effort, str):
        effort = effort.strip().lower()
        match = re.search(r"\d", effort)
        if match:
            effort = int(match.group(0))
        else:
            effort = next((i for i, level in enumerate(EFFORT_LEVELS) if level in effort), None)
    elif isinstance(effort, float) and effort.is_integer():
        effort = int(effort)
    approval = value.get("needs_approval")
    if isinstance(approval, str):
        approval = approval.strip().lower() in ("true", "yes", "1")
    errors = []
    if task_type not in TYPES:
        errors.append(f"out-of-vocabulary type {task_type!r}")
    if not isinstance(effort, int) or not 0 <= effort <= 3:
        errors.append(f"out-of-vocabulary effort {effort!r}")
    if not isinstance(approval, bool):
        errors.append(f"out-of-vocabulary needs_approval {approval!r}")
    parsed = {
        "type": task_type if task_type in TYPES else None,
        "effort": effort if isinstance(effort, int) and 0 <= effort <= 3 else None,
        "needs_approval": approval if isinstance(approval, bool) else None,
    }
    return parsed, "; ".join(errors)


def run_item(arm: str, policy: dict, item: dict, cwd: Path, key: str | None) -> dict:
    request = item["request"]
    started = time.time()
    signal = {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
              "total_tokens": 0, "cost_usd": 0.0}
    confidence = None
    probabilities = None
    error = None
    if arm == "jev":
        try:
            response = jev_ask(jev_state(policy, request), key or "")
        except Exception as exc:  # noqa: BLE001 - recorded, never raised
            error = f"{type(exc).__name__}: {exc}"
            raw, parsed, parse_error, meta = "", None, "request failed", {}
        else:
            answers = response.get("answers") or {}
            choice = answers.get("task_type") or {}
            score = answers.get("effort") or {}
            noul = answers.get("needs_approval") or {}
            # A Score answer is probability-weighted and may land between levels; the
            # level index is the rounded position, and the raw value is kept.
            score_value = score.get("score")
            effort_index = (
                None if score_value is None
                else max(0, min(len(EFFORT_LEVELS) - 1, round(score_value)))
            )
            raw = json.dumps(response)
            usage = response.get("usage") or {}
            signal = {
                "input_tokens": usage.get("input_tokens") or 0,
                "output_tokens": usage.get("output_tokens") or 0,
                "cache_read_tokens": 0,
                "total_tokens": (usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0),
                "cost_usd": round((usage.get("input_tokens") or 0) * JEV_USD_PER_INPUT_TOKEN, 9),
            }
            confidence = {"task_type": choice.get("confidence"), "effort": score.get("confidence")}
            probabilities = {k: v for k, v in (choice.get("probabilities") or {}).items() if v}
            parsed, parse_error = normalize({
                "type": choice.get("choice"),
                "effort": effort_index,
                "needs_approval": None if noul.get("noul") is None else noul.get("noul") >= 0.5,
            })
            parsed["noul"] = noul.get("noul")
            parsed["effort_raw"] = score_value
            meta = {"reported_models": [response.get("model")]}
    else:
        try:
            text, usage, meta = pi_ask(arm, pi_prompt(policy, request), cwd)
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
            raw, parsed, parse_error, meta = "", None, "request failed", {}
        else:
            raw = text
            parsed, parse_error = normalize(parse_json_answer(text))
            signal = {
                "input_tokens": usage["input"],
                "output_tokens": usage["output"],
                "cache_read_tokens": usage["cache_read"],
                "total_tokens": usage["total"],
                "cost_usd": usage["cost_usd"],
            }
    wall = round(time.time() - started, 3)
    label = item["label"]
    record = {
        "arm": arm,
        "item_id": item["id"],
        "request_sha256": sha256_text(request),
        "label": label,
        "parsed": parsed,
        "parse_error": parse_error or None,
        "error": error,
        "raw_answer": (raw or "")[:1200],
        "wall_seconds": wall,
        **signal,
        "confidence": confidence,
        "probabilities": probabilities,
        **(meta or {}),
    }
    if parsed:
        record["type_ok"] = parsed.get("type") == label["type"]
        record["effort_ok"] = parsed.get("effort") == label["effort"]
        record["effort_delta"] = (
            None if parsed.get("effort") is None else abs(parsed["effort"] - label["effort"])
        )
        record["approval_ok"] = parsed.get("needs_approval") == label["needs_approval"]
        record["all_ok"] = bool(record["type_ok"] and record["effort_ok"] and record["approval_ok"])
    else:
        record.update({"type_ok": False, "effort_ok": False, "effort_delta": None,
                       "approval_ok": False, "all_ok": False})
    return record


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def report(items_path: Path, results_path: Path) -> int:
    fixture = json.loads(items_path.read_text())
    rows = load(results_path)
    arm_order = [arm for arm in ARMS if any(r["arm"] == arm for r in rows)]
    arm_order += sorted({r["arm"] for r in rows} - set(arm_order))
    print(f"items={len(fixture['items'])} records={len(rows)} arms={arm_order}")
    header = f"{'arm':28s} {'n':>3s} {'type':>5s} {'effort':>6s} {'±1':>4s} {'approv':>6s} {'all3':>5s} {'bad':>4s} {'p50s':>6s} {'p95s':>6s} {'in_tok':>7s} {'cache':>8s} {'out_tok':>7s} {'cost$':>9s}"
    print(header)
    for arm in arm_order:
        sel = [r for r in rows if r["arm"] == arm]
        walls = sorted(r["wall_seconds"] for r in sel)
        p95 = walls[min(len(walls) - 1, int(round(0.95 * (len(walls) - 1))))]
        deltas = [r["effort_delta"] for r in sel if r["effort_delta"] is not None]
        print(
            f"{arm:28s} {len(sel):3d} "
            f"{sum(r['type_ok'] for r in sel):5d} "
            f"{sum(r['effort_ok'] for r in sel):6d} "
            f"{sum(1 for d in deltas if d <= 1):4d} "
            f"{sum(r['approval_ok'] for r in sel):6d} "
            f"{sum(r['all_ok'] for r in sel):5d} "
            f"{sum(1 for r in sel if r['parse_error']):4d} "
            f"{statistics.median(walls):6.1f} {p95:6.1f} "
            f"{sum(r['input_tokens'] for r in sel):7d} "
            f"{sum(r['cache_read_tokens'] for r in sel):8d} "
            f"{sum(r['output_tokens'] for r in sel):7d} "
            f"{sum(r['cost_usd'] for r in sel):9.6f}"
        )
    print("cols: type=exact type hits, effort=exact level hits, ±1=within one level, "
          "approv=approval hits, all3=whole answer correct, bad=parse/OOV failures")
    print("tokens: in_tok/cache are as reported by the host; providers differ in whether "
          "cached prompt tokens are split out, so cost$ is the comparable figure")
    print("== per item (label | arm answers) ==")
    for item in fixture["items"]:
        cells = []
        for arm in arm_order:
            row = next((r for r in rows if r["arm"] == arm and r["item_id"] == item["id"]), None)
            if row is None:
                cells.append(f"{arm}=missing")
                continue
            answer = row["parsed"] or {}
            mark = "ok " if row["all_ok"] else "XX "
            noul = answer.get("noul")
            extra = f" p={noul:.2f}" if isinstance(noul, float) else ""
            cells.append(f"{arm.split(':')[-1]}={mark}{answer.get('type')}/{answer.get('effort')}/"
                         f"{answer.get('needs_approval')}{extra}")
        label = item["label"]
        print(f"{item['id']} want {label['type']}/{label['effort']}/"
              f"{str(label['needs_approval'])[0]} | " + " | ".join(cells))
    return 0


def cmd_run(args) -> int:
    fixture = json.loads(Path(args.items).read_text())
    policy = fixture["policy"]
    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    cwd = root / "cwd"
    cwd.mkdir(exist_ok=True)
    results_path = Path(args.results).resolve()
    results_path.parent.mkdir(parents=True, exist_ok=True)
    arms = tuple(args.arms.split(",")) if args.arms else ARMS
    key = os.environ.get("TYPESAFE_API_KEY")
    if "jev" in arms and not key:
        raise SystemExit("TYPESAFE_API_KEY is required for the jev arm")
    done = {(r["arm"], r["item_id"]) for r in load(results_path)}
    for item in fixture["items"]:
        for arm in arms:
            if (arm, item["id"]) in done:
                print(f"skip {arm} {item['id']}", flush=True)
                continue
            record = run_item(arm, policy, item, cwd, key)
            (root / f"{slug(arm)}__{item['id']}.json").write_text(
                json.dumps(record, indent=2) + "\n"
            )
            with results_path.open("a") as handle:
                handle.write(json.dumps(record) + "\n")
            print(f"{item['id']} {arm:28s} wall={record['wall_seconds']:6.1f}s "
                  f"type={record['parsed'] and record['parsed'].get('type')} "
                  f"effort={record['parsed'] and record['parsed'].get('effort')} "
                  f"approval={record['parsed'] and record['parsed'].get('needs_approval')} "
                  f"ok={record['all_ok']} in={record['input_tokens']} "
                  f"cost=${record['cost_usd']:.6f} "
                  f"err={record['parse_error'] or record['error'] or '-'}", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--items", default=str(HERE / "items.json"))
    run.add_argument("--root", required=True)
    run.add_argument("--results", required=True)
    run.add_argument("--arms", default="")
    run.set_defaults(func=cmd_run)
    rep = sub.add_parser("report")
    rep.add_argument("--items", default=str(HERE / "items.json"))
    rep.add_argument("--results", required=True)
    rep.set_defaults(func=lambda a: report(Path(a.items), Path(a.results).resolve()))
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

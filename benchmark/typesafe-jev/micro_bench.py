#!/usr/bin/env python3
"""Focused micro-benchmark for TypeSafe Jev.

Measures how Jev behaves across:
  - baseline latency (same call repeated)
  - state size scaling (50 / 500 / 2k / 8k chars of state)
  - question-count scaling (1 / 4 / 8 questions per call)
  - answer consistency (same call repeated, distribution across runs)

All calls hit the same /v1/systemone endpoint with the jev-1.13.0 model and the
same question design. The benchmark is stdlib-only; TYPESAFE_API_KEY is read
from the environment and never written to a record.

  python3 benchmark/typesafe-jev/micro_bench.py run   --root DIR
  python3 benchmark/typesafe-jev/micro_bench.py report --root DIR
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import statistics
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
JEV_URL = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-1.13.0"
JEV_USD_PER_INPUT_TOKEN = 42.0 / 1e9
CERT_FILE = "/etc/ssl/cert.pem"
TIMEOUT = 30

VARIANTS = (
    "latency", "consistency",
    "size_tiny", "size_small", "size_medium", "size_large",
    "q1_choice", "q1_score", "q1_noul",
    "q4_mixed", "q8_mixed",
)


def _key() -> str:
    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        raise SystemExit("TYPESAFE_API_KEY is required")
    return key


def _state_for_size(size: str) -> dict:
    base = "request: bench a hypothetical code change. "
    body = {
        "tiny": base * 1,
        "small": base * 8,
        "medium": base * 32,
        "large": base * 128,
    }[size]
    return {"policy": {"type": "single label", "effort": "ordered level 0..3"},
            "request": body}


def _one_q_choice() -> dict:
    return {"type": {
        "type": "choice",
        "instructions": "Which task type fits the request?",
        "criteria": {
            "bug": "restore broken intended behavior",
            "feature": "add or change capability",
            "refactor": "restructure without behavior change",
            "docs": "documentation or policy text only",
            "test": "verification only",
            "chore": "deps, config, builds, maintenance",
            "research": "tracked investigation",
        },
    }}


def _one_q_score() -> dict:
    return {"effort": {
        "type": "score",
        "instructions": "How much of the repository does the request need?",
        "criteria": ["one file", "few files in one module",
                     "cross-module or multi-repo", "architecture-level change"],
    }}


def _one_q_noul() -> dict:
    return {"needs_approval": {
        "type": "noul",
        "instructions": "Is the request a reserved user-owned decision?",
        "criteria": {"true": "main push, delete, creds, install.",
                     "false": "ordinary scoped change."},
    }}


def _q_mixed(n: int) -> dict:
    """n distinct questions: cycle through choice/score/noul with unique suffixes."""
    pool = [_one_q_choice(), _one_q_score(), _one_q_noul()]
    base_keys = ["task_type", "effort", "needs_approval"]
    out = {}
    for i in range(n):
        qid = f"{base_keys[i % 3]}_{i}"  # distinct question ids
        out[qid] = list(pool[i % 3].values())[0]
    return out


def questions_for(variant: str) -> dict:
    if variant == "q1_choice":
        return _one_q_choice()
    if variant == "q1_score":
        return _one_q_score()
    if variant == "q1_noul":
        return _one_q_noul()
    if variant == "q4_mixed":
        return _q_mixed(4)
    if variant == "q8_mixed":
        return _q_mixed(8)
    # latency / consistency / size_* use a single noul question
    return _one_q_noul()


def state_for(variant: str) -> dict:
    if variant.startswith("size_"):
        return _state_for_size(variant[len("size_"):])
    return _state_for_size("small")


def repeats_for(variant: str) -> int:
    return {
        "latency": 20,
        "consistency": 10,
        "size_tiny": 5, "size_small": 5, "size_medium": 5, "size_large": 5,
        "q1_choice": 5, "q1_score": 5, "q1_noul": 5,
        "q4_mixed": 5, "q8_mixed": 5,
    }[variant]


def jev_call(state: dict, questions: dict, key: str) -> tuple[dict, float]:
    body = json.dumps({"state": state, "model": JEV_MODEL, "questions": questions}).encode()
    request = urllib.request.Request(
        JEV_URL,
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    started = time.time()
    with urllib.request.urlopen(
        request,
        timeout=TIMEOUT,
        context=ssl.create_default_context(cafile=CERT_FILE if Path(CERT_FILE).exists() else None),
    ) as response:
        payload = json.loads(response.read())
    return payload, time.time() - started


def run_one(variant: str, index: int, key: str) -> dict:
    state = state_for(variant)
    questions = questions_for(variant)
    try:
        payload, wall = jev_call(state, questions, key)
        answers = payload.get("answers") or {}
        usage = payload.get("usage") or {}
        return {
            "variant": variant,
            "index": index,
            "ok": True,
            "wall_seconds": round(wall, 4),
            "input_tokens": usage.get("input_tokens") or 0,
            "output_tokens": usage.get("output_tokens") or 0,
            "total_tokens": (usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0),
            "cost_usd": round((usage.get("input_tokens") or 0) * JEV_USD_PER_INPUT_TOKEN, 9),
            "model": payload.get("model"),
            "answers": answers,
        }
    except Exception as exc:  # noqa: BLE001
        return {"variant": variant, "index": index, "ok": False,
                "error": f"{type(exc).__name__}: {exc}"}


def cmd_run(args) -> int:
    root = Path(args.root).resolve()
    (root / "raw").mkdir(parents=True, exist_ok=True)
    summary = []
    for variant in VARIANTS:
        records = []
        repeats = repeats_for(variant)
        print(f"\n== {variant} ({repeats} repeats) ==", flush=True)
        for i in range(repeats):
            rec = run_one(variant, i, _key())
            (root / "raw" / f"{variant}__{i:02d}.json").write_text(
                json.dumps(rec, indent=2) + "\n")
            if rec["ok"]:
                print(f"  {i:02d} wall={rec['wall_seconds']:.3f}s "
                      f"in={rec['input_tokens']} out={rec['output_tokens']} "
                      f"cost=${rec['cost_usd']:.7f}", flush=True)
            else:
                print(f"  {i:02d} ERROR {rec['error']}", flush=True)
            records.append(rec)
        ok = [r for r in records if r["ok"]]
        summary.append({
            "variant": variant,
            "repeats": repeats,
            "ok": len(ok),
            "errors": len(records) - len(ok),
        })
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return 0


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
    return s[idx]


def _consistency(records: list[dict]) -> dict:
    """Look at noul probability distribution across repeats of the same call."""
    nouls = []
    for r in records:
        if not r.get("ok"):
            continue
        ans = r.get("answers") or {}
        for v in ans.values():
            if isinstance(v, dict) and v.get("type") == "noul":
                nouls.append(v.get("noul"))
                break
    if not nouls:
        return {}
    return {
        "n": len(nouls),
        "min": min(nouls), "max": max(nouls),
        "median": round(statistics.median(nouls), 4),
        "stdev": round(statistics.stdev(nouls), 4) if len(nouls) > 1 else 0.0,
        "range": round(max(nouls) - min(nouls), 4),
    }


def cmd_report(args) -> int:
    root = Path(args.root).resolve()
    raw = root / "raw"
    by_variant: dict[str, list[dict]] = {}
    for path in sorted(raw.glob("*.json")):
        rec = json.loads(path.read_text())
        by_variant.setdefault(rec["variant"], []).append(rec)
    print(f"variants={len(by_variant)} total_calls={sum(len(v) for v in by_variant.values())}\n")

    header = (f"{'variant':12s} {'n':>3s} {'ok':>3s} {'in_tok':>7s} "
              f"{'out_tok':>7s} {'p50 s':>6s} {'p95 s':>6s} {'min s':>6s} "
              f"{'max s':>6s} {'cost$':>9s}")
    print(header)
    for variant in VARIANTS:
        records = by_variant.get(variant, [])
        ok = [r for r in records if r.get("ok")]
        if not ok:
            print(f"{variant:12s} {len(records):3d} {len(ok):3d}  (no ok calls)")
            continue
        walls = [r["wall_seconds"] for r in ok]
        in_tok = sum(r["input_tokens"] for r in ok)
        out_tok = sum(r["output_tokens"] for r in ok)
        cost = sum(r["cost_usd"] for r in ok)
        print(f"{variant:12s} {len(records):3d} {len(ok):3d} {in_tok:7d} "
              f"{out_tok:7d} {_percentile(walls, 0.5):6.3f} "
              f"{_percentile(walls, 0.95):6.3f} {min(walls):6.3f} {max(walls):6.3f} "
              f"{cost:9.7f}")
    print("\n== consistency (noul probability across repeats) ==")
    cons = _consistency(by_variant.get("consistency", []))
    if cons:
        print(json.dumps(cons, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--root", required=True)
    run.set_defaults(func=cmd_run)
    rep = sub.add_parser("report")
    rep.add_argument("--root", required=True)
    rep.set_defaults(func=cmd_report)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

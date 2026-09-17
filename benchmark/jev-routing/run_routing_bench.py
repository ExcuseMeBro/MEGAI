#!/usr/bin/env python3
"""Jev-routed model choice between Pi's deepseek-flash and MiniMax-M3 models.

Arms
  pi:deepseek/deepseek-flash  fixed baseline
  pi:minimax/MiniMax-M3       fixed baseline
  jev-route                   one Jev model-choice call per request, then the chosen
                              model answers the identical prompt

The fixture, the strict-JSON answer prompt and the Pi/Jev plumbing are imported from
``benchmark/typesafe-jev`` so every arm answers the same requests under the same policy
text; only the model-selection interface differs.

  python3 run_routing_bench.py run --root DIR --results DIR/trials.jsonl
  python3 run_routing_bench.py report --results DIR/trials.jsonl

Raw responses stay in --root. The jev arm needs TYPESAFE_API_KEY in the environment; it
is never written to a record. A failed routing call falls back to the cheaper model and
is recorded, never retried.

Reading the numbers: the oracle is the cheapest fixed arm that answered an item fully
correctly, so it is an upper bound built from the same run, not a model's real
capability. The set is small (24 items, one run each): treat one- or two-item gaps as
noise. The work here is triage answering, not whole-repository implementation, so a
routing win on this set is evidence about triage only.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "typesafe-jev"))

from run_jev_bench import (  # noqa: E402
    JEV_USD_PER_INPUT_TOKEN,
    jev_ask,
    load,
    normalize,
    parse_json_answer,
    pi_ask,
    pi_prompt,
    slug,
)

DEEPSEEK = "pi:deepseek/deepseek-flash"
MINIMAX = "pi:minimax/MiniMax-M3"
ROUTE = "jev-route"
ARMS = (DEEPSEEK, MINIMAX, ROUTE)
DEFAULT_ITEMS = HERE.parent / "typesafe-jev" / "items.json"

# The candidate descriptions are the only difference between a routed and a fixed run:
# both models exist in the user's configuration, so the choice is about the work.
ROUTE_INSTRUCTION = (
    "Two models are available to answer this request. `deepseek-flash` is fast and cheap. "
    "`MiniMax-M3` is slower and about eight times more expensive per answer. Choose the "
    "model most likely to answer this request correctly for the lowest cost."
)
ROUTE_QUESTIONS = {
    "model": {
        "type": "choice",
        "instructions": "Which candidate model should answer this request? Judge the work "
                        "the request describes, not its length.",
        "criteria": {
            "deepseek-flash": "Fast and cheap; fits bounded, clearly specified work such as a "
                              "one-file fix, a test, docs or a routine configuration change",
            "MiniMax-M3": "Slower and about eight times more expensive; reserve it for work that "
                          "is ambiguous, cross-module or needs more reasoning than a bounded change",
            "either": "Both would plausibly do this work; prefer the cheaper model",
        },
    },
    "hard": {
        "type": "noul",
        "instructions": "True if this request needs more reasoning than a bounded, clearly "
                        "specified change.",
    },
}

def route_state(policy: dict, request: str) -> dict:
    return {"candidates": ["deepseek-flash", "MiniMax-M3"], "instruction": ROUTE_INSTRUCTION,
            "policy": policy, "request": request}


def score(parsed: dict | None, label: dict) -> dict:
    """Per-item correctness against the author label, mirroring the triage benchmark."""
    if not parsed:
        return {"type_ok": False, "effort_ok": False, "effort_delta": None,
                "approval_ok": False, "all_ok": False}
    delta = None if parsed["effort"] is None else parsed["effort"] - label["effort"]
    record = {
        "type_ok": parsed["type"] == label["type"],
        "effort_ok": parsed["effort"] == label["effort"],
        "effort_delta": delta,
        "approval_ok": parsed["needs_approval"] == label["needs_approval"],
    }
    record["all_ok"] = bool(record["type_ok"] and record["effort_ok"] and record["approval_ok"])
    return record


def run_item(arm: str, policy: dict, item: dict, cwd: Path, key: str | None) -> dict:
    prompt = pi_prompt(policy, item["request"])
    started = time.time()
    chosen = arm
    route = None
    error = None
    router_cost = 0.0
    router_wall = 0.0
    if arm == ROUTE:
        try:
            response = jev_ask(route_state(policy, item["request"]), key or "", ROUTE_QUESTIONS)
        except Exception as exc:  # noqa: BLE001 - recorded, never raised
            error = f"route call failed: {type(exc).__name__}: {exc}"
            chosen = DEEPSEEK
        else:
            answers = response.get("answers") or {}
            choice = answers.get("model") or {}
            noul = answers.get("hard") or {}
            label = choice.get("choice") if isinstance(choice.get("choice"), str) else ""
            route = {"choice": label, "confidence": choice.get("confidence"),
                     "probabilities": choice.get("probabilities"), "hard": noul.get("noul")}
            usage = response.get("usage") or {}
            router_cost = round((usage.get("input_tokens") or 0) * JEV_USD_PER_INPUT_TOKEN, 9)
            router_wall = round(time.time() - started, 3)
            chosen = MINIMAX if label == "MiniMax-M3" else DEEPSEEK
            if not label:
                error = "routing answer carried no model choice; fell back to deepseek-flash"
    text, usage, meta = pi_ask(chosen, prompt, cwd)
    parsed, parse_error = normalize(parse_json_answer(text))
    record = {
        "arm": arm,
        "chosen_arm": chosen,
        "item_id": item["id"],
        "label": item["label"],
        "raw_answer": text.strip()[:2000],
        "parsed": parsed,
        "parse_error": parse_error,
        "route": route,
        "router_cost_usd": router_cost,
        "router_wall_seconds": router_wall,
        "reported_models": meta["reported_models"],
        "exit_status": meta["exit_status"],
        "stderr_tail": meta["stderr_tail"],
        "error": error,
        "wall_seconds": round(time.time() - started, 3),
        "input_tokens": usage["input"],
        "output_tokens": usage["output"],
        "cache_read_tokens": usage["cache_read"],
        "cost_usd": round(usage["cost_usd"] + router_cost, 9),
    }
    record.update(score(parsed, item["label"]))
    return record


def analyze(rows: list[dict], items: list[dict]) -> dict:
    """Routing quality against the per-item oracle built from the fixed arms."""
    per_item: dict[str, dict[str, dict]] = {}
    for row in rows:
        per_item.setdefault(row["item_id"], {})[row["arm"]] = row
    out: dict = {
        "per_item": per_item, "items": len(items), "complete": 0, "missing": [],
        "route_deepseek": 0, "route_minimax": 0, "route_failed": 0, "oracle": {},
        "matched": 0, "lost": [], "neither_correct": 0, "oracle_pick_hit": 0,
        "route_cost": 0.0, "oracle_cost": 0.0, "deepseek_cost": 0.0, "minimax_cost": 0.0,
        "route_ok": 0, "deepseek_ok": 0, "minimax_ok": 0, "replay_agree": 0, "replay_diff": [],
        "hard_ok": [], "hard_bad": [], "confidence_ok": [], "confidence_bad": [],
    }
    for item in items:
        records = per_item.get(item["id"], {})
        if not all(arm in records for arm in ARMS):
            out["missing"].append(item["id"])
            continue
        out["complete"] += 1
        deepseek, minimax, routed = records[DEEPSEEK], records[MINIMAX], records[ROUTE]
        out["deepseek_cost"] += deepseek["cost_usd"]
        out["minimax_cost"] += minimax["cost_usd"]
        out["route_cost"] += routed["cost_usd"]
        out["deepseek_ok"] += bool(deepseek["all_ok"])
        out["minimax_ok"] += bool(minimax["all_ok"])
        out["route_ok"] += bool(routed["all_ok"])
        correct = [arm for arm in (DEEPSEEK, MINIMAX) if records[arm]["all_ok"]]
        if correct:
            best = min(correct, key=lambda arm: records[arm]["cost_usd"])
            out["oracle"][best] = out["oracle"].get(best, 0) + 1
            out["oracle_cost"] += records[best]["cost_usd"]
            if routed["all_ok"]:
                out["matched"] += 1
            else:
                out["lost"].append(item["id"])
        else:
            out["neither_correct"] += 1
            out["oracle_cost"] += min(deepseek["cost_usd"], minimax["cost_usd"])
        chosen = routed["chosen_arm"]
        out["route_minimax" if chosen == MINIMAX else "route_deepseek"] += 1
        # Same model, same prompt, second run: how often the routed answer replays the
        # fixed arm's answer. Any gap here is run-to-run variance, not a routing effect.
        if routed["parsed"] == records[chosen]["parsed"]:
            out["replay_agree"] += 1
        else:
            out["replay_diff"].append(item["id"])
        if chosen in correct:
            out["oracle_pick_hit"] += 1
        detail = routed.get("route") or {}
        if detail.get("choice") is None:
            out["route_failed"] += 1
        hard, confidence = detail.get("hard"), detail.get("confidence")
        if isinstance(hard, (int, float)):
            (out["hard_ok"] if routed["all_ok"] else out["hard_bad"]).append(float(hard))
        if isinstance(confidence, (int, float)):
            (out["confidence_ok"] if routed["all_ok"] else out["confidence_bad"]).append(
                float(confidence))
    return out


def _arm_table(rows: list[dict], arm: str) -> str:
    selected = [row for row in rows if row["arm"] == arm]
    if not selected:
        return f"{arm:28s} missing"
    walls = sorted(row["wall_seconds"] for row in selected)
    p95 = walls[min(len(walls) - 1, int(round(0.95 * (len(walls) - 1))))]
    deltas = [row["effort_delta"] for row in selected if row["effort_delta"] is not None]
    return (f"{arm:28s} {len(selected):3d} "
            f"{sum(row['type_ok'] for row in selected):5d} "
            f"{sum(row['effort_ok'] for row in selected):6d} "
            f"{sum(1 for delta in deltas if delta <= 1):4d} "
            f"{sum(row['approval_ok'] for row in selected):6d} "
            f"{sum(row['all_ok'] for row in selected):5d} "
            f"{sum(1 for row in selected if row['parse_error']):4d} "
            f"{statistics.median(walls):6.1f} {p95:6.1f} "
            f"{sum(row['cost_usd'] for row in selected):9.6f}")


def report(items_path: Path, results_path: Path) -> int:
    fixture = json.loads(Path(items_path).read_text())
    rows = load(results_path)
    analysis = analyze(rows, fixture["items"])
    order = [arm for arm in ARMS if any(row["arm"] == arm for row in rows)]
    order += sorted({row["arm"] for row in rows} - set(order))
    print(f"items={len(fixture['items'])} records={len(rows)} arms={order}")
    print(f"{'arm':28s} {'n':>3s} {'type':>5s} {'effort':>6s} {'±1':>4s} {'approv':>6s} "
          f"{'all3':>5s} {'bad':>4s} {'p50s':>6s} {'p95s':>6s} {'cost$':>9s}")
    for arm in order:
        print(_arm_table(rows, arm))
    print("cols: type=exact type hits, effort=exact level hits, ±1=within one level, "
          "approv=approval hits, all3=whole answer correct, bad=parse/OOV failures")
    complete = analysis["complete"]
    print("== routing ==")
    print(f"items with all three arms: {complete}/{analysis['items']}"
          + (f" (missing {analysis['missing']})" if analysis["missing"] else ""))
    if not complete:
        return 1
    print(f"routed to deepseek-flash: {analysis['route_deepseek']} | "
          f"MiniMax-M3: {analysis['route_minimax']} | "
          f"routing call failed (fell back to deepseek): {analysis['route_failed']}")
    oracle = ", ".join(f"{arm.split(':')[-1]}={count}"
                       for arm, count in sorted(analysis["oracle"].items())) or "none"
    print(f"oracle (cheapest fully-correct fixed arm): {oracle}; "
          f"neither fixed arm correct: {analysis['neither_correct']}")
    print(f"router picked a fully-correct fixed arm: {analysis['oracle_pick_hit']}/{complete}")
    print(f"routed arm answered fully correctly: {analysis['route_ok']}/{complete} "
          f"(deepseek {analysis['deepseek_ok']}, minimax {analysis['minimax_ok']})")
    lost = analysis["lost"]
    print(f"lost correctness (routed failed where a fixed arm passed): {len(lost)}"
          + (f" [{', '.join(lost)}]" if lost else ""))
    diff = analysis["replay_diff"]
    print(f"same-model replay: the routed run answered identically to that model's fixed "
          f"run on {analysis['replay_agree']}/{complete} items"
          + (f"; differing {diff} are run-to-run variance, not a routing effect" if diff else ""))
    print(f"cost: routed ${analysis['route_cost']:.6f} | always-deepseek "
          f"${analysis['deepseek_cost']:.6f} | always-minimax ${analysis['minimax_cost']:.6f} | "
          f"oracle (cheapest correct arm per item, an upper bound) ${analysis['oracle_cost']:.6f}")
    cheap = analysis["deepseek_cost"] or 1.0
    print(f"routed cost is {analysis['route_cost'] / cheap:.2f}x always-deepseek and "
          f"{analysis['route_cost'] / (analysis['minimax_cost'] or 1.0):.2f}x always-minimax")
    for key, label in (("hard", "mean Jev `hard` (needs more reasoning)"),
                       ("confidence", "mean Jev model-choice confidence")):
        good, bad = analysis[f"{key}_ok"], analysis[f"{key}_bad"]
        print(f"{label}: correct "
              f"{statistics.mean(good):.2f} (n={len(good)})" if good else
              f"{label}: correct n=0")
        if bad:
            print(f"{label}: incorrect {statistics.mean(bad):.2f} (n={len(bad)})")
    print("== per item (label | fixed arms | routed) ==")
    for item in fixture["items"]:
        records = analysis["per_item"].get(item["id"], {})
        cells = []
        for arm in (DEEPSEEK, MINIMAX):
            row = records.get(arm)
            cells.append("missing" if row is None else
                         f"{'ok ' if row['all_ok'] else 'XX '}{(row['parsed'] or {}).get('type')}/"
                         f"{(row['parsed'] or {}).get('effort')}/"
                         f"{(row['parsed'] or {}).get('needs_approval')}")
        routed = records.get(ROUTE)
        if routed is None:
            cells.append("missing")
        else:
            detail = routed.get("route") or {}
            cells.append(f"{'ok ' if routed['all_ok'] else 'XX '}"
                         f"{detail.get('choice')}->{(routed['parsed'] or {}).get('type')}/"
                         f"{(routed['parsed'] or {}).get('effort')}/"
                         f"{(routed['parsed'] or {}).get('needs_approval')}")
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
    if ROUTE in arms and not key:
        raise SystemExit("TYPESAFE_API_KEY is required for the jev-route arm")
    done = {(row["arm"], row["item_id"]) for row in load(results_path)}
    for item in fixture["items"]:
        for arm in arms:
            if (arm, item["id"]) in done:
                print(f"skip {arm} {item['id']}", flush=True)
                continue
            record = run_item(arm, policy, item, cwd, key)
            (root / f"{slug(arm)}__{item['id']}.json").write_text(
                json.dumps(record, indent=2) + "\n")
            with results_path.open("a") as handle:
                handle.write(json.dumps(record) + "\n")
            detail = record.get("route") or {}
            print(f"{item['id']} {arm:28s} wall={record['wall_seconds']:6.1f}s "
                  f"chose={detail.get('choice') or '-'} "
                  f"ok={record['all_ok']} cost=${record['cost_usd']:.6f} "
                  f"err={record['parse_error'] or record['error'] or '-'}", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--items", default=str(DEFAULT_ITEMS))
    run.add_argument("--root", required=True)
    run.add_argument("--results", required=True)
    run.add_argument("--arms", default="")
    run.set_defaults(func=cmd_run)
    rep = sub.add_parser("report")
    rep.add_argument("--items", default=str(DEFAULT_ITEMS))
    rep.add_argument("--results", required=True)
    rep.set_defaults(func=lambda a: report(Path(a.items), Path(a.results).resolve()))
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

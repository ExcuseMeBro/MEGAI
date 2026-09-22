#!/usr/bin/env python3
"""Label and read the live Laya decision ledger.

`laya` appends one JSONL line per local decision to `~/.megai/laya-calls.jsonl`
(`LAYA_LOG` moves that file, `LAYA_LOG=0` turns it off). This closes the loop that
file exists for. `note` appends what actually happened for one recorded decision,
keyed by the short record id the tool prints; `report` joins answers to outcomes and
prints what is worth acting on: how often the local answer matched the real outcome
per question, what its probabilities are worth as a cutoff, the routes that answered
and the rows where the two disagreed — the rows worth turning into a test set.

It reads and appends to that one file, starts no model and makes no request, and
prints no state: the ledger never stores the state sent to the model, and neither
does this.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_LEDGER = Path.home() / ".megai/laya-calls.jsonl"
CUTOFFS = (0.5, 0.6, 0.7, 0.8, 0.9)
YES = {"yes", "true", "1", "y"}
NO = {"no", "false", "0", "n"}


def ledger_path() -> Path | None:
    """The ledger `laya` writes to, or None when `LAYA_LOG=0` turned logging off."""
    value = os.environ.get("LAYA_LOG", "").strip()
    if value == "0":
        return None
    return Path(value) if value else DEFAULT_LEDGER


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def read_rows(path: Path) -> list[dict[str, Any]]:
    """Every readable ledger row. A missing file is an empty ledger, and one
    half-written trailing line is skipped rather than failing the read."""
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def split(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[tuple[str, str], str]]:
    """Calls, failures and the outcome labels, the latter keyed by (record id,
    question id). A label without `--question` covers every question of that call."""
    calls: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    labels: dict[tuple[str, str], str] = {}
    for row in rows:
        if row.get("kind") == "actual":
            labels[(str(row.get("id") or ""), str(row.get("question") or "*"))] = str(row.get("actual") or "")
        elif row.get("answers"):
            calls.append(row)
        else:
            failures.append(row)
    return calls, failures, labels


def call_id(row: dict[str, Any]) -> str:
    return str(row.get("id") or "")


def questions_of(row: dict[str, Any]) -> dict[str, Any]:
    answers = row.get("answers")
    return answers if isinstance(answers, dict) else {}


def confidence(entry: dict[str, Any]) -> float | None:
    """The probability the model put on the answer it gave: `confidence` when the
    checkpoint reports it, otherwise the weight of the picked choice."""
    value = entry.get("confidence")
    if isinstance(value, (int, float)):
        return float(value)
    probabilities = entry.get("probabilities")
    if isinstance(probabilities, dict):
        weight = probabilities.get(entry.get("answer"))
        if isinstance(weight, (int, float)):
            return float(weight)
    return None


def probability(entry: dict[str, Any], kind: str, value: Any) -> float | None:
    """The number a cutoff applies to: a `noul` answer *is* its probability, and a
    `choice` answer is judged on the weight it put on the label it picked."""
    if kind == "noul":
        return float(value) if isinstance(value, (int, float)) else None
    return confidence(entry)


def agrees(kind: str, value: Any, actual: str) -> bool | None:
    """Whether the recorded answer matched the outcome, or None when the pair is
    not comparable — a `score` level has no right answer, and a `noul` outcome has
    to read as yes or no to mean anything."""
    actual = actual.strip().lower()
    if kind == "noul":
        if not isinstance(value, (int, float)):
            return None
        if actual in YES:
            said = True
        elif actual in NO:
            said = False
        else:
            return None
        return (float(value) >= 0.5) == said
    if kind == "choice":
        return str(value).strip().lower() == actual
    return None


def collect(calls: list[dict[str, Any]], labels: dict[tuple[str, str], str]) -> dict[str, dict[str, Any]]:
    """Per question id: how often it was asked, the recorded answers and, when a
    label exists, whether the answer matched the outcome."""
    seen: dict[str, dict[str, Any]] = collections.OrderedDict()
    for row in calls:
        for qid, entry in questions_of(row).items():
            if not isinstance(entry, dict):
                continue
            bucket = seen.setdefault(qid, {"type": str(entry.get("type") or "?"), "asked": 0, "seen": []})
            bucket["asked"] += 1
            actual = labels.get((call_id(row), qid))
            if actual is None:
                actual = labels.get((call_id(row), "*"))
            bucket["seen"].append({
                "value": entry.get("answer"),
                "p": probability(entry, bucket["type"], entry.get("answer")),
                "confidence": confidence(entry),
                "actual": actual,
                "agrees": None if actual is None else agrees(bucket["type"], entry.get("answer"), actual),
                "id": call_id(row),
                "route": str(row.get("route") or ""),
            })
    return seen


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def number(value: float | None, digits: int = 2) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def percent(matched: int, total: int) -> str:
    return "—" if not total else f"{100 * matched / total:.1f}%"


def quantile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))]


def disagreements_of(questions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """The rows where the local answer and the recorded outcome differ, flattened
    with their question id: the free test set a later calibration wants."""
    rows = []
    for qid, bucket in questions.items():
        for row in bucket["seen"]:
            if row["agrees"] is False:
                rows.append({**row, "question": qid})
    return rows


def counts(rows: list[dict[str, Any]], key: str, fallback: str) -> str:
    """`english 12, multilingual 3` — which route or checkpoint answered, and how
    often: a calibration is retuned per language family, not per call."""
    counted = collections.Counter(str(row.get(key) or fallback) for row in rows)
    return ", ".join(f"{name} {count}" for name, count in counted.most_common()) or "none"


def report(path: Path, calls: list[dict[str, Any]], failures: list[dict[str, Any]], questions: dict[str, dict[str, Any]]) -> str:
    sources = collections.Counter(str(row.get("source") or "unknown") for row in calls + failures)
    labeled = sum(1 for bucket in questions.values() for row in bucket["seen"] if row["agrees"] is not None)
    asked = sum(bucket["asked"] for bucket in questions.values())
    lines = [
        f"ledger: {path}",
        f"lines: {len(calls) + len(failures)}  calls: {len(calls)}  failed: {len(failures)}",
        "sources: " + (", ".join(f"{name} {count}" for name, count in sources.most_common()) or "none"),
        f"routes: {counts(calls, 'route', 'unknown')}",
        f"models: {counts(calls, 'model', 'unknown')}",
        f"languages: {counts(calls, 'lang', 'auto')}",
        f"labeled answers: {labeled} of {asked}",
        "",
        "questions",
        f"{'question':<22} {'type':<7} {'n':>4} {'mean':>6} {'p50':>6} {'0.5+':>6} {'0.65+':>6} {'0.85+':>6}",
    ]
    for qid, bucket in questions.items():
        probabilities = [row["p"] for row in bucket["seen"] if row["p"] is not None]
        above = [sum(1 for p in probabilities if p >= cut) for cut in (0.5, 0.65, 0.85)]
        lines.append(
            f"{qid:<22} {bucket['type']:<7} {bucket['asked']:>4} {number(mean(probabilities)):>6} "
            f"{number(quantile(probabilities, 0.5)):>6} {above[0]:>6} {above[1]:>6} {above[2]:>6}"
        )

    lines.append("probability = a `noul` answer, or the weight on the picked `choice`")

    scored = {qid: bucket for qid, bucket in questions.items() if any(r["agrees"] is not None for r in bucket["seen"])}
    if not scored:
        lines += ["", "no outcome labels yet: `laya_shadow.py note --id <record id> --actual <label>`"]
        return "\n".join(lines)

    lines += ["", "outcome", f"{'question':<22} {'n':>4} {'agree':>7} {'mean P right/wrong':>20}"]
    for qid, bucket in scored.items():
        rows = [row for row in bucket["seen"] if row["agrees"] is not None]
        right = [row["p"] for row in rows if row["agrees"] and row["p"] is not None]
        wrong = [row["p"] for row in rows if not row["agrees"] and row["p"] is not None]
        lines.append(
            f"{qid:<22} {len(rows):>4} {percent(sum(1 for r in rows if r['agrees']), len(rows)):>7} "
            f"{number(mean(right))}/{number(mean(wrong))}"
        )

    noul = [row for bucket in questions.values() if bucket["type"] == "noul" for row in bucket["seen"]
            if row["agrees"] is not None and row["p"] is not None]
    if noul:
        lines += ["", f"noul cutoffs (labeled n={len(noul)})", f"{'cut':>5} {'cases':>6} {'actual yes':>11}"]
        for cut in CUTOFFS:
            above = [row for row in noul if row["p"] >= cut]
            yes = sum(1 for row in above if row["agrees"])
            lines.append(f"{cut:>5.2f} {len(above):>6} {percent(yes, len(above)):>11}")

    rows = disagreements_of(questions)
    lines += ["", f"disagreements ({len(rows)} rows, the next test set)"]
    if rows:
        lines.append(f"{'id':<10} {'question':<22} {'model':<24} {'actual':<24} {'P':>5}")
        for row in rows:
            lines.append(
                f"{row['id']:<10} {row['question']:<22} {str(row['value']):<24} {str(row['actual']):<24} {number(row['p']):>5}"
            )
    return "\n".join(lines)


def note(path: Path, args: argparse.Namespace) -> int:
    calls, _, _ = split(read_rows(path))
    by_id = {call_id(row): row for row in calls}
    if args.id not in by_id:
        print(f"no recorded call with id {args.id!r} in {path}", file=sys.stderr)
        return 1
    asked = sorted(questions_of(by_id[args.id]))
    if args.question and args.question not in asked:
        print(f"{args.id} asked no question {args.question!r}; it asked: {', '.join(asked) or 'none'}", file=sys.stderr)
        return 1
    row = {"kind": "actual", "id": args.id, "question": args.question or None, "actual": args.actual,
           "source": args.source, "note": args.note or None, "t": now()}
    write(path, {key: value for key, value in row.items() if value is not None})
    what = args.question or f"all of {', '.join(asked) or 'no questions'}"
    print(f"labeled {args.id} ({what}): {args.actual}")
    return 0


def write(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="laya_shadow.py",
        description="Label what actually happened for a recorded Laya decision, and read the ledger back.",
    )
    parser.add_argument("--path", help="ledger file (default: LAYA_LOG, else ~/.megai/laya-calls.jsonl)")
    actions = parser.add_subparsers(dest="action", required=True)
    noting = actions.add_parser("note", help="append the real outcome for one recorded decision")
    noting.add_argument("--id", required=True, help="the record id the laya tool printed")
    noting.add_argument("--actual", required=True, help="what really happened")
    noting.add_argument("--question", default="", help="one question id; omit to label every question of that call")
    noting.add_argument("--source", default="agent", help="who labeled it (default: agent)")
    noting.add_argument("--note", default="", help="a short free-text note")
    actions.add_parser("report", help="agreement, probability cutoffs and disagreements from the ledger")
    args = parser.parse_args(argv)

    path = Path(args.path) if args.path else ledger_path()
    if path is None:
        print("ledger is off (`LAYA_LOG=0`)", file=sys.stderr)
        return 1
    if args.action == "note":
        return note(path, args)

    rows = read_rows(path)
    calls, failures, labels = split(rows)
    print(report(path, calls, failures, collect(calls, labels)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

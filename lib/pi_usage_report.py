#!/usr/bin/env python3
"""Read-only Pi session usage report for efficiency work.

Aggregates Pi JSONL session logs into the numbers that actually drive cost:
prompt size per assistant turn, turns per session, reported cost per model,
tool-call batching and the replay amplification of retained tool output.

It writes nothing, makes no provider request and prints no transcript content,
message text, session file path or working directory. `--by-project` is the only
mode that prints a local path fragment; it is off by default.

Reported cost and token counters are observations from the session log, not
billed amounts. `replay_tokens_estimate` is an explicit estimate: it assumes a
retained tool result is re-sent on every later assistant request and ignores
compaction, so it is an upper bound, not a measured re-send count.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ESTIMATE_BASIS = "chars/4"
BUCKETS = ((0, 50_000), (50_000, 100_000), (100_000, 200_000), (200_000, None))
BUCKET_LABELS = ("under_50k", "50k_to_100k", "100k_to_200k", "at_least_200k")


def agent_dir() -> Path:
    return Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi/agent"))


def parse_time(value: str | None) -> float | None:
    if value is None:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as error:
        raise ValueError(f"unparseable timestamp: {value}") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def number(value: Any) -> float | None:
    """Return a non-negative finite number; booleans and junk are missing, not zero."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value or value in (float("inf"), float("-inf")) or value < 0:
        return None
    return float(value)


def event_time(entry: dict[str, Any]) -> float | None:
    stamp = entry.get("timestamp")
    if not isinstance(stamp, str):
        return None
    try:
        return parse_time(stamp)
    except ValueError:
        return None


def content_length(message: dict[str, Any]) -> int:
    return len(json.dumps(message.get("content"), separators=(",", ":")))


def tool_name(message: dict[str, Any], call_names: dict[str, str]) -> str:
    for key in ("toolName", "tool", "name"):
        value = message.get(key)
        if isinstance(value, str) and value:
            return value
    call_id = message.get("toolCallId") or message.get("toolUseId")
    if isinstance(call_id, str) and call_id in call_names:
        return call_names[call_id]
    return "unknown"


def session_entries(path: Path) -> list[dict[str, Any]]:
    entries = []
    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            entries.append({"type": "malformed"})
            continue
        if isinstance(entry, dict):
            entries.append(entry)
        else:
            entries.append({"type": "malformed"})
    return entries


class Aggregate:
    def __init__(self) -> None:
        self.models: dict[str, dict[str, Any]] = {}
        self.totals = collections.Counter()
        self.buckets: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
        self.tools: dict[str, dict[str, Any]] = {}
        self.projects: dict[str, dict[str, Any]] = collections.defaultdict(
            lambda: {"sessions": 0, "turns": 0, "reported_cost": 0.0, "total_tokens": 0})

    def model(self, key: str) -> dict[str, Any]:
        return self.models.setdefault(key, {
            "turns": 0, "input": 0.0, "output": 0.0, "cacheRead": 0.0, "cacheWrite": 0.0,
            "totalTokens": 0.0, "reported_cost": 0.0, "cost_objects": 0,
            "usage_objects": 0, "usage_objects_complete": 0, "prompt_tokens": 0.0,
            "missing_usage": 0, "cost_missing": 0, "contexts": [],
        })

    def tool(self, name: str) -> dict[str, Any]:
        return self.tools.setdefault(name, {"calls": 0, "chars": 0, "replay_replays": 0,
                                            "replay_tokens_estimate": 0.0})


def scan_session(path: Path, start: float | None, end: float | None, agg: Aggregate,
                 by_project: bool) -> dict[str, Any] | None:
    sequence: list[tuple[str, Any]] = []
    call_names: dict[str, str] = {}
    malformed = 0
    compactions = 0
    summarization: list[Any] = []
    for entry in session_entries(path):
        kind = entry.get("type")
        if kind == "malformed":
            malformed += 1
            continue
        if kind == "compaction":
            compactions += 1
            summarization.append(entry.get("usage"))
            continue
        if kind == "branch_summary":
            summarization.append(entry.get("usage"))
            continue
        if kind != "message":
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        stamp = event_time(entry)
        if stamp is not None and ((start is not None and stamp < start) or (end is not None and stamp > end)):
            continue
        role = message.get("role")
        if role == "assistant":
            for block in message.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "toolCall":
                    call_id = block.get("id") or block.get("toolCallId")
                    if isinstance(call_id, str):
                        name = block.get("name")
                        call_names[call_id] = name if isinstance(name, str) and name else "unknown"
            sequence.append(("assistant", (message, entry)))
        elif role == "toolResult":
            sequence.append(("toolResult", message))
    turns = [item for kind, item in sequence if kind == "assistant"]
    if not turns:
        return None
    # Walk backwards so each retained tool result is counted once per later
    # assistant request. Compaction is not modelled: this is an upper bound.
    remaining = 0
    replay_tokens: collections.Counter = collections.Counter()
    calls_by_tool: collections.Counter = collections.Counter()
    chars_by_tool: collections.Counter = collections.Counter()
    replay_counts: collections.Counter = collections.Counter()
    batching: collections.Counter = collections.Counter()
    for index in range(len(sequence) - 1, -1, -1):
        kind, item = sequence[index]
        if kind == "assistant":
            remaining += 1
            continue
        name = tool_name(item, call_names)
        chars = content_length(item)
        replay_counts[name] += remaining
        replay_tokens[name] += (chars // 4) * remaining
        calls_by_tool[name] += 1
        chars_by_tool[name] += chars
    for kind, item in sequence:
        if kind != "assistant":
            continue
        calls = [b for b in (item[0].get("content") or [])
                 if isinstance(b, dict) and b.get("type") == "toolCall"]
        batching[min(len(calls), 5)] += 1
        agg.totals["tool_calls"] += len(calls)
    session_cost = 0.0
    session_tokens = 0.0
    for message, _entry in turns:
        provider = message.get("provider") if isinstance(message.get("provider"), str) else "unknown"
        model = message.get("model") if isinstance(message.get("model"), str) else "unknown"
        block = agg.model(f"{provider}/{model}")
        block["turns"] += 1
        usage = message.get("usage")
        if not isinstance(usage, dict):
            block["missing_usage"] += 1
            continue
        block["usage_objects"] += 1
        values = {key: number(usage.get(key)) for key in ("input", "output", "cacheRead", "cacheWrite")}
        if all(value is not None for value in values.values()):
            block["usage_objects_complete"] += 1
        present = [value for value in values.values() if value is not None]
        block["prompt_tokens"] += sum(value for value in (values["input"], values["cacheRead"]) if value)
        for key, value in values.items():
            if value is not None:
                block[key] += value
        total = number(usage.get("totalTokens"))
        if total is not None:
            block["totalTokens"] += total
            session_tokens += total
        elif present:
            summed = sum(present)
            block["totalTokens"] += summed
            session_tokens += summed
        context = sum(value for value in (values["input"], values["cacheRead"]) if value)
        block["contexts"].append(context)
        for label, (low, high) in zip(BUCKET_LABELS, BUCKETS):
            if context >= low and (high is None or context < high):
                agg.buckets[f"{provider}/{model}"][label] += 1
                break
        cost = usage.get("cost")
        if isinstance(cost, dict) and number(cost.get("total")) is not None:
            block["cost_objects"] += 1
            block["reported_cost"] += number(cost.get("total"))
            session_cost += number(cost.get("total"))
        else:
            block["cost_missing"] += 1
    for count, turns_with in batching.items():
        agg.totals[f"turns_with_{count}_toolcalls"] += turns_with
    agg.totals["sessions"] += 1
    agg.totals["turns"] += len(turns)
    agg.totals["compactions"] += compactions
    agg.totals["malformed_lines"] += malformed
    for name, chars in chars_by_tool.items():
        block = agg.tool(name)
        block["calls"] += calls_by_tool[name]
        block["chars"] += chars
        block["replay_replays"] += replay_counts[name]
        block["replay_tokens_estimate"] += replay_tokens[name]
    for usage in summarization:
        # Compaction/branch-summary usage is real provider work; it is reported
        # separately so the window-cap trade-off can be judged, never hidden.
        if not isinstance(usage, dict):
            agg.totals["summarization_usage_missing"] += 1
            continue
        agg.totals["summarizations"] += 1
        for key in ("input", "output", "cacheRead", "cacheWrite"):
            value = number(usage.get(key))
            if value is not None:
                agg.totals[f"summarization_{key}"] += value
        cost = usage.get("cost")
        if isinstance(cost, dict) and number(cost.get("total")) is not None:
            agg.totals["summarization_reported_cost"] += number(cost.get("total"))
        else:
            agg.totals["summarization_cost_missing"] += 1
    if by_project:
        label = path.parent.name
        agg.projects[label]["sessions"] += 1
        agg.projects[label]["turns"] += len(turns)
        agg.projects[label]["reported_cost"] += session_cost
        agg.projects[label]["total_tokens"] += session_tokens
    return {"turns": len(turns), "reported_cost": session_cost}


def build_report(root: Path, days: float | None, start: float | None, end: float | None,
                 by_project: bool, limit: int | None) -> dict[str, Any]:
    if not root.is_dir():
        raise ValueError(f"session directory not found: {root}")
    cutoff = None if days is None else time.time() - days * 86400.0
    files = sorted(root.rglob("*.jsonl"))
    agg = Aggregate()
    newest: list[tuple[float, int, float]] = []
    used = 0
    for path in files:
        try:
            stat = path.stat()
        except OSError:
            continue
        if cutoff is not None and stat.st_mtime < cutoff:
            continue
        result = scan_session(path, start, end, agg, by_project)
        if result is None:
            continue
        used += 1
        newest.append((stat.st_mtime, result["turns"], result["reported_cost"]))
    newest.sort(reverse=True)
    models = {}
    for key, block in agg.models.items():
        turns = block.pop("turns")
        block.pop("contexts")
        prompt = block.pop("prompt_tokens")
        models[key] = dict(
            block,
            turns=turns,
            prompt_tokens=prompt,
            context_tokens_per_turn=(prompt / turns) if turns else None,
            reported_cost_per_turn=(block["reported_cost"] / turns) if turns else None,
            context_buckets=dict(agg.buckets.get(key, {})),
        )
    tools = {}
    for name, block in agg.tools.items():
        calls = block["calls"]
        tools[name] = dict(
            block,
            mean_chars=(block["chars"] / calls) if calls else None,
            estimate_basis=ESTIMATE_BASIS,
        )
    ordered = sorted(models.items(), key=lambda item: -item[1]["reported_cost"])
    if limit is not None:
        ordered = ordered[:limit]
    turns = agg.totals["turns"]
    return {
        "schema": 1,
        "basis": ("Observed session-log counters, not billed cost. cacheRead counters are cache "
                  "lookups re-sent per request; replay_tokens_estimate ignores compaction."),
        "estimate_basis": ESTIMATE_BASIS,
        "window": {"days": days, "sessions_matched": used, "sessions_scanned": len(files),
                   "sessions_shipped": len(newest)},
        "totals": {"turns": turns, "tool_calls": agg.totals["tool_calls"],
                   "batching": {f"{index}_tool_calls": agg.totals[f"turns_with_{index}_toolcalls"]
                                for index in range(6)},
                   "single_tool_call_ratio": (agg.totals["turns_with_1_toolcalls"] / turns) if turns else None,
                   "compactions": agg.totals["compactions"],
                   "summarization": {
                       "summarizations": agg.totals["summarizations"],
                       "input": agg.totals["summarization_input"],
                       "output": agg.totals["summarization_output"],
                       "cacheRead": agg.totals["summarization_cacheRead"],
                       "cacheWrite": agg.totals["summarization_cacheWrite"],
                       "reported_cost": agg.totals["summarization_reported_cost"],
                       "usage_missing": agg.totals["summarization_usage_missing"],
                       "cost_missing": agg.totals["summarization_cost_missing"],
                   },
                   "malformed_lines": agg.totals["malformed_lines"]},
        "models": models,
        "model_order": [key for key, _ in ordered],
        "tools": tools,
        "projects": dict(agg.projects) if by_project else None,
    }


def render(report: dict[str, Any]) -> str:
    lines = []
    totals = report["totals"]
    window = report["window"]
    lines.append(f"sessions={window['sessions_matched']}/{window['sessions_scanned']} "
                 f"days={window['days']} turns={totals['turns']} tool_calls={totals['tool_calls']} "
                 f"compactions={totals['compactions']}")
    summary = totals["summarization"]
    if summary["summarizations"]:
        lines.append(f"summarization work: {summary['summarizations']} calls, "
                     f"input {summary['input']:,.0f}, output {summary['output']:,.0f}, "
                     f"reported ${summary['reported_cost']:.2f}")
    single = totals["single_tool_call_ratio"]
    if single is not None:
        lines.append(f"turns with exactly one tool call: {single * 100:.1f}%   "
                     f"per-turn distribution: "
                     + " ".join(f"{key}={value}" for key, value in totals["batching"].items()))
    lines.append("")
    header = f"{'model':34}{'turns':>7}{'ctx/turn':>10}{'cost/turn':>11}{'reported$':>11}{'tokens':>14}"
    lines.append(header)
    for key in report["model_order"]:
        block = report["models"][key]
        context = block["context_tokens_per_turn"]
        per_turn = block["reported_cost_per_turn"]
        lines.append(f"{key:34}{block['turns']:>7}"
                     f"{(f'{context:,.0f}' if context else '-'):>10}"
                     f"{(f'${per_turn:.4f}' if per_turn is not None else '-'):>11}"
                     f"{block['reported_cost']:>11.2f}{block['totalTokens']:>14,.0f}")
    lines.append("")
    lines.append(f"{'tool':16}{'calls':>7}{'mean chars':>12}{'replay (est. tokens)':>22}")
    for name, block in sorted(report["tools"].items(), key=lambda item: -item[1]["replay_tokens_estimate"]):
        mean = block["mean_chars"] or 0
        lines.append(f"{name:16}{block['calls']:>7}{mean:>12,.0f}"
                     f"{block['replay_tokens_estimate']:>22,.0f}")
    if report["projects"]:
        lines.append("")
        lines.append(f"{'project label':28}{'sessions':>9}{'turns':>7}{'reported$':>11}")
        for label, block in sorted(report["projects"].items(), key=lambda item: -item[1]["reported_cost"]):
            lines.append(f"{label:28}{block['sessions']:>9}{block['turns']:>7}{block['reported_cost']:>11.2f}")
    lines.append("")
    lines.append(f"estimate basis: {report['estimate_basis']}; replay ignores compaction and is an upper bound")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--agent-dir", type=Path, default=None,
                        help="Pi agent directory (default: PI_CODING_AGENT_DIR or ~/.pi/agent)")
    parser.add_argument("--days", type=float, default=14.0,
                        help="only sessions modified within this many days (0 disables; default 14)")
    parser.add_argument("--since", default=None, help="ISO timestamp; keep entries at or after it")
    parser.add_argument("--until", default=None, help="ISO timestamp; keep entries at or before it")
    parser.add_argument("--by-project", action="store_true",
                        help="also print local session-directory labels (off by default)")
    parser.add_argument("--limit", type=int, default=None, help="limit models in the ordering")
    parser.add_argument("--text", action="store_true", help="human table instead of JSON")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be at least 1")
    days = None if not args.days or args.days <= 0 else args.days
    report = build_report(args.agent_dir or agent_dir(), days,
                          parse_time(args.since), parse_time(args.until),
                          args.by_project, args.limit)
    print(render(report) if args.text else json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        raise SystemExit(f"usage report: {error}") from error

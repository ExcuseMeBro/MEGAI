#!/usr/bin/env python3
"""Read-only metrics from Pi JSONL sessions for an explicit task boundary.

The helper aggregates one parent session plus any explicitly supplied child
sessions. Boundaries are entry IDs (ancestry selection on the active branch of
the end entry) or explicit timestamps (chronological selection across branches,
which cannot be mixed with entry IDs). It never emits transcript content or
session paths and never invents child tokens, provider wait time or billed cost.

Honesty rules:

* Reported usage/cost is an observed subtotal, never a claim of completeness.
  ``usage_complete``/``cost_complete`` say whether every expected source reported
  it; absent optional reasoning is ``null``, not a measured zero.
* ``observed_totals`` always sums what was observed. ``totals`` stays ``null``
  until the child scope is complete (``--children-complete``) and the observed
  usage/cost is itself complete.
* Numbers are validated: booleans, fractional or negative counters, NaN and
  Infinity are rejected rather than truncated or coerced.
* Session trees are validated up front; cyclic, dangling, or non-string parent
  links fail without walking forever. Naive timestamps are interpreted as UTC.
* Entries are deduplicated across a fork only when the lineage is verified and
  the shared entries are structurally identical (canonical JSON: sorted keys,
  normalized separators); a differing duplicate fails instead of guessing.
* ``usage_complete`` means recorded native accounting coverage: every assistant
  message recorded usage and the recorded usage/cost objects were complete. It is
  not billing proof; optional ``toolResult``/``compaction``/``branch_summary``
  usage is tracked separately in ``usage_coverage`` and is never inferred.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = 1
COST_BASIS = "provider-reported usage estimate; not billed cost"

_COUNTERS = ("user_messages", "assistant_messages", "tool_calls", "tool_results",
             "tool_errors", "compactions", "branch_summaries")
_USAGE_FIELDS = (("input", "input"), ("output", "output"), ("cacheRead", "cacheRead"),
                 ("cacheWrite", "cacheWrite"), ("totalTokens", "reported_totalTokens"))
_COST_FIELDS = ("input", "output", "cacheRead", "cacheWrite", "total")


def _parse_time(value: str) -> datetime:
    """Parse an ISO timestamp; a naive value is interpreted as UTC."""
    text = value.strip()
    if text.endswith("Z") or text.endswith("z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as error:
        raise ValueError(f"invalid timestamp: {value!r}") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _validate_tree(entries: list[dict]) -> None:
    """Reject dangling, non-string or cyclic parent links before any walk."""
    by_id = {entry["id"]: entry for entry in entries}
    for entry in entries:
        parent = entry.get("parentId")
        if parent is not None and not isinstance(parent, str):
            raise ValueError(f"entry {entry['id']} has a non-string parentId")
        if isinstance(parent, str) and parent not in by_id:
            raise ValueError(f"entry {entry['id']} has a dangling parentId")
    state: dict[str, int] = {}
    for entry in entries:
        if state.get(entry["id"]) == 2:
            continue
        chain: list[str] = []
        current: str | None = entry["id"]
        while current is not None:
            mark = state.get(current)
            if mark == 1:
                raise ValueError("session tree has a cyclic parentId")
            if mark == 2:
                break
            state[current] = 1
            chain.append(current)
            parent = by_id[current].get("parentId")
            current = parent if isinstance(parent, str) else None
        for node in chain:
            state[node] = 2


def read_session(path: Path | str) -> dict:
    """Parse and validate one session file; raise ValueError on malformed input."""
    source = Path(path)
    if not source.is_file():
        raise ValueError(f"session file missing: {source.name}")
    header = None
    entries: list[dict] = []
    seen: set[str] = set()
    with source.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            text = line.strip()
            if not text:
                continue
            try:
                item = json.loads(text)
            except ValueError as error:
                raise ValueError(f"malformed JSON at line {number} of {source.name}") from error
            if not isinstance(item, dict) or not isinstance(item.get("type"), str):
                raise ValueError(f"{source.name}: line {number} is not a session entry")
            if item["type"] == "session":
                if header is not None:
                    raise ValueError(f"{source.name}: duplicate session header at line {number}")
                if not isinstance(item.get("id"), str) or not item["id"]:
                    raise ValueError(f"{source.name}: session header lacks an id")
                header = item
                continue
            if header is None:
                raise ValueError(f"{source.name}: first entry is not a session header")
            if int(header.get("version", 1)) < 2:
                raise ValueError(f"{source.name}: legacy session v{header.get('version', 1)} lacks id/parentId; open it in Pi to migrate")
            if not isinstance(item.get("id"), str) or not item["id"]:
                raise ValueError(f"{source.name}: entry at line {number} lacks an id")
            if "parentId" not in item:
                raise ValueError(f"{source.name}: entry at line {number} lacks a parentId")
            if item["id"] in seen:
                raise ValueError(f"{source.name}: duplicate entry id at line {number}")
            seen.add(item["id"])
            entries.append(item)
    if header is None:
        raise ValueError(f"{source.name}: missing session header")
    _validate_tree(entries)
    return {"header": header, "entries": entries}


def select_ancestry(entries: list[dict], start_id: str, end_id: str) -> list[dict]:
    """Select the ancestry of ``end_id`` from ``start_id`` inclusive.

    Both boundaries must be on the same root-to-leaf path, so work on another
    branch is never silently included. Cyclic and dangling links fail.
    """
    by_id = {entry["id"]: entry for entry in entries}
    if end_id not in by_id:
        raise ValueError("end entry not found in session")
    chain: list[dict] = []
    visited: set[str] = set()
    current: str | None = end_id
    while current is not None:
        if current in visited:
            raise ValueError("session tree has a cyclic parentId")
        visited.add(current)
        entry = by_id.get(current)
        if entry is None:
            raise ValueError("session tree has a dangling parentId")
        parent = entry.get("parentId")
        if parent is not None and not isinstance(parent, str):
            raise ValueError("session tree has a non-string parentId")
        chain.append(entry)
        current = parent
    chain.reverse()
    ids = [entry["id"] for entry in chain]
    if start_id not in ids:
        raise ValueError("start entry is not an ancestor of the end entry; boundaries are on different branches")
    return chain[ids.index(start_id):]


def select_chronological(entries: list[dict], start_time: str, end_time: str) -> list[dict]:
    """Select entries whose timestamps fall in ``[start, end]`` across branches."""
    start = _parse_time(start_time)
    end = _parse_time(end_time)
    if start > end:
        raise ValueError("start time is after end time")
    selected = []
    for entry in entries:
        stamp = entry.get("timestamp")
        if not isinstance(stamp, str):
            raise ValueError(f"entry {entry['id']} lacks a timestamp for chronological bounds")
        moment = _parse_time(stamp)
        if start <= moment <= end:
            selected.append(entry)
    return selected


def _int_field(value, field: str, where: str) -> int:
    """Validate a non-negative integer token counter; booleans are not numbers."""
    if value is None:
        return 0
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{where} {field} must be a number")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{where} {field} must be finite")
        if not value.is_integer():
            raise ValueError(f"{where} {field} must be a whole number")
    number = int(value)
    if number < 0:
        raise ValueError(f"{where} {field} must not be negative")
    return number


def _num_field(value, field: str, where: str) -> float:
    """Validate a finite non-negative cost field."""
    if value is None:
        return 0.0
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{where} {field} must be a number")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{where} {field} must be finite")
    number = float(value)
    if number < 0:
        raise ValueError(f"{where} {field} must not be negative")
    return number


def _blank_usage() -> dict:
    return {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0,
            "reported_totalTokens": 0}


def _blank_cost() -> dict:
    return {field: 0.0 for field in _COST_FIELDS}


def _blank_counters() -> dict:
    return {key: 0 for key in _COUNTERS}


def _blank_coverage() -> dict:
    return {"assistant_messages": 0, "assistant_usage_reported": 0,
            "tool_results": 0, "tool_result_usage_reported": 0,
            "compactions": 0, "compaction_usage_reported": 0,
            "branch_summaries": 0, "branch_summary_usage_reported": 0,
            "usage_objects": 0, "usage_objects_incomplete": 0,
            "cost_objects": 0, "cost_objects_incomplete": 0,
            "total_tokens_reported": 0, "reasoning_reported": 0}


def summarize(selected: list[dict]) -> dict:
    """Aggregate one selection, mirroring Pi's own session statistics fields."""
    usage = _blank_usage()
    cost = _blank_cost()
    coverage = _blank_coverage()
    models: dict[str, int] = {}
    counters = _blank_counters()
    reasoning_total = 0
    reasoning_reported = False

    def add(value, where: str) -> None:
        nonlocal reasoning_total, reasoning_reported
        if value is None:
            return
        if not isinstance(value, dict):
            raise ValueError(f"{where} usage must be an object")
        coverage["usage_objects"] += 1
        required = ("input", "output", "cacheRead", "cacheWrite")
        if any(value.get(key) is None for key in required):
            coverage["usage_objects_incomplete"] += 1
        for field, key in _USAGE_FIELDS:
            usage[key] += _int_field(value.get(field), field, where)
        if value.get("totalTokens") is not None:
            coverage["total_tokens_reported"] += 1
        if value.get("reasoning") is not None:
            coverage["reasoning_reported"] += 1
            reasoning_reported = True
            reasoning_total += _int_field(value.get("reasoning"), "reasoning", where)
        if "cost" in value:
            reported = value.get("cost")
            if not isinstance(reported, dict):
                raise ValueError(f"{where} cost must be an object")
            coverage["cost_objects"] += 1
            if any(reported.get(field) is None for field in _COST_FIELDS):
                coverage["cost_objects_incomplete"] += 1
            for field in _COST_FIELDS:
                cost[field] += _num_field(reported.get(field), field, f"{where} cost")

    for entry in selected:
        kind = entry.get("type")
        if kind in ("compaction", "branch_summary"):
            if kind == "compaction":
                counters["compactions"] += 1
                coverage["compactions"] += 1
                if entry.get("usage") is not None:
                    coverage["compaction_usage_reported"] += 1
            else:
                counters["branch_summaries"] += 1
                coverage["branch_summaries"] += 1
                if entry.get("usage") is not None:
                    coverage["branch_summary_usage_reported"] += 1
            add(entry.get("usage"), f"{kind} entry")
            continue
        if kind != "message":
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            raise ValueError("session message entry lacks a message object")
        role = message.get("role")
        if role == "user":
            counters["user_messages"] += 1
        elif role == "toolResult":
            counters["tool_results"] += 1
            coverage["tool_results"] += 1
            if message.get("isError"):
                counters["tool_errors"] += 1
            value = message.get("usage")
            if value is not None:
                coverage["tool_result_usage_reported"] += 1
            add(value, "toolResult message")
        elif role == "assistant":
            counters["assistant_messages"] += 1
            coverage["assistant_messages"] += 1
            content = message.get("content")
            if isinstance(content, list):
                counters["tool_calls"] += sum(
                    1 for block in content
                    if isinstance(block, dict) and block.get("type") == "toolCall")
            key = f"{message.get('provider', '?')}/{message.get('model', '?')}"
            models[key] = models.get(key, 0) + 1
            value = message.get("usage")
            if value is not None:
                coverage["assistant_usage_reported"] += 1
            add(value, "assistant message")
    usage["reasoning"] = reasoning_total if reasoning_reported else None
    usage["reported_totalTokens"] = (usage["reported_totalTokens"]
                                     if coverage["total_tokens_reported"] else None)
    usage["total"] = usage["input"] + usage["output"] + usage["cacheRead"] + usage["cacheWrite"]
    if coverage["usage_objects"] == 0 or coverage["cost_objects"] == 0:
        # No reported usage (or no cost object) means no cost data at all: stay null, never zero.
        reported_cost = None
        cost_complete = False
    else:
        reported_cost = {key: round(value, 6) for key, value in cost.items()}
        cost_complete = (coverage["cost_objects"] == coverage["usage_objects"]
                        and coverage["cost_objects_incomplete"] == 0)
    usage_complete = (coverage["assistant_usage_reported"] == coverage["assistant_messages"]
                      and coverage["usage_objects_incomplete"] == 0)
    return {**counters, "models": models, "usage": usage,
            "usage_complete": usage_complete, "usage_coverage": coverage,
            "cost": reported_cost, "cost_complete": cost_complete,
            "provider_wait_seconds": None, "user_corrections": None}


def _combine_blocks(blocks: list[dict]) -> dict:
    """Sum observed counters/usage/cost across blocks without claiming completeness."""
    counters = _blank_counters()
    models: dict[str, int] = {}
    usage = _blank_usage()
    coverage = _blank_coverage()
    reasoning_total = 0
    reasoning_reported = False
    for block in blocks:
        for key in counters:
            counters[key] += block[key]
        for key, value in block["models"].items():
            models[key] = models.get(key, 0) + value
        for key in ("input", "output", "cacheRead", "cacheWrite"):
            usage[key] += block["usage"][key]
        if block["usage"]["reported_totalTokens"] is not None:
            usage["reported_totalTokens"] += block["usage"]["reported_totalTokens"]
        if block["usage"]["reasoning"] is not None:
            reasoning_reported = True
            reasoning_total += block["usage"]["reasoning"]
        for key in coverage:
            coverage[key] += block["usage_coverage"][key]
    usage["reported_totalTokens"] = (usage["reported_totalTokens"]
                                     if coverage["total_tokens_reported"] else None)
    usage["reasoning"] = reasoning_total if reasoning_reported else None
    usage["total"] = usage["input"] + usage["output"] + usage["cacheRead"] + usage["cacheWrite"]
    if not blocks:
        # An asserted empty scope is a known zero, unlike a session that reported nothing.
        cost = _blank_cost()
        cost_complete = True
    elif coverage["usage_objects"] == 0 or coverage["cost_objects"] == 0:
        cost = None
        cost_complete = False
    else:
        reported = [block["cost"] for block in blocks if block["cost"] is not None]
        cost = {key: round(sum(item[key] for item in reported), 6) for key in _COST_FIELDS}
        cost_complete = (coverage["cost_objects"] == coverage["usage_objects"]
                        and coverage["cost_objects_incomplete"] == 0)
    return {**counters, "models": models, "usage": usage,
            "usage_complete": all(block["usage_complete"] for block in blocks),
            "usage_coverage": coverage, "cost": cost, "cost_complete": cost_complete}


def _real(path: Path) -> str:
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


def _canonical(entry: dict) -> str:
    return json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _parent_index(sessions: list[dict]) -> dict[int, int | None]:
    """Resolve only verifiable parent links among the supplied sessions."""
    by_real = {session["realpath"]: index for index, session in enumerate(sessions)}
    by_id = {session["header"]["id"]: index for index, session in enumerate(sessions)}
    parents: dict[int, int | None] = {}
    for index, session in enumerate(sessions):
        reference = session["header"].get("parentSession")
        parent = None
        if isinstance(reference, str):
            parent = by_real.get(_real(Path(reference)))
            if parent is None:
                parent = by_id.get(reference)
            if parent == index:
                parent = None
        parents[index] = parent
    return parents


def _is_ancestor(parents: dict[int, int | None], ancestor: int, node: int) -> bool:
    seen: set[int] = set()
    current: int | None = node
    while current is not None and current not in seen:
        seen.add(current)
        current = parents.get(current)
        if current == ancestor:
            return True
    return False


def aggregate(parent: Path, children: list[Path], *, start_entry: str | None,
              end_entry: str | None, start_time: str | None, end_time: str | None,
              children_complete: bool, assert_no_children: bool) -> dict:
    if start_entry is not None and children:
        raise ValueError("entry-ID boundaries select the parent ancestry only; use --start-time/--end-time with child sessions")
    paths = [parent, *children]
    sessions = []
    for path in paths:
        loaded = read_session(path)
        loaded["realpath"] = _real(Path(path))
        sessions.append(loaded)
    parent_session = sessions[0]
    if start_entry is not None:
        selected = select_ancestry(parent_session["entries"], start_entry, end_entry)
        boundary_mode = "ancestry"
    else:
        selected = select_chronological(parent_session["entries"], start_time, end_time)
        boundary_mode = "chronological"
    parent_block = {"role": "parent", "session_id": parent_session["header"]["id"],
                    "boundary_mode": boundary_mode, "selected_entries": len(selected),
                    **summarize(selected)}
    seen: dict[str, tuple[int, dict]] = {
        entry["id"]: (0, entry) for entry in selected}
    parents = _parent_index(sessions)
    child_blocks = []
    for index, child_session in enumerate(sessions[1:], start=1):
        child_selected = select_chronological(child_session["entries"], start_time, end_time)
        skipped = 0
        counted = []
        for entry in child_selected:
            previous = seen.get(entry["id"])
            if previous is not None:
                owner, shared = previous
                if not _is_ancestor(parents, owner, index):
                    raise ValueError("duplicate entry id without verified lineage would double count; "
                                     "supply the fork lineage or drop the clone")
                if _canonical(entry) != _canonical(shared):
                    raise ValueError("duplicate entry id with structurally different content; refusing to deduplicate")
                skipped += 1
                continue
            counted.append(entry)
        seen.update({entry["id"]: (index, entry) for entry in counted})
        child_blocks.append({"role": "child", "session_id": child_session["header"]["id"],
                             "boundary_mode": boundary_mode,
                             "selected_entries": len(child_selected),
                             "shared_history_entries_skipped": skipped,
                             **summarize(counted)})
    child_observed = _combine_blocks(child_blocks) if child_blocks else None
    tool_result_usage = (parent_block["usage_coverage"]["tool_result_usage_reported"]
                         + sum(block["usage_coverage"]["tool_result_usage_reported"]
                               for block in child_blocks))
    # A counted toolResult usage may itself summarize an explicitly supplied child's
    # LLM work. Never dedupe by value: keep observed subtotals but refuse a complete total.
    nested_usage_overlap_suspected = bool(children) and tool_result_usage > 0
    if assert_no_children:
        attribution = {"mode": "none", "complete": True, "totals_known": True, "counted": 0,
                       "totals": _combine_blocks([]), "observed_totals": _combine_blocks([])}
    elif children:
        child_totals_complete = (not nested_usage_overlap_suspected and children_complete
                                 and child_observed["usage_complete"]
                                 and child_observed["cost_complete"])
        attribution = {"mode": "explicit", "complete": children_complete,
                       "totals_known": child_totals_complete, "counted": len(child_blocks),
                       "totals": child_observed if child_totals_complete else None,
                       "observed_totals": child_observed}
    else:
        attribution = {"mode": "unknown", "complete": False, "totals_known": False,
                       "counted": 0, "totals": None, "observed_totals": None}
    observed = _combine_blocks([parent_block, *child_blocks])
    totals_complete = (not nested_usage_overlap_suspected and attribution["totals_known"]
                       and observed["usage_complete"] and observed["cost_complete"])
    notes = [
        "selection is bounded by explicit entry IDs (ancestry) or timestamps (chronological); a session is not assumed to be one task",
        "naive timestamps are interpreted as UTC; timestamps are used only for boundary selection, never as provider wait time",
        "usage_complete means recorded native accounting coverage, not billing proof; optional toolResult/compaction/branch_summary usage is tracked separately in usage_coverage",
        "provider wait time and user corrections are not available from standard session logs and stay null",
        "reported usage and cost are observed subtotals; cost is a provider-reported estimate, not billed cost",
        "reasoning and reported_totalTokens are null when no usage object reported them",
    ]
    if not observed["usage_complete"]:
        notes.append("some usage-bearing entries did not record complete usage; usage is an observed subtotal")
    if observed["cost"] is None:
        notes.append("no usage entry reported cost; cost stays null rather than zero")
    elif not observed["cost_complete"]:
        notes.append("some usage entries did not report complete cost; cost is an observed subtotal")
    if nested_usage_overlap_suspected:
        notes.append("a counted toolResult usage may summarize an explicit child's LLM work; complete totals stay null rather than double counting (no value-based dedupe)")
    if attribution["mode"] == "unknown":
        notes.append("child session totals are unknown and not zero; supply --child scopes or assert no children")
    elif attribution["mode"] == "explicit" and not attribution["totals_known"] and not nested_usage_overlap_suspected:
        notes.append("complete task/child totals stay null until the child scope and its usage/cost coverage are complete")
    return {
        "schema": SCHEMA,
        "boundary": {
            "mode": boundary_mode,
            "start_entry": start_entry,
            "end_entry": end_entry,
            "start_time": start_time,
            "end_time": end_time,
        },
        "parent": parent_block,
        "children": child_blocks,
        "child_attribution": attribution,
        "child_totals_known": attribution["totals_known"],
        "nested_usage_overlap_suspected": nested_usage_overlap_suspected,
        "totals": observed if totals_complete else None,
        "totals_known": totals_complete,
        "observed_totals": observed,
        "cost_basis": COST_BASIS,
        "notes": notes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--parent", required=True, help="parent session JSONL file")
    parser.add_argument("--child", action="append", default=[], help="child session JSONL (repeatable)")
    parser.add_argument("--start-entry")
    parser.add_argument("--end-entry")
    parser.add_argument("--start-time")
    parser.add_argument("--end-time")
    parser.add_argument("--children-complete", action="store_true",
                        help="assert the supplied child scopes are complete")
    parser.add_argument("--assert-no-children", action="store_true",
                        help="assert this task had no child sessions")
    args = parser.parse_args(argv)
    entry_pair = bool(args.start_entry or args.end_entry)
    time_pair = bool(args.start_time or args.end_time)
    if entry_pair and time_pair:
        raise ValueError("use entry IDs or timestamps, not both")
    if entry_pair and not (args.start_entry and args.end_entry):
        raise ValueError("entry boundaries require both --start-entry and --end-entry")
    if time_pair and not (args.start_time and args.end_time):
        raise ValueError("timestamp boundaries require both --start-time and --end-time")
    if not entry_pair and not time_pair:
        raise ValueError("explicit boundaries required: entry IDs or timestamp range")
    if args.assert_no_children and args.child:
        raise ValueError("--assert-no-children cannot be combined with --child")
    if args.children_complete and not args.child:
        raise ValueError("--children-complete requires at least one --child")
    report = aggregate(Path(args.parent), [Path(item) for item in args.child],
                       start_entry=args.start_entry, end_entry=args.end_entry,
                       start_time=args.start_time, end_time=args.end_time,
                       children_complete=args.children_complete,
                       assert_no_children=args.assert_no_children)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        raise SystemExit(f"pi task metrics: {error}") from error

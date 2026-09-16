#!/usr/bin/env python3
"""Measure what agent handoffs cost, from local Pi session logs (read-only).

Three numbers, all derived from the session JSONL and nothing invented:

  1. tier split         -- the expensive tier's share of reported spend
  2. handoff pairs      -- upstream wrote a /tmp handoff doc, downstream read it
       * duplicate share -- what fraction of the downstream session's file reads
                            the upstream session had already read
       * pair cost
  3. handoff artefacts  -- how many handoff docs upstream wrote, how many were
                           ever read back by another session

A handoff pair is an explicit context handoff: the upstream agent's summary/plan
file is the downstream agent's entry point. In-message handoffs are invisible
here, so the pair count is a lower bound.

Usage:
  python3 -B benchmark/handoff-cost/measure.py --days 14
  python3 -B benchmark/handoff-cost/measure.py --days 14 --json

Reported cost is the session log's own counter, not a billed amount. The script
writes nothing, makes no provider request and prints no message text.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import glob
import json
import os
import re
import sys

DEFAULT_TIER_MODEL = "openai-codex/gpt-6-astra"
TMP_PREFIX = "/tmp/"
DOC_RE = re.compile(
    r"(report|brief|plan|evidence|result|summary|handoff|context|findings|writer|worker)",
    re.IGNORECASE,
)
DOC_EXT = (".md", ".txt", ".json", ".log")


def is_handoff_doc(path: str) -> bool:
    """Scratch scripts and test files in /tmp are not handoff artefacts."""
    base = os.path.basename(path)
    return path.startswith(TMP_PREFIX) and base.endswith(DOC_EXT) and bool(DOC_RE.search(base))


def parse_timestamp(value):
    """Record timestamps are ISO strings; message timestamps are epoch millis."""
    try:
        if isinstance(value, (int, float)):
            seconds = float(value)
            if seconds > 1e11:
                seconds /= 1000.0
            return datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc)
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


class Session:
    __slots__ = ("path", "label", "start", "cost", "tokens", "turns", "reads", "writes", "models")

    def __init__(self, path: str, label: str):
        self.path, self.label = path, label
        self.start = None
        self.cost = 0.0
        self.tokens = 0
        self.turns = 0
        self.reads: list[str] = []
        self.writes: list[str] = []
        self.models: set[str] = set()

    def is_tier(self, model: str) -> bool:
        return any(m.startswith(model) for m in self.models)


def parse_session(path: str) -> Session | None:
    session = Session(path, os.path.basename(os.path.dirname(path)))
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if '"type":"message"' not in line and '"type": "message"' not in line:
                    continue
                try:
                    record = json.loads(line)
                except Exception:
                    continue
                message = record.get("message") or {}
                stamp = parse_timestamp(record.get("timestamp")) or parse_timestamp(
                    message.get("timestamp")
                )
                if stamp and (session.start is None or stamp < session.start):
                    session.start = stamp
                if message.get("role") != "assistant":
                    continue
                session.turns += 1
                session.models.add(f'{message.get("provider", "?")}/{message.get("model", "?")}')
                usage = message.get("usage") or {}
                session.cost += float((usage.get("cost") or {}).get("total") or 0.0)
                session.tokens += int(usage.get("totalTokens") or 0)
                for call in message.get("content") or []:
                    if not isinstance(call, dict) or call.get("type") != "toolCall":
                        continue
                    arguments = call.get("arguments") or {}
                    target = arguments.get("path") or arguments.get("file_path")
                    if not target:
                        continue
                    if call.get("name") == "read":
                        session.reads.append(target)
                    elif call.get("name") in ("write", "edit"):
                        session.writes.append(target)
    except OSError:
        return None
    return session if session.start else None


def collect(agent_dir: str, days: int, now=None) -> list[Session]:
    now = now or datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(days=days)
    sessions = []
    for path in glob.glob(os.path.join(agent_dir, "sessions", "*", "*.jsonl")):
        try:
            modified = datetime.datetime.fromtimestamp(
                os.path.getmtime(path), datetime.timezone.utc
            )
        except OSError:
            continue
        if modified < cutoff:
            continue
        session = parse_session(path)
        if session:
            sessions.append(session)
    sessions.sort(key=lambda s: (s.start, s.path))
    return sessions


def _handoff_pairs(sessions: list[Session]):
    """(upstream, downstream, doc) for every doc an upstream session wrote and a
    later session read."""
    writers: dict[str, list[Session]] = collections.defaultdict(list)
    readers: dict[str, list[Session]] = collections.defaultdict(list)
    for session in sessions:
        for path in session.writes:
            if is_handoff_doc(path):
                writers[path].append(session)
        for path in session.reads:
            if is_handoff_doc(path):
                readers[path].append(session)
    pairs, seen = [], set()
    for doc, upstreams in writers.items():
        for upstream in upstreams:
            for downstream in readers.get(doc, []):
                if downstream is upstream or downstream.start < upstream.start:
                    continue
                key = (upstream.path, downstream.path, doc)
                if key not in seen:
                    seen.add(key)
                    pairs.append((upstream, downstream, doc))
    return pairs, writers


def _stats(group: list[Session]) -> dict:
    return {
        "sessions": len(group),
        "turns": sum(s.turns for s in group),
        "cost": round(sum(s.cost for s in group), 4),
        "tokens": sum(s.tokens for s in group),
        "reads": sum(len(s.reads) for s in group),
        "turns_per_session": round(sum(s.turns for s in group) / len(group), 1) if group else 0.0,
        "reads_per_session": round(sum(len(s.reads) for s in group) / len(group), 1) if group else 0.0,
        "cost_per_session": round(sum(s.cost for s in group) / len(group), 4) if group else 0.0,
    }


def summarize(sessions: list[Session], tier_model: str = DEFAULT_TIER_MODEL) -> dict:
    pairs, writers = _handoff_pairs(sessions)
    tier = [s for s in sessions if s.is_tier(tier_model)]
    other = [s for s in sessions if not s.is_tier(tier_model)]
    total_cost = sum(s.cost for s in sessions)

    duplicate_shares, downstream_reads, duplicate_reads, upstream_reads = [], [], [], []
    for upstream, downstream, _ in pairs:
        have, need = set(upstream.reads), set(downstream.reads)
        # upstream reads count each file once; the duplicate share is measured
        # against the downstream session's own read volume.
        duplicate_shares.append(len(have & need) / len(need) if need else 0.0)
        downstream_reads.append(len(need))
        duplicate_reads.append(len(have & need))
        upstream_reads.append(len(have))

    fed = {b.path for _, b, _ in pairs}
    read_back = {
        doc
        for doc in writers
        if any(
            reader is not writer
            for writer in writers[doc]
            for reader in [r for r in sessions if doc in r.reads]
        )
    }
    def mean(values):
        return round(sum(values) / len(values), 3) if values else 0.0

    return {
        "totals": {
            "sessions": len(sessions),
            "turns": sum(s.turns for s in sessions),
            "tokens": sum(s.tokens for s in sessions),
            "reported_cost": round(total_cost, 4),
        },
        "tiers": {
            "tier_model": tier_model,
            "tier": _stats(tier),
            "other": _stats(other),
            "tier_cost_share": round(sum(s.cost for s in tier) / total_cost, 4) if total_cost else 0.0,
        },
        "handoffs": {
            "docs_written": len(writers),
            "docs_read_back": len(read_back),
            "pairs": len(pairs),
            "fed_sessions": len(fed),
            "pair_cost": round(sum(a.cost + b.cost for a, b, _ in pairs), 4),
            "duplicate_share_mean": mean(duplicate_shares),
            "duplicate_share_max": round(max(duplicate_shares), 3) if duplicate_shares else 0.0,
            "downstream_reads_mean": mean(downstream_reads),
            "duplicate_reads_mean": mean(duplicate_reads),
            "upstream_reads_mean": mean(upstream_reads),
        },
        "fed_vs_self": {
            f"{name}_{tier_name}": _stats(
                [
                    s
                    for s in sessions
                    if (s.path in fed) == (name == "fed")
                    and s.is_tier(tier_model) == (tier_name == "tier")
                ]
            )
            for name in ("fed", "self")
            for tier_name in ("tier", "other")
        },
    }


def render(summary: dict) -> str:
    totals, tiers, handoffs = summary["totals"], summary["tiers"], summary["handoffs"]
    lines = [
        f"sessions={totals['sessions']} turns={totals['turns']} tokens={totals['tokens']:,} "
        f"reported_cost=${totals['reported_cost']:.2f}",
        "",
        f"[1] tier split (tier model: {tiers['tier_model']})",
    ]
    for name in ("tier", "other"):
        stats = tiers[name]
        lines.append(
            f"    {name:5s} sessions={stats['sessions']:4d} turns={stats['turns']:5d} "
            f"cost=${stats['cost']:8.2f} cost/session=${stats['cost_per_session']:6.2f} "
            f"reads/session={stats['reads_per_session']:5.1f}"
        )
    lines.append(f"    tier share of reported spend: {100 * tiers['tier_cost_share']:.1f}%")
    lines += [
        "",
        "[2] handoff pairs (upstream wrote a /tmp handoff doc, downstream read it)",
        f"    handoff docs written upstream: {handoffs['docs_written']}",
        f"    docs ever read back by another session: {handoffs['docs_read_back']}",
        f"    handoff pairs: {handoffs['pairs']}  fed downstream sessions: {handoffs['fed_sessions']}",
        f"    pair cost total=${handoffs['pair_cost']:.2f}",
        f"    downstream re-read share of its own reads: mean={100 * handoffs['duplicate_share_mean']:.1f}% "
        f"max={100 * handoffs['duplicate_share_max']:.1f}%",
        f"    mean downstream reads={handoffs['downstream_reads_mean']:.1f} "
        f"already read upstream={handoffs['duplicate_reads_mean']:.1f} "
        f"(upstream mean reads={handoffs['upstream_reads_mean']:.1f})",
        "",
        "[3] sessions started from an upstream handoff doc (per tier)",
    ]
    for name in ("fed", "self"):
        for tier_name in ("tier", "other"):
            stats = summary["fed_vs_self"][f"{name}_{tier_name}"]
            if not stats["sessions"]:
                continue
            lines.append(
                f"    {name:4s} {tier_name:5s} n={stats['sessions']:4d} turns={stats['turns']:5d} "
                f"cost=${stats['cost']:8.2f} turns/session={stats['turns_per_session']:6.1f} "
                f"reads/session={stats['reads_per_session']:5.1f}"
            )
    lines += [
        "",
        "limits: reported cost is the session log's counter, not a billed amount; only",
        "explicit /tmp handoff docs are paired, so the pair count is a lower bound;",
        "small groups in [3] are a signal, not evidence.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--agent-dir",
        default=os.environ.get("PI_CODING_AGENT_DIR", os.path.expanduser("~/.pi/agent")),
        help="Pi agent directory (default: PI_CODING_AGENT_DIR or ~/.pi/agent)",
    )
    parser.add_argument("--days", type=int, default=14, help="session window in days (default: 14)")
    parser.add_argument("--tier-model", default=DEFAULT_TIER_MODEL, help="expensive tier model prefix")
    parser.add_argument("--json", action="store_true", help="emit the summary as JSON")
    options = parser.parse_args(argv)

    sessions = collect(options.agent_dir, options.days)
    if not sessions:
        print(f"no sessions found in {options.agent_dir}/sessions within {options.days} days")
        return 1
    summary = summarize(sessions, options.tier_model)
    print(json.dumps(summary, indent=2) if options.json else render(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())

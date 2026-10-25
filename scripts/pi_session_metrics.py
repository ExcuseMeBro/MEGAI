#!/usr/bin/env python3
"""Read-only Pi JSONL metrics. Never emit conversation content or file paths."""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path

MAX_LINE = 16 * 1024 * 1024


def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result if result.tzinfo else None
    except ValueError:
        return None


def number(value):
    return (isinstance(value, (float, int)) and not isinstance(value, bool)
            and 0 <= value <= 2**53 and math.isfinite(value))


def percentile(values, fraction):
    if not values:
        return None
    values = sorted(values)
    return round(values[max(0, math.ceil(len(values) * fraction) - 1)], 2)


def analyze(root, since, until, exclude_session_id=None, exclude_file=None):
    counts = Counter()
    tools = Counter()
    durations = []
    input_tokens = cached_tokens = 0
    sessions = 0
    # Never print arbitrary JSONL fields, tool names, errors, paths or exception text.
    allowed_tools = {"bash", "read", "edit", "write", "tgrep", "workflow_checkpoint", "knowledge_candidate"}
    for path in sorted(Path(root).rglob("*.jsonl")):
        if path.is_symlink() or (exclude_file and path.resolve() == Path(exclude_file).resolve()):
            continue
        has_message = False
        try:
            with path.open("rb") as stream:
                while True:
                    raw = stream.readline(MAX_LINE + 1)
                    if not raw:
                        break
                    if len(raw) > MAX_LINE:
                        counts["oversized_files_skipped"] += 1
                        break
                    try:
                        entry = json.loads(raw)
                    except (ValueError, UnicodeDecodeError):
                        counts["malformed_lines"] += 1
                        continue
                    if not isinstance(entry, dict):
                        counts["malformed_lines"] += 1
                        continue
                    if entry.get("type") == "session" and exclude_session_id and entry.get("id") == exclude_session_id:
                        break
                    at = timestamp(entry.get("timestamp"))
                    if at is None or not since <= at <= until:
                        continue
                    message = entry.get("message")
                    if entry.get("type") != "message" or not isinstance(message, dict):
                        continue
                    has_message = True
                    role = message.get("role")
                    if role == "assistant":
                        counts["assistant_messages"] += 1
                        duration = message.get("durationMs")
                        if number(duration):
                            durations.append(duration)
                        usage = message.get("usage")
                        if isinstance(usage, dict):
                            incoming, cached = usage.get("input", 0), usage.get("cacheRead", 0)
                            if number(incoming) and number(cached):
                                input_tokens += incoming
                                cached_tokens += cached
                        content = message.get("content")
                        if isinstance(content, list):
                            for block in content:
                                if not isinstance(block, dict) or block.get("type") != "toolCall":
                                    continue
                                name = block.get("name")
                                if isinstance(name, str):
                                    bucket = name if name in allowed_tools else "plane" if name.startswith("mcp__plane__") else "other"
                                    tools[bucket] += 1
                    elif role == "toolResult":
                        counts["tool_results"] += 1
                        if message.get("isError") is True:
                            counts["tool_errors"] += 1
        except OSError:
            counts["unreadable_files"] += 1
        sessions += int(has_message)
    total = sum(tools.values())
    workflow = tools["plane"] + tools["workflow_checkpoint"]
    return {
        "window": {"since": since.isoformat(), "until": until.isoformat()},
        "sessions_with_messages": sessions,
        "counts": dict(sorted(counts.items())), "tools": dict(sorted(tools.items())),
        "tool_calls": total,
        "direct_plane_checkpoint_percent": round(100 * workflow / total, 2) if total else None,
        "assistant_duration_ms": {"samples": len(durations), "p50": percentile(durations, .5), "p95": percentile(durations, .95)},
        "input_tokens": input_tokens, "cache_read_tokens": cached_tokens,
        "cache_read_percent": round(100 * cached_tokens / (input_tokens + cached_tokens), 2) if input_tokens + cached_tokens else None,
        "limitations": ["Session-level metadata, not measured user-task productivity or end-to-end latency.",
                        "Nested shell/tool orchestration is not attributed; older records may omit durationMs.",
                        "No session text, tool arguments, errors, arbitrary names or paths are exported."],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=Path, default=Path.home() / ".pi/agent/sessions")
    parser.add_argument("--days", type=float, default=7)
    parser.add_argument("--until", type=timestamp, default=datetime.now(timezone.utc))
    parser.add_argument("--exclude-session-id", default=os.environ.get("PI_SESSION_ID"))
    args = parser.parse_args()
    if not number(args.days) or args.days == 0 or args.until is None:
        parser.error("days must be positive/finite; until must be timezone-aware ISO timestamp")
    if not args.sessions.is_dir():
        parser.error("sessions must be an existing directory")
    try:
        since = args.until - timedelta(days=args.days)
    except OverflowError:
        parser.error("days exceeds supported date range")
    print(json.dumps(analyze(args.sessions, since, args.until, args.exclude_session_id,
                             os.environ.get("PI_SESSION_FILE")), indent=2))


if __name__ == "__main__":
    main()

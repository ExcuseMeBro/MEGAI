#!/usr/bin/env python3
"""Fail-closed semantic checks and section transforms for Codex TOML."""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

BARE = r"[A-Za-z0-9_-]+"
QUOTED = r"(?:\"(?:\\.|[^\"])*\"|'(?:[^']|'')*')"
PART = rf"(?:{BARE}|{QUOTED})"
SECTION_RE = re.compile(rf"^\[(?P<body>{PART}(?:\.{PART})*)\][ \t]*$")
WORKSPACE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def unquote(part: str) -> str:
    if part.startswith("'"):
        return part[1:-1].replace("''", "'")
    if part.startswith('"'):
        return json.loads(part)
    return part


def section_parts(body: str) -> list[str]:
    parts: list[str] = []
    current = []
    quote = ""
    escaped = False
    for char in body:
        if quote:
            current.append(char)
            if quote == '"' and escaped:
                escaped = False
            elif quote == '"' and char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in "\"'":
            quote = char
        if char == ".":
            parts.append(unquote("".join(current)))
            current = []
        else:
            current.append(char)
    if quote:
        fail("unterminated TOML section quote")
    parts.append(unquote("".join(current)))
    return parts


def sections(text: str):
    lines = text.splitlines(keepends=True)
    found = []
    for index, line in enumerate(lines):
        match = SECTION_RE.match(line.rstrip("\r\n"))
        if match:
            found.append((index, section_parts(match.group("body"))))
    for position, (start, path) in enumerate(found):
        end = found[position + 1][0] if position + 1 < len(found) else len(lines)
        yield start, end, path


def parse(text: str) -> dict:
    try:
        value = tomllib.loads(text)
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        fail(f"invalid Codex TOML: {exc}")
    if not isinstance(value, dict):
        fail("Codex TOML root is not an object")
    return value


def load(path: Path) -> tuple[str, dict]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        fail(str(exc))
    return text, parse(text)


def marker_bounds(lines: list[str], begin: str, end: str) -> tuple[int, int] | None:
    starts = [index for index, line in enumerate(lines) if line.rstrip("\r\n") == begin]
    ends = [index for index, line in enumerate(lines) if line.rstrip("\r\n") == end]
    if len(starts) == 0 and len(ends) == 0:
        return None
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        fail("unpaired or duplicated Plane Codex markers")
    return starts[0], ends[0]


def owned(data: dict, block_data: dict | None, helper: str) -> bool:
    servers = data.get("mcp_servers", {})
    plane = servers.get("plane") if isinstance(servers, dict) else None
    block_servers = block_data.get("mcp_servers", {}) if block_data else {}
    block_plane = block_servers.get("plane") if isinstance(block_servers, dict) else None
    if not isinstance(plane, dict) or not isinstance(block_plane, dict):
        return False
    args = plane.get("args")
    block_args = block_plane.get("args")
    return (
        plane.get("command") == helper
        and block_plane.get("command") == helper
        and args == block_args
        and isinstance(args, list)
        and len(args) == 4
        and args[0] == "--token-file"
        and isinstance(args[1], str)
        and args[2] == "--workspace"
        and isinstance(args[3], str)
        and bool(WORKSPACE_RE.fullmatch(args[3]))
    )


def inspect(path: Path, begin: str, end: str, helper: str) -> str:
    if not path.exists():
        return "missing"
    text, data = load(path)
    lines = text.splitlines(keepends=True)
    bounds = marker_bounds(lines, begin, end)
    block_data = None
    if bounds:
        start, finish = bounds
        block_text = "".join(lines[start + 1 : finish])
        block_data = parse(block_text) if block_text.strip() else {}
    servers = data.get("mcp_servers", {})
    if not isinstance(servers, dict) or "plane" not in servers:
        return "missing"
    if not bounds:
        return "unmanaged"
    return "owned" if owned(data, block_data, helper) else "unmanaged"


def strip_managed(path: Path, begin: str, end: str) -> str:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    bounds = marker_bounds(lines, begin, end)
    if not bounds:
        fail("managed Plane Codex markers are missing")
    start, finish = bounds
    return "".join(lines[:start] + lines[finish + 1 :])


def strip_servers(text: str, names: set[str]) -> str:
    data = parse(text)
    servers = data.get("mcp_servers", {})
    if isinstance(servers, dict):
        present = names.intersection(servers)
    else:
        present = set()
    lines = text.splitlines(keepends=True)
    ranges = []
    for start, end, path in sections(text):
        if len(path) >= 2 and path[0] == "mcp_servers" and path[1] in names:
            ranges.append((start, end))
    section_names = {path[1] for _, _, path in sections(text) if len(path) >= 2 and path[0] == "mcp_servers"}
    if present - section_names:
        fail("cannot safely remove dotted-key MCP server; refusing transformation")
    for start, end in reversed(ranges):
        del lines[start:end]
    return "".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("validate", "inspect", "strip-managed", "strip-servers"))
    parser.add_argument("--file", required=True)
    parser.add_argument("--begin", default="# >>> megai-plane-managed (do not edit) >>>")
    parser.add_argument("--end", default="# <<< megai-plane-managed <<<")
    parser.add_argument("--helper", default="")
    parser.add_argument("--server", action="append", default=[])
    args = parser.parse_args()
    path = Path(args.file)
    if args.action == "validate":
        load(path)
        return 0
    if args.action == "inspect":
        print(inspect(path, args.begin, args.end, args.helper))
        return 0
    if args.action == "strip-managed":
        sys.stdout.write(strip_managed(path, args.begin, args.end))
        return 0
    text = path.read_text(encoding="utf-8")
    sys.stdout.write(strip_servers(text, set(args.server)))
    return 0


if __name__ == "__main__":
    main()

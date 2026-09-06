#!/usr/bin/env python3
"""Emit Plane MCP request headers from a private token file."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import stat
import sys
from typing import NoReturn

PLANE_MCP_URL = "https://mcp.plane.so/http/api-key/mcp"
WORKSPACE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
MAX_TOKEN_BYTES = 4096
MAX_ENVELOPE_BYTES = 1024 * 1024


def fail() -> NoReturn:
    # Keep diagnostics deliberately generic: the adapter suppresses stderr, and
    # neither a token nor a credential path should become request output.
    raise SystemExit(1)


def validate_workspace(workspace: str) -> None:
    if not WORKSPACE_RE.fullmatch(workspace) or len(workspace) > 128:
        fail()


def read_token(path: str) -> str:
    try:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
    except (OSError, ValueError):
        fail()

    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            fail()
        if info.st_uid != os.getuid() or info.st_mode & 0o077 or not info.st_mode & 0o400:
            fail()
        raw = os.read(fd, MAX_TOKEN_BYTES + 1)
    except (OSError, ValueError):
        fail()
    finally:
        os.close(fd)

    if len(raw) == 0 or len(raw) > MAX_TOKEN_BYTES:
        fail()
    try:
        token = raw.decode("utf-8")
    except UnicodeDecodeError:
        fail()

    # A token file may have one conventional trailing line ending, but never
    # multiple lines or control characters that could become header injection.
    if token.endswith("\n"):
        token = token[:-1]
        if token.endswith("\r"):
            token = token[:-1]
    if not token or token != token.strip() or any(ord(char) < 0x20 or ord(char) == 0x7F for char in token):
        fail()
    return token


def validate_request_envelope() -> None:
    # requestHeadersCommand receives this versioned envelope on stdin. Validate
    # it completely before opening the credential file.
    try:
        raw = sys.stdin.buffer.read(MAX_ENVELOPE_BYTES + 1)
        if len(raw) > MAX_ENVELOPE_BYTES:
            fail()
        envelope = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        fail()
    if not isinstance(envelope, dict):
        fail()
    if envelope.get("version") != 1:
        fail()
    method = envelope.get("method")
    url = envelope.get("url")
    body = envelope.get("bodyBase64")
    if not isinstance(method, str) or not re.fullmatch(r"[A-Z]+", method):
        fail()
    # Exact string matching binds credentials to the HTTPS origin, default port,
    # and path. It rejects userinfo, query/fragment additions, redirects, and
    # discovery endpoints before the token is read.
    if url != PLANE_MCP_URL:
        fail()
    if not isinstance(body, str):
        fail()
    try:
        base64.b64decode(body, validate=True)
    except (ValueError, base64.binascii.Error):
        fail()


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--token-file", required=True)
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    validate_workspace(args.workspace)
    if not args.check:
        validate_request_envelope()
    token = read_token(args.token_file)
    if args.check:
        return 0
    json.dump(
        {
            "Authorization": f"Bearer {token}",
            "x-workspace-slug": args.workspace,
        },
        sys.stdout,
        separators=(",", ":"),
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    main()

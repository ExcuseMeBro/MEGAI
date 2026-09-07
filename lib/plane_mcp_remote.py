#!/usr/bin/env python3
"""Start the pinned mcp-remote bridge without putting a Plane token in argv."""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plane_mcp_headers import read_token, validate_workspace  # noqa: E402

PLANE_MCP_URL = "https://mcp.plane.so/http/api-key/mcp"
MCP_REMOTE_VERSION = "mcp-remote@0.1.43"
AUTH_ENV = "MEGAI_PLANE_AUTH"
WORKSPACE_ENV = "MEGAI_PLANE_WORKSPACE"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--token-file", required=True)
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    validate_workspace(args.workspace)
    token = read_token(args.token_file)
    if args.check:
        return 0
    npx = shutil.which("npx")
    if not npx:
        return 1
    env = os.environ.copy()
    env[AUTH_ENV] = f"Bearer {token}"
    env[WORKSPACE_ENV] = args.workspace
    command = [
        npx,
        MCP_REMOTE_VERSION,
        PLANE_MCP_URL,
        "--header",
        f"Authorization:${{{AUTH_ENV}}}",
        "--header",
        f"x-workspace-slug:${{{WORKSPACE_ENV}}}",
        "--silent",
    ]
    os.execvpe(npx, command, env)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

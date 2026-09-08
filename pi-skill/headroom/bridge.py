#!/usr/bin/env python3
"""Local Headroom adapter. JSON stdin/stdout; no provider credentials or proxy.

Project-scoped CCR originals expire after seven days. Persistent memories do not.
Pi session history is never rewritten. All model assets must be prepared at install.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from assets import verify_assets  # noqa: E402
from persistence import Originals, memory  # noqa: E402

VERSION = "0.37.0"
MAX_TEXT = 2_000_000


def private_directory(path: Path) -> Path:
    for part in (path, *path.parents):
        if part.is_symlink() and part not in (Path("/tmp"), Path("/var")):
            raise ValueError(f"symlinked storage path: {part}")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not path.is_dir() or path.stat().st_uid != os.getuid():
        raise ValueError("storage must be an owned directory")
    path.chmod(0o700)
    for child in path.iterdir():
        if child.is_symlink():
            raise ValueError("symlinked storage entry")
    return path


def setup(cwd: str) -> Path:
    os.umask(0o077)
    root = Path(os.environ.get("MEGAI_HOME", Path.home() / ".megai"))
    # Sanitize even direct bridge invocations before any third-party import.
    clean = {key: os.environ[key] for key in ("HOME", "PATH", "MEGAI_HOME") if key in os.environ}
    os.environ.clear()
    os.environ.update(clean)
    os.environ.update({
        "HEADROOM_BEACON": "off", "HEADROOM_TELEMETRY": "off",
        "DO_NOT_TRACK": "1", "HEADROOM_OFFLINE": "1",
        "HEADROOM_UPDATE_CHECK": "off", "HEADROOM_EFFORT_ROUTER": "0",
        "HF_HUB_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1",
        "HF_HOME": str(root / "headroom-assets/huggingface"),
        "TIKTOKEN_CACHE_DIR": str(root / "headroom-assets/tiktoken"),
        "HEADROOM_CCR_BACKEND": "memory", "HEADROOM_CCR_TTL_SECONDS": "604800",
        "HEADROOM_EMBEDDER_RUNTIME": "onnx",
    })
    directory = Path(cwd).resolve(strict=True)
    git = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                         cwd=directory, text=True, capture_output=True, timeout=5)
    identity = str(Path(git.stdout.strip()).resolve()) if git.returncode == 0 else str(directory)
    project = hashlib.sha256(identity.encode()).hexdigest()[:32]
    storage = private_directory(root / "headroom-data" / project)
    os.environ["HEADROOM_WORKSPACE_DIR"] = str(storage)
    if importlib.metadata.version("headroom-ai") != VERSION:
        raise ValueError(f"Headroom {VERSION} required; run megai install")
    # In addition to upstream offline flags, refuse Python network activity.
    # No proxy/remote embedding path is part of this adapter.
    def offline(event: str, _args: tuple) -> None:
        if event in ("socket.connect", "socket.connect_ex", "socket.getaddrinfo", "socket.bind"):
            raise PermissionError("Headroom runtime network is disabled")
    sys.addaudithook(offline)
    return storage


def text_arg(request: dict, key: str = "text") -> str:
    text = request.get(key)
    if not isinstance(text, str) or not text.strip() or len(text.encode()) > MAX_TEXT:
        raise ValueError(f"{key} must be nonempty UTF-8 text under {MAX_TEXT} bytes")
    return text


async def handle(request: dict, storage: Path) -> dict:
    action = request.get("action")
    if action == "steering":
        from headroom.proxy.output_steering import steering_text
        level = request.get("level", 2)
        if type(level) is not int or not 0 <= level <= 4:
            raise ValueError("verbosity level must be 0..4")
        return {"text": steering_text(level) if level else ""}
    if action == "compress":
        from headroom import compress
        from headroom.compress import CompressConfig
        text = text_arg(request)
        result = compress(
            [{"role": "tool", "tool_call_id": "pi-local", "content": text}],
            model="gpt-4o",  # Tokenizer only; no provider/model selection or request.
            config=CompressConfig(protect_recent=0, compress_system_messages=False,
                                  kompress_model="disabled"),
        )
        compressed = result.messages[0]["content"]
        if not isinstance(compressed, str):
            raise ValueError("unsupported Headroom compression result")
        if compressed == text or len(compressed.encode()) + 160 >= len(text.encode()):
            return {"text": text, "compressed": False}
        store = Originals(storage)
        key = store.put(text)
        if key is None:
            return {"text": text, "compressed": False, "reason": "originals quota reached"}
        if store.get(key) != text:
            raise ValueError("Headroom original could not be verified")
        return {"text": compressed, "compressed": True, "id": key,
                "tokens_before": result.tokens_before, "tokens_after": result.tokens_after}
    if action == "retrieve":
        key = request.get("id", "")
        if not isinstance(key, str) or not re.fullmatch(r"[a-f0-9]{12,64}", key):
            raise ValueError("invalid retrieval id")
        original = Originals(storage).get(key)
        if original is None:
            raise ValueError("original unavailable or expired; read native session/source")
        offset = request.get("offset", 0)
        limit = request.get("limit", 8000)
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 8000:
            raise ValueError("offset must be >=0 and limit 1..8000 characters")
        return {"text": original[offset:offset + limit], "total_characters": len(original),
                "next_offset": offset + limit if offset + limit < len(original) else None}
    if action in ("save", "recall", "doctor"):
        verify_assets(storage.parent.parent)
        if action in ("save", "recall"):
            content = text_arg(request)
            if len(json.dumps(content, ensure_ascii=False).encode()) > 8000:
                raise ValueError("memory serialized text limit is 8000 bytes")
            return await memory(storage, action, content)
        # Exercise actual storage + local embedding without saving a test memory.
        await memory(storage, "recall", "Headroom local readiness")
        probe = await handle({"action": "compress", "text": json.dumps([
            {"id": i, "status": "ok", "message": "local readiness fixture"}
            for i in range(300)
        ])}, storage)
        if not probe["compressed"]:
            raise ValueError("compression readiness fixture did not compress")
        return {"headroom": VERSION, "compression": "verified-with-original",
                "memory": "local-onnx", "network": "offline",
                "effort_routing": False, "storage": str(storage)}
    raise ValueError("unknown Headroom action")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("json", "compress", "retrieve", "save", "recall", "doctor"))
    parser.add_argument("text", nargs="*")
    args = parser.parse_args()
    if args.action == "json":
        raw = sys.stdin.buffer.read(MAX_TEXT + 100_000)
        if len(raw) >= MAX_TEXT + 100_000:
            raise ValueError("request too large")
        request = json.loads(raw)
        if not isinstance(request, dict):
            raise ValueError("expected a JSON object")
    else:
        request = {"action": args.action, "text": " ".join(args.text)}
        if args.action == "compress" and not args.text:
            request["text"] = sys.stdin.read(MAX_TEXT + 1)
        if args.action == "retrieve":
            request["id"] = request.pop("text")
    cwd = request.get("cwd", os.getcwd())
    if not isinstance(cwd, str):
        raise ValueError("cwd must be a path")
    with contextlib.redirect_stdout(sys.stderr):
        storage = setup(cwd)
        result = asyncio.run(handle(request, storage))
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        # Do not print payloads, memory text or credentials into logs.
        print(f"Headroom failed ({type(error).__name__}); raw context retained. Run megai headroom doctor.", file=sys.stderr)
        raise SystemExit(1) from None

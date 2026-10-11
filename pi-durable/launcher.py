#!/usr/bin/env python3
"""Standalone foreground supervisor. Kernel flock, no daemon or registry dependency."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import stat as statlib
import subprocess
import sys
import uuid

MAX_JSON = 2 * 1024 * 1024


def safe_path(path):
    path = Path(os.path.abspath(path))
    for part in [path, *path.parents]:
        if part.is_symlink():
            raise ValueError(f"Symlink refused: {part}")
    return path


def read_json(path):
    path = safe_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        stat = os.fstat(fd)
        if not statlib.S_ISREG(stat.st_mode) or stat.st_uid != os.getuid() or stat.st_mode & 0o077:
            raise ValueError("State file must be private, regular and user-owned")
        with os.fdopen(fd, "r", closefd=False) as stream:
            text = stream.read(MAX_JSON + 1)
        if len(text.encode()) > MAX_JSON:
            raise ValueError("State file exceeds bound")
        return json.loads(text)
    finally:
        os.close(fd)


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_json(path, value):
    path = safe_path(path)
    temporary = path.parent / f".tmp-{uuid.uuid4()}"
    content = (json.dumps(value) + "\n").encode()
    if len(content) > MAX_JSON:
        raise ValueError("State exceeds bound")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(content)
            stream.flush()
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, path)
    sync_directory(path.parent)


def emit(value):
    print(json.dumps(value), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "run", "resume", "status", "stop", "cancel", "reconcile", "doctor"])
    parser.add_argument("--task", default=str(Path.home() / ".megai/pi-durable/tasks/default"))
    parser.add_argument("--cwd", default=os.getcwd())
    parser.add_argument("--provider", default=os.environ.get("PI_PROVIDER", "openai-codex"))
    parser.add_argument("--model", default=os.environ.get("PI_MODEL", "gpt-6.1-sol"))
    parser.add_argument("--thinking", default=os.environ.get("PI_REASONING_LEVEL", "medium"))
    parser.add_argument("--agent-dir", default=os.environ.get("PI_CODING_AGENT_DIR", str(Path.home() / ".pi/agent")))
    parser.add_argument("--allow-write", action="store_true", help="Explicitly enable write/edit/bash; not a filesystem sandbox")
    parser.add_argument("--prompt-file", help="UTF-8 file, or '-' for stdin")
    parser.add_argument("--request-id", help="Stable unique ID for this input; required for run")
    parser.add_argument("--note", help="Human note recording actual interrupted-write outcomes")
    parser.add_argument("--max-restarts", type=int, default=2, help="Process-crash restarts only (0–3); provider errors never retried")
    args = parser.parse_args()
    if not 0 <= args.max_restarts <= 3:
        parser.error("--max-restarts must be 0–3")
    os.umask(0o077)
    task = safe_path(args.task)
    if args.command == "init":
        task.mkdir(parents=True, exist_ok=True, mode=0o700)
    stat = task.stat()
    if not task.is_dir() or stat.st_uid != os.getuid() or stat.st_mode & 0o077:
        raise ValueError("Task directory must be private and user-owned")
    # Never unlink this inode: flock is released by the kernel when ALL owners die.
    lock_path = safe_path(task / "owner.lock")
    lock = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        lock_stat = os.fstat(lock)
        if not statlib.S_ISREG(lock_stat.st_mode) or lock_stat.st_uid != os.getuid() or lock_stat.st_mode & 0o077:
            raise ValueError("Unsafe lock file")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            owner = read_json(task / "owner.json") if (task / "owner.json").exists() else {}
            if args.command == "status":
                progress = read_json(task / "progress.json") if (task / "progress.json").exists() else None
                emit({"status": "running", "owner": owner,
                      "progress": progress if progress and progress.get("runId") == owner.get("runId") else None})
                return 0
            if args.command == "stop":
                if not owner.get("runId"):
                    raise ValueError("Owner starting; no verified run to stop")
                atomic_json(task / "stop.json", {"runId": owner["runId"]})
                emit({"status": "stop-requested", "runId": owner["runId"], "pendingWorkRetained": True})
                return 0
            emit({"status": "blocked", "message": "Storage already owned", "owner": owner})
            return 2
        if args.command == "stop":
            emit({"status": "not-running", "pendingWorkRetained": True})
            return 0
        payload = {}
        if args.command == "init":
            payload = {"schema": 1, "cwd": str(Path(args.cwd).resolve(strict=True)), "provider": args.provider,
                       "model": args.model, "thinking": args.thinking, "allowWrite": args.allow_write,
                       "agentDir": str(Path(args.agent_dir).absolute())}
        elif args.command in ("reconcile", "cancel"):
            if args.command == "reconcile" and not sys.stdin.isatty():
                emit({"status": "blocked", "message": "Human terminal required for reconciliation"})
                return 2
            payload = {"note": args.note}
        elif args.command == "run":
            if not args.prompt_file or not args.request_id:
                parser.error("run requires --prompt-file and --request-id")
            if (task / "active.json").exists():
                emit({"status": "blocked", "message": "Existing active request: use resume"})
                return 2
            if args.prompt_file == "-":
                text = sys.stdin.read(1024 * 1024 + 1)
            else:
                with open(args.prompt_file, encoding="utf-8") as stream:
                    text = stream.read(1024 * 1024 + 1)
            if not text.strip() or len(text.encode()) > 1024 * 1024:
                raise ValueError("Prompt must be nonempty and at most 1 MiB")
            request = {"requestId": args.request_id, "content": text}
            # Admission input is committed before spawning; supervisor retries cannot change it.
            atomic_json(task / "active.json", request)
            # Worker consumes the same immutable request as resume, including the first attempt.
            args.command = "resume"
        node = shutil.which("node")
        if not node:
            raise ValueError("Node.js >=24 required")
        run_id = str(uuid.uuid4())
        atomic_json(task / "owner.json", {"schema": 1, "runId": run_id, "supervisorPid": os.getpid()})
        env = dict(os.environ, MEGAI_DURABLE_LOCK_FD=str(lock), MEGAI_DURABLE_RUN_ID=run_id)
        if env.get("MEGAI_DURABLE_TESTING") != "1":
            env.pop("MEGAI_DURABLE_TEST_MODULE", None)
        stopping = False

        def stop(_signal, _frame):
            nonlocal stopping
            stopping = True
            atomic_json(task / "stop.json", {"runId": run_id})

        signal.signal(signal.SIGINT, stop)
        signal.signal(signal.SIGTERM, stop)
        for attempt in range(args.max_restarts + 1):
            if stopping or ((task / "stop.json").exists() and read_json(task / "stop.json").get("runId") == run_id):
                return 130
            # Worker retains this same locked open-file description if the supervisor itself dies.
            child = subprocess.Popen([node, str(Path(__file__).with_name("worker.mjs")), args.command, str(task), json.dumps(payload)],
                                     pass_fds=(lock,), env=env)
            code = child.wait()
            if code == 0:
                if args.command == "cancel" and (task / "active.json").exists():
                    history = task / "cancelled"
                    history.mkdir(exist_ok=True, mode=0o700)
                    os.replace(task / "active.json", history / f"{uuid.uuid4()}.json")
                    sync_directory(history)
                    sync_directory(task)
                if args.command == "resume" and (task / "active.json").exists():
                    result = read_json(task / "result.json")
                    active = read_json(task / "active.json")
                    if result.get("requestId") != active.get("requestId") or result.get("submission", {}).get("status") != "done":
                        raise ValueError("Completed result does not match active request")
                    (task / "active.json").unlink()
                    sync_directory(task)
                return 0
            # Only unexpected process death gets a bounded restart. Explicit stop, validation/auth/model/storage errors do not.
            if stopping or code >= 0 or code == -signal.SIGTERM or args.command != "resume":
                return 130 if stopping else (128 - code if code < 0 else code)
            if attempt == args.max_restarts:
                emit({"status": "blocked", "message": "Process restart budget exhausted; explicit resume required"})
                return 2
            emit({"event": "restart", "attempt": attempt + 1, "signal": -code})
        return 2
    finally:
        os.close(lock)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        emit({"status": "error", "message": str(error)})
        sys.exit(1)

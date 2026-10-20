#!/usr/bin/env python3
"""Opt-in research only. Real Pi RPC, no production installation or shared queue.

A small original T3-inspired receipt prototype, NOT T3's runtime. It deliberately
blocks ambiguous in-flight retries: SQLite cannot atomically commit an external
Pi/bash/model side effect. Only committed results can be safely replayed.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import queue
import shlex
import shutil
import sqlite3
import subprocess
import threading
import time


class Uncertain(RuntimeError):
    pass


class Receipts:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS receipts (id TEXT PRIMARY KEY, payload TEXT NOT NULL, state TEXT NOT NULL, result TEXT)")

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.execute("PRAGMA synchronous=FULL")
        return db

    def dispatch(self, command_id, payload, action, before_send=None, before_commit=None):
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload,state,result FROM receipts WHERE id=?", (command_id,)).fetchone()
            if row:
                if row[0] != fingerprint:
                    raise ValueError("command id payload mismatch")
                if row[1] == "done":
                    return json.loads(row[2])
                raise Uncertain("in-flight command: reconcile external effect before retry")
            db.execute("INSERT INTO receipts VALUES (?,?,'running',NULL)", (command_id, fingerprint))
        if before_send:
            before_send()
        result = action()
        if before_commit:
            before_commit()
        with self.connect() as db:
            db.execute("UPDATE receipts SET state='done',result=? WHERE id=?", (json.dumps(result), command_id))
        return result


class Pi:
    def __init__(self, cwd, pi="pi", session=None):
        self.events = queue.Queue()
        self.event_count = 0
        self.cwd = str(cwd)
        self.stderr_path = Path(cwd) / "pi-stderr.log"
        self.stderr = self.stderr_path.open("w")
        args = [pi, "--mode", "rpc", "-ne", "-ns", "-np", "--no-themes"]
        args += ["--session", str(session)] if session else ["--no-session"]
        # Preserve normal auth/model/thinking. Only disable extensions/skills for
        # a controlled API comparison; do NOT claim full production-harness perf.
        self.proc = subprocess.Popen(args, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self.stderr, text=True, bufsize=1)
        self.reader = threading.Thread(target=self.read, daemon=True)
        self.reader.start()
        state = self.rpc({"id": "ready", "type": "get_state"}, timeout=30)
        assert state["success"], state
        self.state = state.get("data", {})

    def read(self):
        for line in self.proc.stdout:
            try:
                self.events.put(json.loads(line))
            except json.JSONDecodeError:
                self.events.put({"type": "invalid_json"})
        self.events.put({"type": "eof"})

    def receive(self, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Pi RPC deadline expired; owned process retained for diagnosis")
        event = self.events.get(timeout=remaining)
        self.event_count += 1
        if event["type"] == "eof":
            raise RuntimeError("Pi exited before response")
        return event

    def send(self, command):
        self.proc.stdin.write(json.dumps(command) + "\n")
        self.proc.stdin.flush()

    def rpc(self, command, timeout=30):
        self.send(command)
        deadline = time.monotonic() + timeout
        while True:
            event = self.receive(deadline)
            if event.get("type") == "response" and event.get("id") == command["id"]:
                return event

    def bash(self, command_id, command):
        result = self.rpc({"id": command_id, "type": "bash", "command": command, "excludeFromContext": True})
        assert result["success"] and result["data"]["exitCode"] == 0, result
        return {"success": True, "exitCode": result["data"]["exitCode"]}

    def prompt(self, command_id, message, timeout=120):
        self.send({"id": command_id, "type": "prompt", "message": message})
        deadline = time.monotonic() + timeout
        usage = {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}
        assistant_messages = 0
        failed = False
        accepted = False
        while True:
            event = self.receive(deadline)
            if event.get("type") == "response" and event.get("id") == command_id:
                accepted = event.get("success", False)
                if not accepted:
                    raise RuntimeError("Pi rejected benchmark prompt: " + str(event.get("error")))
            if event.get("type") == "message_end":
                msg = event.get("message", {})
                if msg.get("role") == "assistant":
                    assistant_messages += 1
                    failed |= msg.get("stopReason") in ("error", "aborted")
                    for key in usage:
                        usage[key] += msg.get("usage", {}).get(key, 0)
            if event.get("type") == "agent_end":
                return {"accepted": accepted, "assistant_messages": assistant_messages,
                        "failed": failed, "usage": usage}

    def close(self):
        # Normal EOF for this benchmark-owned disposable process only. Never
        # signal/restart a user session. A timeout retains the owned process.
        self.proc.stdin.close()
        self.proc.wait(timeout=15)
        self.reader.join(timeout=2)
        self.proc.stdout.close()
        self.stderr.close()


def elapsed(action):
    start = time.perf_counter()
    result = action()
    return result, (time.perf_counter() - start) * 1000


def local_bench(root, pi, repeats):
    rows = []
    for mode in ("plain", "durable"):
        folder = root / mode
        folder.mkdir()
        client = Pi(folder, pi)
        store = Receipts(folder / "receipts.sqlite3")
        try:
            for scenario in ("normal", "duplicate", "lost_ack_committed", "lost_ack_uncommitted", "parallel_duplicate"):
                for index in range(repeats):
                    command_id = f"{scenario}-{index}"
                    effect = folder / f"{command_id}.txt"
                    command = f"printf 'effect\\n' >> {shlex.quote(str(effect))}"
                    payload = {"type": "bash", "command": command}
                    calls = [0]
                    def action():
                        calls[0] += 1
                        return client.bash(command_id, command)
                    def dispatch(db=store):
                        return db.dispatch(command_id, payload, action) if mode == "durable" else action()
                    blocked = False
                    start = time.perf_counter()
                    if scenario in ("normal", "duplicate", "lost_ack_committed"):
                        dispatch()
                        if scenario == "duplicate":
                            dispatch()
                            dispatch()
                        if scenario == "lost_ack_committed":
                            # Client loses response after durable commit, recreates store.
                            dispatch(Receipts(folder / "receipts.sqlite3"))
                    elif scenario == "lost_ack_uncommitted":
                        if mode == "durable":
                            def drop():
                                raise ConnectionError("injected response loss before receipt commit")
                            try:
                                store.dispatch(command_id, payload, action, before_commit=drop)
                            except ConnectionError:
                                pass
                            try:
                                dispatch(Receipts(folder / "receipts.sqlite3"))
                            except Uncertain:
                                blocked = True
                        else:
                            dispatch()  # Discard caller response, no native receipt.
                            dispatch()
                    else:
                        # Two durable controllers race one id; one real Pi client.
                        # Native same-client concurrent bash is not supported: do
                        # not invent parallel baseline behavior. Mark separately.
                        if mode == "plain":
                            continue
                        barrier = threading.Barrier(2)
                        def racing():
                            db = Receipts(folder / "receipts.sqlite3")
                            barrier.wait(timeout=5)
                            try:
                                return db.dispatch(command_id, payload, action)
                            except Uncertain:
                                return {"blocked": True}
                        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                            outcomes = list(pool.map(lambda _: racing(), range(2)))
                        blocked = any(x.get("blocked") for x in outcomes)
                    row = {"mode": mode, "scenario": scenario, "trial": index, "rpc_calls": calls[0],
                           "effects": len(effect.read_text().splitlines()), "blocked": blocked,
                           "ms": (time.perf_counter() - start) * 1000}
                    rows.append(row)
                    expected = 1 if mode == "durable" or scenario == "normal" else (3 if scenario == "duplicate" else 2)
                    assert row["effects"] == expected, row
                    if scenario == "lost_ack_uncommitted" and mode == "durable":
                        assert blocked, row
        finally:
            client.close()
    return rows


def restart_bench(root, pi, repeats):
    rows = []
    for mode in ("plain", "durable"):
        for trial in range(repeats):
            folder = root / f"restart-{trial}-{mode}"
            folder.mkdir()
            session = folder / "session.jsonl"
            effect = folder / "effects.txt"
            payload = {"type": "bash", "command": f"printf 'effect\\n' >> {shlex.quote(str(effect))}"}
            calls = 0
            start = time.perf_counter()
            # Natural EOF/reopen of benchmark-owned Pi only, NOT crash recovery.
            # Native session JSONL persists too; durable mode additionally has receipts.
            for _ in range(2):
                client = Pi(folder, pi, session=session)
                try:
                    def action():
                        nonlocal calls
                        calls += 1
                        return client.bash("restart-id", payload["command"])
                    if mode == "durable":
                        Receipts(folder / "receipts.sqlite3").dispatch("restart-id", payload, action)
                    else:
                        action()
                finally:
                    client.close()
            effects = len(effect.read_text().splitlines())
            assert effects == (1 if mode == "durable" else 2)
            rows.append({"mode": mode, "scenario": "clean_pi_restart", "trial": trial,
                         "rpc_calls": calls, "effects": effects, "blocked": False,
                         "ms": (time.perf_counter() - start) * 1000})
    return rows


def parallel_bench(root, pi, repeats):
    rows = []
    for mode in ("plain", "durable"):
        folder = root / f"parallel-{mode}"
        folder.mkdir()
        clients = []
        for index in range(2):
            cwd = folder / str(index)
            cwd.mkdir()
            clients.append(Pi(cwd, pi))
        store = Receipts(folder / "receipts.sqlite3")
        try:
            for trial in range(repeats):
                def work(index):
                    command_id = f"independent-{trial}-{index}"
                    effect = folder / f"{command_id}.txt"
                    script = f"import time,pathlib;time.sleep(0.2);pathlib.Path({str(effect)!r}).write_text('ok')"
                    command = f"python3 -c {shlex.quote(script)}"
                    def action():
                        return clients[index].bash(command_id, command)
                    result = store.dispatch(command_id, {"command": command}, action) if mode == "durable" else action()
                    assert effect.read_text() == 'ok'
                    return result
                start = time.perf_counter()
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                    list(pool.map(work, range(2)))
                rows.append({"mode": mode, "scenario": "independent_parallel", "trial": trial,
                             "rpc_calls": 2, "effects": 2, "blocked": False,
                             "ms": (time.perf_counter() - start) * 1000})
        finally:
            for client in clients:
                client.close()
    return rows


def model_metadata(state):
    model = state.get("model") or {}
    return {"provider": model.get("provider"), "id": model.get("id"), "api": model.get("api"), "thinkingLevel": state.get("thinkingLevel")}


PROMPT = "Authorized disposable fixture for Plane MEGAI-219 (already In Progress); no production files. Fix slug.py: slug(value) must trim outer whitespace, lowercase, and replace each consecutive run of spaces or underscores by one hyphen; do not modify test_slug.py. Run python3 -m unittest -v test_slug before finishing. Do not use git or network."
FIXTURE = '''import unittest\nfrom slug import slug\nclass SlugTest(unittest.TestCase):\n    def test_examples(self):\n        for value, expected in [('  Hello__WORLD  ', 'hello-world'), ('a   b_c', 'a-b-c'), ('Already-ok', 'already-ok'), ('', '')]:\n            self.assertEqual(slug(value), expected)\n'''


def coding_bench(root, pi, repeats):
    rows = []
    for trial in range(repeats):
        modes = ["plain", "durable"] if trial % 2 == 0 else ["durable", "plain"]
        for mode in modes:
            folder = root / f"coding-{trial}-{mode}"
            folder.mkdir()
            (folder / "slug.py").write_text('def slug(value):\n    return value\n')
            (folder / "test_slug.py").write_text(FIXTURE)
            client = Pi(folder, pi)
            store = Receipts(folder / "receipts.sqlite3")
            actual = []
            command_id = f"coding-{trial}"
            try:
                for attempt in range(2):
                    def action():
                        result = client.prompt(command_id, PROMPT)
                        actual.append(result)
                        return result
                    result, ms = elapsed(lambda: store.dispatch(command_id, {"type": "prompt", "message": PROMPT}, action)
                                         if mode == "durable" else action())
                    checked = subprocess.run(["python3", "-m", "unittest", "-v", "test_slug"], cwd=folder,
                                             capture_output=True, text=True, timeout=10)
                    (folder / f"acceptance-{attempt}.log").write_text(checked.stdout + checked.stderr)
                    assert (folder / "test_slug.py").read_text() == FIXTURE, "model modified acceptance tests"
                    rows.append({"mode": mode, "scenario": "live_coding", "trial": trial, "attempt": attempt,
                                 "ms": ms, "accepted": checked.returncode == 0, "provider_failed": result["failed"],
                                 "actual_prompt_calls": len(actual), "usage_this_call": actual[-1]["usage"] if attempt == 0 or mode == "plain" else {},
                                 "model": model_metadata(client.state)})
                    assert checked.returncode == 0 and not result["failed"], rows[-1]
            finally:
                client.close()
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pi", default=shutil.which("pi"))
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--live", type=int, default=0, help="paid/model-backed coding pairs; zero disables")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    metadata = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "pi_version": subprocess.check_output([args.pi, "--version"], text=True).strip(),
                "pi": str(Path(args.pi).resolve()), "python": os.sys.version, "node": subprocess.check_output(["node", "--version"], text=True).strip(),
                "scope": "isolated Pi RPC with -ne -ns -np --no-themes; no selected model overrides",
                "prototype": "original SQLite receipt wrapper inspired by T3, not upstream runtime"}
    rows = []
    try:
        if args.smoke:
            folder = args.out / "smoke"
            folder.mkdir()
            client = Pi(folder, args.pi)
            try:
                metadata["state"] = model_metadata(client.state)
                rows.append({"bash": client.bash("probe", "printf READY")})
                if args.live:
                    rows.append({"live": client.prompt("probe-live", "Reply exactly READY. Do not use any tools.", timeout=60)})
            finally:
                client.close()
        else:
            rows += local_bench(args.out, args.pi, args.repeats)
            rows += restart_bench(args.out, args.pi, min(args.repeats, 5))
            rows += parallel_bench(args.out, args.pi, min(args.repeats, 10))
            if args.live:
                rows += coding_bench(args.out, args.pi, args.live)
    finally:
        (args.out / "results.json").write_text(json.dumps({"metadata": metadata, "rows": rows}, indent=2) + "\n")
    print(json.dumps({"out": str(args.out), "rows": len(rows), "metadata": metadata}, indent=2))


if __name__ == "__main__":
    main()

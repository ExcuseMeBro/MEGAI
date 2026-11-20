"""Opt-in POSIX rollout pilot. Worker releases are inert synthetic files."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import hmac
import json
import os
import re
import stat
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from itertools import islice
from pathlib import Path

COMPONENTS = ("pi-runtime", "skills", "plugins", "managed-config")
TEMP_ROOT = Path("/tmp").resolve(strict=True)
PREFIX = "megai-coordinator-"
NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")
DIGEST = re.compile(r"[0-9a-f]{64}")
MAX_WORKERS, MAX_PARALLEL, MAX_RUNS = 32, 8, 128
MANIFEST_LIMIT, STATE_LIMIT = 4096, 2 * 1024 * 1024


class RolloutError(Exception):
    pass


def valid_name(value):
    return isinstance(value, str) and NAME.fullmatch(value) is not None


def validate_inventory(canary, followers, max_parallel):
    names = [canary, *followers]
    if (not 2 <= len(names) <= MAX_WORKERS or not all(map(valid_name, names))
            or len(set(names)) != len(names)):
        raise RolloutError("use 2–32 distinct lowercase worker IDs")
    if type(max_parallel) is not int or not 1 <= max_parallel <= MAX_PARALLEL:
        raise RolloutError("max parallel must be 1–8")


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RolloutError("duplicate JSON field")
        result[key] = value
    return result


def decode(raw):
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_keys)
    except (ValueError, RecursionError) as exc:
        raise RolloutError("invalid JSON document") from exc


def regular_file(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    stream = os.fdopen(fd, "rb")
    meta = os.fstat(fd)
    if not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1:
        stream.close()
        raise RolloutError("expected a regular, non-linked file")
    return stream


def read_bounded(path, limit):
    with regular_file(path) as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise RolloutError("file exceeds its size limit")
    return raw


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_json(path, value, limit):
    raw = encode(value)
    if len(raw) > limit:
        raise RolloutError("sandbox document exceeds its size limit")
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".writing-", delete=False) as f:
        stage = Path(f.name)
        try:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
            os.replace(stage, path)
            sync_dir(path.parent)
        finally:
            stage.unlink(missing_ok=True)


def private_dir(path, *, create=False):
    if create:
        try:
            path.mkdir(mode=0o700)
        except FileExistsError:
            pass
        else:
            sync_dir(path.parent)
    meta = path.lstat()
    if not stat.S_ISDIR(meta.st_mode) or meta.st_uid != os.getuid() or meta.st_mode & 0o077:
        raise RolloutError("expected a private, non-symlinked sandbox directory")
    return path


def synthetic_bundle(version):
    if not valid_name(version):
        raise RolloutError("use a lowercase version ID of 1–32 characters")
    return {
        "schema": 1,
        "version": version,
        "components": {part: f"synthetic:{part}:{version}" for part in COMPONENTS},
    }


def load_bundle(path, approved):
    if not DIGEST.fullmatch(approved):
        raise RolloutError("expected a lowercase SHA-256 digest")
    raw = read_bounded(path, MANIFEST_LIMIT)
    if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), approved):
        raise RolloutError("bundle digest mismatch")
    manifest = decode(raw)
    if (not isinstance(manifest, dict) or type(manifest.get("schema")) is not int
            or manifest != synthetic_bundle(manifest.get("version"))):
        raise RolloutError("only the four exact synthetic components are supported")
    return manifest


def expected_files(manifest):
    return {f"{part}.txt": (manifest["components"][part] + "\n").encode()
            for part in COMPONENTS}


class LocalWorker:
    """Stage verified, inert files; the coordinator alone publishes activation."""

    def __init__(self, root):
        self.root = root

    def stage(self, worker, manifest, digest):
        workers = private_dir(self.root / "workers")
        base = private_dir(workers / worker, create=True)
        release = base / digest
        try:
            release.lstat()
        except FileNotFoundError:
            with tempfile.TemporaryDirectory(dir=base, prefix=".staging-") as tmp:
                stage = Path(tmp)
                for name, payload in expected_files(manifest).items():
                    fd = os.open(stage / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    with os.fdopen(fd, "wb") as f:
                        f.write(payload)
                        f.flush()
                        os.fsync(f.fileno())
                self.verify_release(stage, manifest)
                sync_dir(stage)
                os.rename(stage, release)
                sync_dir(base)
        self.verify_release(release, manifest)

    @staticmethod
    def verify_release(release, manifest):
        private_dir(release)
        expected = expected_files(manifest)
        if {p.name for p in islice(release.iterdir(), len(expected) + 1)} != expected.keys():
            raise RolloutError("unexpected worker release layout")
        for name, payload in expected.items():
            if read_bounded(release / name, len(payload)) != payload:
                raise RolloutError("worker component verification failed")

    def health(self, worker, manifest, digest):
        base = private_dir(private_dir(self.root / "workers") / worker)
        self.verify_release(base / digest, manifest)


class Coordinator:
    def __init__(self, root):
        root = Path(root)
        if root.parent != TEMP_ROOT or not re.fullmatch(re.escape(PREFIX) + r"[a-z0-9_]{8}", root.name):
            raise RolloutError("use the exact sandbox path returned by init")
        self.root = private_dir(root)
        self.adapter = LocalWorker(self.root)

    @classmethod
    def initialize(cls, canary, followers, max_parallel):
        validate_inventory(canary, followers, max_parallel)
        root = Path(tempfile.mkdtemp(prefix=PREFIX, dir=TEMP_ROOT))
        try:
            (root / ".writer").touch(mode=0o600, exist_ok=False)
            (root / "workers").mkdir(mode=0o700)
            (root / "bundles").mkdir(mode=0o700)
            atomic_json(root / "state.json", {
                "schema": 1,
                "canary": canary,
                "followers": followers,
                "max_parallel": max_parallel,
                "active": dict.fromkeys([canary, *followers]),
                "runs": {},
                "pending": None,
            }, STATE_LIMIT)
            sync_dir(root.parent)
        except BaseException:
            # This path and all entries were created exclusively by this init.
            for name in ("state.json", ".writer"):
                (root / name).unlink(missing_ok=True)
            for name in ("workers", "bundles"):
                if (root / name).is_dir():
                    (root / name).rmdir()
            root.rmdir()
            raise
        return root

    @property
    def journal(self):
        return self.root / "state.json"

    def status(self):
        state = decode(read_bounded(self.journal, STATE_LIMIT))
        if (not isinstance(state, dict) or state.get("schema") != 1
                or not isinstance(state.get("followers"), list)):
            raise RolloutError("invalid sandbox journal")
        validate_inventory(state.get("canary"), state["followers"], state.get("max_parallel"))
        return state

    @contextmanager
    def writer(self):
        with regular_file(self.root / ".writer") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RolloutError("sandbox already has a writer") from exc
            yield

    def save(self, state):
        atomic_json(self.journal, state, STATE_LIMIT)

    def bundle_path(self, version):
        if not valid_name(version):
            raise RolloutError("use a lowercase bundle ID of 1–32 characters")
        return private_dir(self.root / "bundles") / f"{version}.json"

    def create_bundle(self, version):
        manifest = synthetic_bundle(version)
        digest = hashlib.sha256(encode(manifest)).hexdigest()
        with self.writer():
            path = self.bundle_path(version)
            try:
                load_bundle(path, digest)
            except FileNotFoundError:
                if sum(1 for _ in islice(path.parent.iterdir(), MAX_RUNS)) >= MAX_RUNS:
                    raise RolloutError("sandbox bundle storage is full; use a new pilot sandbox")
                atomic_json(path, manifest, MANIFEST_LIMIT)
        return {"bundle": version, "sha256": digest}

    def rollout(self, version, digest):
        with self.writer():
            state = self.status()
            if state["pending"] is not None:
                raise RolloutError("interrupted rollout; run recover before starting another")
            manifest = load_bundle(self.bundle_path(version), digest)
            if manifest["version"] != version:
                raise RolloutError("bundle version must match its ID")
            if version in state["runs"]:
                run = state["runs"][version]
                if not hmac.compare_digest(run["sha256"], digest):
                    raise RolloutError("version already bound to a different bundle digest")
                return {"duplicate": True, "run": run}
            if len(state["runs"]) >= MAX_RUNS:
                raise RolloutError("sandbox rollout history is full; use a new pilot sandbox")
            run = {
                "version": version, "sha256": digest, "status": "running",
                "previous": state["active"].copy(),
                "workers": dict.fromkeys(state["active"], "unscheduled"),
                "failure": None,
            }
            state["runs"][version] = run
            state["pending"] = version
            self.save(state)
            followers = state["followers"]
            cap = state["max_parallel"]
            waves = ([state["canary"]], *(followers[i:i + cap] for i in range(0, len(followers), cap)))
            with ThreadPoolExecutor(max_workers=cap) as pool:
                for wave in waves:
                    self.record(state, run, wave, "staging")
                    failures = self.parallel(pool, self.adapter.stage, wave, manifest, digest)
                    if failures:
                        return self.fail(state, run, failures, "staging")
                    for worker in wave:
                        state["active"][worker] = {"version": version, "sha256": digest}
                    self.record(state, run, wave, "activated")
                    failures = self.parallel(pool, self.adapter.health, wave, manifest, digest)
                    if failures:
                        return self.fail(state, run, failures, "health")
                    self.record(state, run, wave, "healthy")
            run["status"] = "succeeded"
            state["pending"] = None
            self.save(state)
            return {"duplicate": False, "run": run}

    def record(self, state, run, wave, status):
        run["workers"].update(dict.fromkeys(wave, status))
        self.save(state)

    @staticmethod
    def parallel(pool, operation, wave, manifest, digest):
        jobs = {worker: pool.submit(operation, worker, manifest, digest) for worker in wave}
        failures = []
        for worker, job in jobs.items():
            try:
                job.result()
            except (RolloutError, OSError):
                failures.append(worker)
        return failures

    def restore(self, state, run, status):
        state["active"] = run["previous"].copy()
        for worker, phase in run["workers"].items():
            if phase != "unscheduled":
                run["workers"][worker] = "rolled_back"
        run["status"] = status
        state["pending"] = None
        self.save(state)

    def fail(self, state, run, workers, phase):
        run["failure"] = {"phase": phase, "workers": workers}
        self.restore(state, run, "failed")
        return {"duplicate": False, "run": run}

    def recover(self):
        with self.writer():
            state = self.status()
            version = state["pending"]
            if version is None:
                return {"recovered": False}
            run = state["runs"][version]
            self.restore(state, run, "interrupted")
            return {"recovered": True, "run": run}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    bundle = sub.add_parser("bundle", help="create an inert synthetic bundle in the sandbox")
    bundle.add_argument("--sandbox", type=Path, required=True)
    bundle.add_argument("--version", required=True)
    init = sub.add_parser("init", help="provision a new private temporary sandbox")
    init.add_argument("--canary", required=True)
    init.add_argument("--follower", action="append", required=True)
    init.add_argument("--max-parallel", type=int, default=2)
    for command in ("rollout", "status", "recover"):
        action = sub.add_parser(command)
        action.add_argument("--sandbox", type=Path, required=True)
        if command == "rollout":
            action.add_argument("--bundle", required=True, help="sandbox bundle ID")
            action.add_argument("--sha256", required=True)
    args = parser.parse_args(argv)
    code = 0
    try:
        if args.command == "init":
            result = {"sandbox": str(Coordinator.initialize(args.canary, args.follower, args.max_parallel))}
        else:
            coordinator = Coordinator(args.sandbox)
            if args.command == "bundle":
                result = coordinator.create_bundle(args.version)
            elif args.command == "rollout":
                result = coordinator.rollout(args.bundle, args.sha256)
                code = 0 if result["run"]["status"] == "succeeded" else 1
            elif args.command == "status":
                result = coordinator.status()
            else:
                result = coordinator.recover()
    except (RolloutError, OSError) as exc:
        print(f"coordinator: {exc.strerror if isinstance(exc, OSError) else exc}", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(encode(result))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

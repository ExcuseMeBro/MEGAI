#!/usr/bin/env python3
"""Explicit local, label-scoped Docker cleanup after verified remote-dev delivery."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

PREFIX = "io.megai."
KINDS = ("container", "network", "volume", "image")


class Refused(RuntimeError):
    pass


def run(argv, env=None):
    result = subprocess.run(argv, text=True, capture_output=True, timeout=90, env=env)
    if result.returncode:
        # Avoid echoing subprocess output (container metadata may contain secrets).
        raise Refused(f"Command failed ({result.returncode}): {argv[0]} {argv[1]}")
    return result.stdout.strip()


def git(repo, *args):
    return run(["git", "-C", str(repo), *args])


def labels(repo, task):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", task):
        raise Refused("Task must be a unique lowercase slug (1-80 characters)")
    common = git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    identity = hashlib.sha256(str(Path(common).resolve()).encode()).hexdigest()
    return {PREFIX + "repo": identity, PREFIX + "task": task,
            PREFIX + "disposable": "true"}


def owned(metadata, expected):
    return isinstance(metadata, dict) and all(metadata.get(k) == v for k, v in expected.items())


def verify_delivery(repo, commit, remote):
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        raise Refused("Use the full delivered commit SHA")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", remote):
        raise Refused("Invalid remote name")
    if not git(repo, "symbolic-ref", "--short", "HEAD").startswith("task/"):
        raise Refused("Run before removing the task worktree, on its task/ branch")
    if git(repo, "status", "--porcelain", "--untracked-files=normal"):
        raise Refused("Task worktree has uncommitted changes")
    if git(repo, "rev-parse", "HEAD") != commit:
        raise Refused("Commit must equal the task worktree HEAD")
    # Explicit refspec prevents trusting a stale remote-tracking ref or custom fetch config.
    git(repo, "fetch", "--no-tags", remote, f"refs/heads/dev:refs/remotes/{remote}/dev")
    git(repo, "merge-base", "--is-ancestor", commit, f"refs/remotes/{remote}/dev")


class Docker:
    def __init__(self, context):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", context):
            raise Refused("Invalid Docker context")
        self.context = context
        self.env = {k: v for k, v in os.environ.items()
                    if k not in {"DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH"}}
        contexts = json.loads(run(["docker", "context", "inspect", context], self.env))
        endpoint = contexts[0]["Endpoints"]["docker"]["Host"]
        if not endpoint.startswith("unix:///"):
            raise Refused("Cleanup supports explicit local Unix-socket contexts only")
        # Pin the endpoint, not the mutable context name, for this invocation.
        self.base = ["docker", "--host", endpoint]
        self.kiri_store = (Path.home() / "Library/Application Support/kiri"
                           if endpoint == "unix://" + str(Path.home() / ".kiri/run/docker.sock") else None)
        self.call("version", "--format", "{{.Server.Version}}")

    def call(self, *args):
        return run([*self.base, *args], self.env)

    def inspect(self, kind, identity):
        data = json.loads(self.call(kind, "inspect", identity))
        if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
            raise Refused("Unexpected inspect response")
        item = data[0]
        if item.get("Config") is not None and not isinstance(item["Config"], dict):
            raise Refused("Unexpected resource config")
        if kind == "image" and self.kiri_store and "Labels" not in (item.get("Config") or {}):
            # Kiri omits image labels from both Docker list and inspect responses.
            # Read only the content-addressed config, verify its digest, never
            # infer ownership from a tag and never modify Kiri's internal store.
            item.setdefault("Config", {})["Labels"] = kiri_image_labels(self.kiri_store, canonical(kind, item))
        return item

    def candidates(self, kind, expected):
        args = [kind, "ls", "--quiet"]
        if kind in ("container", "image"):
            args += ["--all", "--no-trunc"]
        if kind != "image" or not self.kiri_store:
            for key, value in expected.items():
                args += ["--filter", f"label={key}={value}"]
        return sorted(set(self.call(*args).split()))


def kiri_image_labels(store, identity):
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", identity):
        raise Refused("Invalid Kiri config digest")
    path = store / "blobs/sha256" / identity[7:]
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise Refused("Kiri image config is not a regular file")
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024 or hashlib.sha256(raw).hexdigest() != identity[7:]:
        raise Refused("Kiri config size/digest validation failed")
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get("config"), dict):
        raise Refused("Invalid Kiri image config")
    return data["config"].get("Labels")


def metadata(kind, item):
    if kind in ("container", "image"):
        return (item.get("Config") or {}).get("Labels")
    return item.get("Labels")


def canonical(kind, item):
    key = "Name" if kind == "volume" else "Id"
    value = item.get(key)
    pattern = r"[A-Za-z0-9][A-Za-z0-9_.-]{0,254}" if kind == "volume" else r"(?:sha256:)?[0-9a-f]{64}"
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise Refused("Invalid resource identity")
    return value


def cleanup(docker, expected, apply=False):
    plan = []
    # Inspect ALL candidates before any mutation. Filters alone are not trusted.
    for kind in KINDS:
        for candidate in docker.candidates(kind, expected):
            item = docker.inspect(kind, candidate)
            if owned(metadata(kind, item), expected):
                plan.append((kind, canonical(kind, item)))
    for kind, identity in plan:
        if not apply:
            print(json.dumps({"action": "preview", "kind": kind, "id": identity}))
            continue
        item = docker.inspect(kind, identity)
        if canonical(kind, item) != identity or not owned(metadata(kind, item), expected):
            raise Refused("Resource ownership changed; refusing removal")
        if kind == "container":
            state = item.get("State", {})
            if state.get("Running"):
                docker.call("container", "stop", "--time", "10", identity)
            # No force, no -v: anonymous volumes are not implicitly disposable.
            docker.call("container", "rm", identity)
        elif kind == "network":
            if item.get("Containers"):
                raise Refused("Network still has attached containers; refusing removal")
            docker.call("network", "rm", identity)
        else:
            # Engine rejects in-use volumes/images; never force deletion or prune.
            docker.call(kind, "rm", identity)
        print(json.dumps({"action": "remove", "kind": kind, "id": identity}), flush=True)
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("labels", "cleanup"))
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--task", required=True)
    parser.add_argument("--context", default="kiri")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--commit")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        expected = labels(args.repo, args.task)
        if args.action == "labels":
            if args.apply:
                raise Refused("--apply is only valid for cleanup")
            print(json.dumps(expected, sort_keys=True))
        else:
            verify_delivery(args.repo, args.commit or "", args.remote)
            cleanup(Docker(args.context), expected, args.apply)
        return 0
    except (Refused, OSError, ValueError, KeyError, IndexError, TypeError, subprocess.TimeoutExpired) as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

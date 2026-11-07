#!/usr/bin/env python3
"""Authorized local disposable Docker roundtrip plus installed config readback."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("resources", ROOT / "scripts/task_resources.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", required=True)
    args = parser.parse_args()
    docker = m.Docker(args.context)
    # Readiness check and existing tiny base image: no pull required.
    docker.inspect("image", "alpine:3")
    name = "megai-check-" + uuid.uuid4().hex[:12]
    made = []
    with tempfile.TemporaryDirectory(prefix=name) as temp:
        origin, repo = (Path(temp) / n for n in ("remote.git", "repo"))
        m.run(["git", "init", "--bare", str(origin)])
        m.run(["git", "clone", str(origin), str(repo)])
        m.git(repo, "config", "user.email", "test@example.invalid")
        m.git(repo, "config", "user.name", "Test")
        m.git(repo, "checkout", "-b", "task/runtime")
        m.git(repo, "commit", "--allow-empty", "-m", "isolated runtime fixture")
        sha = m.git(repo, "rev-parse", "HEAD")
        m.git(repo, "push", "origin", "HEAD:dev")
        expected = m.labels(repo, name)
        flags = [part for k, v in expected.items() for part in ("--label", f"{k}={v}")]
        command = [sys.executable, str(ROOT / "scripts/task_resources.py"), "cleanup", "--repo", str(repo), "--task", name, "--context", args.context, "--commit", sha]
        try:
            volume = docker.call("volume", "create", *flags, name + "-data")
            made.append(("volume", volume))
            network = docker.call("network", "create", *flags, name + "-net")
            made.append(("network", network))
            # Build a minimal labelled image, without a network-enabled RUN step.
            build = Path(temp) / "build"
            build.mkdir()
            (build / "Dockerfile").write_text("FROM alpine:3\n" + "\n".join(f"LABEL {k}={v}" for k, v in expected.items()) + "\n")
            image_tag = name + ":test"
            docker.call("build", "--network", "none", "--tag", image_tag, str(build))
            made.append(("image", image_tag))
            container = docker.call("container", "run", "-d", *flags, "--name", name, "--network", network, "--mount", f"type=volume,source={volume},target=/fixture", image_tag, "sleep", "300")
            made.append(("container", container))
            preserved = []
            for suffix, labels in (("retained", {**expected, m.PREFIX + "disposable": "false"}), ("foreign", {**expected, m.PREFIX + "task": "other-" + name}), ("unlabelled", {})):
                opts = [part for k, v in labels.items() for part in ("--label", f"{k}={v}")]
                v = docker.call("volume", "create", *opts, name + "-" + suffix)
                made.append(("volume", v))
                preserved.append(v)
            preview = [json.loads(line) for line in m.run(command).splitlines()]
            assert len(preview) == 4, preview
            assert all(p["action"] == "preview" for p in preview)
            for kind, identity in made:
                docker.inspect(kind, identity)
            result = [json.loads(line) for line in m.run([*command, "--apply"]).splitlines()]
            assert len(result) == 4 and all(p["action"] == "remove" for p in result)
            for kind, identity in (("container", container), ("volume", volume), ("network", network), ("image", image_tag)):
                try:
                    docker.inspect(kind, identity)
                except m.Refused:
                    made.remove((kind, identity))
                else:
                    raise AssertionError(f"Task {kind} survived cleanup")
            for v in preserved:
                docker.inspect("volume", v)
            assert m.run([*command, "--apply"]) == "", "Repeat must be idempotent"
            print("PASS real CLI: preview, labelled cleanup, preserved volumes, repeat")
        finally:
            # Only IDs created by this test; never discover/prune other resources.
            for kind in m.KINDS:
                for k, identity in list(made):
                    if k != kind:
                        continue
                    if kind == "container":
                        docker.call("container", "stop", "--time", "2", identity)
                    docker.call(kind, "rm", identity)
    home = Path.home()
    installed = home / ".local/bin/megai-task-resources"
    assert installed.read_bytes() == (ROOT / "scripts/task_resources.py").read_bytes()
    policy = (ROOT / "docs/task-resources-policy.md").read_text().strip()
    for relative in (".pi/agent/AGENTS.md", ".codex/AGENTS.md", ".claude/CLAUDE.md"):
        assert policy in (home / relative).read_text(), relative
    disk = home / "Library/Application Support/kiri/vm/data.img"
    assert disk.stat().st_size == 64 * 1024 ** 3, "Kiri VM disk ceiling changed"
    socket = home / ".kiri/run/docker.sock"
    settings = json.loads(m.run(["curl", "--fail", "--silent", "--show-error", "--max-time", "5", "--unix-socket", str(socket), "http://localhost/kiri/builder"]))
    assert settings["cache_gb"] == 8 and settings["idle_secs"] == 300 and settings["cache_limit"] == 8 * 1024 ** 3, settings
    assert not settings["overridden"], "Kiri environment overrides the saved budget"
    assert shutil.which("docker"), "Docker CLI missing"
    print("PASS installed helper SHA256:", hashlib.sha256(installed.read_bytes()).hexdigest())
    print("PASS identical Pi/Codex/Claude policy; Kiri 64 GiB disk, 8 GiB cache/300s saved settings")


if __name__ == "__main__":
    try:
        main()
    except (m.Refused, subprocess.TimeoutExpired) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

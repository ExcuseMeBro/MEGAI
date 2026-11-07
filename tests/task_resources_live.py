#!/usr/bin/env python3
"""Authorized local disposable Docker roundtrip plus installed config readback."""
import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("resources", ROOT / "scripts/task_resources.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", required=True)
    args = parser.parse_args()
    docker = m.Docker(args.context)
    # Readiness check: reuse an already present image, never pull.
    tags = [tag for tag in docker.call("image", "ls", "--format", "{{.Repository}}:{{.Tag}}").splitlines()
            if tag and "<none>" not in tag]
    if not tags:
        raise m.Refused("No usable local base image")
    base = next((tag for tag in tags if tag.startswith("python:3.")), tags[0])
    docker.inspect("image", base)
    name = "megai-check-" + uuid.uuid4().hex[:12]
    made = []
    with tempfile.TemporaryDirectory(prefix=name) as temp:
        origin, repo = (Path(temp) / n for n in ("remote.git", "repo"))
        m.run(["git", "init", "--bare", str(origin)])
        m.run(["git", "clone", str(origin), str(repo)])
        m.git(repo, "config", "user.email", "test@example.invalid")
        m.git(repo, "config", "user.name", "Test")
        m.git(repo, "checkout", "-b", f"task/{name}")
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
            # Kiri's builder needs a context below a host path it mounts (/tmp),
            # not the per-user TMPDIR, otherwise the build silently imports nothing.
            build = Path(tempfile.mkdtemp(dir="/tmp", prefix=name))
            (build / "Dockerfile").write_text(f"FROM {base}\n" + "\n".join(f"LABEL {k}={v}" for k, v in expected.items()) + "\n")
            image_tag = name + ":test"
            # Pinned --host selects the docker-container driver: --load imports the result.
            docker.call("build", "--load", "--network", "none", "--tag", image_tag, str(build))
            made.append(("image", image_tag))
            container = docker.call("container", "run", "-d", *flags, "--name", name, "--network", network, "--mount", f"type=volume,source={volume},target=/fixture", image_tag, "sleep", "300")
            made.append(("container", container))
            preserved = {}
            for suffix, labels in (("retained", {**expected, m.PREFIX + "disposable": "false"}), ("foreign", {**expected, m.PREFIX + "task": "other-" + name}), ("unlabelled", {})):
                opts = [part for k, v in labels.items() for part in ("--label", f"{k}={v}")]
                v = docker.call("volume", "create", *opts, name + "-" + suffix)
                made.append(("volume", v))
                preserved[suffix] = v
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
            for v in preserved.values():
                docker.inspect("volume", v)
            assert m.run([*command, "--apply"]) == "", "Repeat must be idempotent"
            print("PASS real CLI: preview, labelled cleanup, preserved volumes, repeat")
            # Sweep path: the delivered task branch/worktree is gone, so labelled
            # leftovers are reclaimable.
            m.git(repo, "checkout", "dev")
            m.git(repo, "branch", "-D", f"task/{name}")
            stray = docker.call("volume", "create", *flags, name + "-stray")
            made.append(("volume", stray))
            sweep = [sys.executable, str(ROOT / "scripts/task_resources.py"), "sweep", "--context",
                     args.context, "--repo-dir", str(repo), "--min-age-hours", "0"]
            preview = [json.loads(line) for line in m.run(sweep).splitlines()]
            assert any(line["action"] == "preview" and line.get("id") == stray for line in preview), preview
            docker.inspect("volume", stray)
            applied = [json.loads(line) for line in m.run([*sweep, "--apply"]).splitlines()]
            assert any(line["action"] == "remove" and line["id"] == stray for line in applied), applied
            # Disposable=false and unlabelled volumes survive a sweep; a foreign
            # task's disposable volume is its own group and is reclaimed.
            for suffix in ("retained", "unlabelled"):
                docker.inspect("volume", preserved[suffix])
            try:
                docker.inspect("volume", stray)
            except m.Refused:
                made.remove(("volume", stray))
            else:
                raise AssertionError("Labelled leftover survived sweep")
            reserved = docker.call("volume", "create", *flags, name + "-live")
            made.append(("volume", reserved))
            m.git(repo, "branch", f"task/{name}", "dev")
            blocked = [json.loads(line) for line in m.run(sweep).splitlines()]
            live_lines = [line for line in blocked if line.get("id") == reserved]
            assert live_lines == [{"action": "skip", "kind": "volume", "id": reserved,
                                   "task": name, "repo": m.repo_identity(repo),
                                   "reason": "task-branch-active"}], live_lines
            docker.inspect("volume", reserved)
            m.git(repo, "branch", "-D", f"task/{name}")
            print("PASS sweep: merged/released group removed, active task branch preserved")
        finally:
            # Only IDs created by this test; never discover/prune other resources.
            shutil.rmtree(build, ignore_errors=True)
            for kind in m.KINDS:
                for k, identity in made:
                    if k != kind:
                        continue
                    if kind == "container":
                        docker.call("container", "stop", "--time", "2", identity)
                    try:
                        docker.call(kind, "rm", identity)
                    except m.Refused:
                        # Already removed by the verified sweep under test.
                        pass
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
    for extra in (["caches"], ["sweep", "--context", args.context, "--temp-clusters", "--min-age-hours", "0"]):
        lines = m.run([sys.executable, str(ROOT / "scripts/task_resources.py"), *extra]).splitlines()
        assert all(json.loads(line)["action"] for line in lines), lines
    report = json.loads(m.run([sys.executable, str(ROOT / "scripts/task_resources.py"),
                               "mem", "--top", "3"]))
    assert report["kind"] == "memory" and report["total_bytes"] > 0, report
    assert 0 < len(report["top"]) <= 3 and "swap" in report, report
    lines = m.run([sys.executable, str(ROOT / "scripts/task_resources.py"), "sweep",
                   "--context", args.context, "--idle-servers", "--min-idle-hours", "0"]).splitlines()
    assert all(json.loads(line)["action"] for line in lines), lines
    print("PASS read-only cache/temp-cluster/idle-server preview and mem JSON")
    print("PASS installed helper SHA256:", hashlib.sha256(installed.read_bytes()).hexdigest())
    print("PASS identical Pi/Codex/Claude policy; Kiri 64 GiB disk, 8 GiB cache/300s saved settings")


if __name__ == "__main__":
    try:
        main()
    except (m.Refused, subprocess.TimeoutExpired) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

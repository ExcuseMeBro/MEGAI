#!/usr/bin/env python3
"""Fast offline lifecycle checks; no real Docker resources are touched."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("resources", ROOT / "scripts/task_resources.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
LABELS = {m.PREFIX + "repo": "a" * 64, m.PREFIX + "task": "test-1", m.PREFIX + "disposable": "true"}
SHA = "a" * 40


class FakeDocker:
    def __init__(self):
        self.items = {}
        self.calls = []
        self.add("container", "1" * 64, LABELS, State={"Running": True})
        self.add("volume", "owned-volume", LABELS)
        self.add("volume", "retained-volume", {**LABELS, m.PREFIX + "disposable": "false"})
        self.add("volume", "foreign-volume", {**LABELS, m.PREFIX + "task": "other"})
        self.add("volume", "foreign-repo", {**LABELS, m.PREFIX + "repo": "b" * 64})
        self.add("volume", "unlabelled", {})
        self.add("network", "2" * 64, LABELS, Containers={})
        self.add("image", "sha256:" + "3" * 64, LABELS)

    def add(self, kind, identity, labels, **extra):
        item = {"Id": identity, "Name": identity, "Labels": labels, "Config": {"Labels": labels}, **extra}
        self.items[kind, identity] = item

    def candidates(self, kind, expected):
        # Deliberately ignore server-side filtering to exercise client-side checks.
        return [i for k, i in self.items if k == kind]

    def inspect(self, kind, identity):
        return self.items[kind, identity]

    def call(self, *args):
        self.calls.append(args)
        if args[1] == "rm":
            del self.items[args[0], args[-1]]

    def everything(self, kind):
        return [i for k, i in self.items if k == kind]


class LifecycleTests(unittest.TestCase):
    def test_preview_does_not_mutate(self):
        d = FakeDocker()
        with patch("sys.stdout", new=io.StringIO()):
            self.assertEqual(len(m.cleanup(d, LABELS)), 4)
        self.assertEqual(d.calls, [])

    def test_apply_is_scoped_ordered_and_idempotent(self):
        d = FakeDocker()
        with patch("sys.stdout", new=io.StringIO()):
            m.cleanup(d, LABELS, True)
            self.assertEqual(m.cleanup(d, LABELS, True), [])
        self.assertEqual([c[0] for c in d.calls if c[1] == "rm"], list(m.KINDS))
        self.assertEqual(len(d.items), 4)
        self.assertEqual(d.calls[0], ("container", "stop", "--time", "10", "1" * 64))
        self.assertFalse(any("--force" in c or "-v" in c or "prune" in c for c in d.calls))

    def test_preflight_inspect_failure_has_no_mutations(self):
        d = FakeDocker()
        with patch.object(d, "inspect", side_effect=m.Refused("failed")), \
                self.assertRaises(m.Refused):
            m.cleanup(d, LABELS, True)
        self.assertEqual(d.calls, [])

    def test_ownership_rechecked(self):
        d = FakeDocker()
        original = d.inspect
        count = 0

        def inspect(kind, identity):
            nonlocal count
            count += 1
            item = original(kind, identity)
            if count > len(d.items):
                item = {**item, "Config": {"Labels": {}}}
            return item

        with patch.object(d, "inspect", side_effect=inspect), \
                patch("sys.stdout", new=io.StringIO()), self.assertRaises(m.Refused):
            m.cleanup(d, LABELS, True)
        self.assertEqual(d.calls, [])

    def test_attached_network_preserved(self):
        d = FakeDocker()
        d.items = {("network", "2" * 64): d.items["network", "2" * 64]}
        d.items["network", "2" * 64]["Containers"] = {"foreign": {}}
        with patch("sys.stdout", new=io.StringIO()), self.assertRaises(m.Refused):
            m.cleanup(d, LABELS, True)
        self.assertEqual(d.calls, [])

    def test_engine_refusal_is_not_forced(self):
        d = FakeDocker()
        with patch.object(d, "call", side_effect=m.Refused("in use")), \
                patch("sys.stdout", new=io.StringIO()), self.assertRaises(m.Refused):
            m.cleanup(d, LABELS, True)

    def test_delivery_checks_and_explicit_fetch(self):
        with patch.object(m, "git", side_effect=["task/test", "", SHA, "", ""]) as g:
            m.verify_delivery("repo", SHA, "origin")
        self.assertIn(unittest.mock.call("repo", "fetch", "--no-tags", "origin", "refs/heads/dev:refs/remotes/origin/dev"), g.call_args_list)
        self.assertEqual(g.call_args_list[-1], unittest.mock.call("repo", "merge-base", "--is-ancestor", SHA, "refs/remotes/origin/dev"))

    def test_delivery_fail_closed(self):
        for results in (["dev"], ["task/x", " M file"], ["task/x", "", "b" * 40],
                        ["task/x", "", SHA, m.Refused("offline")],
                        ["task/x", "", SHA, "", m.Refused("not merged")]):
            with self.subTest(results=results), patch.object(m, "git", side_effect=results), \
                    self.assertRaises(m.Refused):
                m.verify_delivery("repo", SHA, "origin")

    def test_invalid_inputs(self):
        for task in ("", "../escape", "--help", "two words", "a" * 81):
            with self.assertRaises(m.Refused):
                m.labels("repo", task)
        for commit, remote in (("HEAD", "origin"), (SHA, "--upload-pack=evil"), (SHA, "../x")):
            with self.assertRaises(m.Refused):
                m.verify_delivery("repo", commit, remote)
        with self.assertRaises(m.Refused):
            m.canonical("volume", {"Name": "--all"})

    def test_local_context_and_endpoint_pinning(self):
        for endpoint, allowed in (("ssh://server", False), ("tcp://127.0.0.1:2375", False), ("unix:///tmp/test.sock", True)):
            response = json.dumps([{"Endpoints": {"docker": {"Host": endpoint}}}])
            with patch.object(m, "run", return_value=response) as run:
                if allowed:
                    d = m.Docker("kiri")
                    self.assertEqual(d.base, ["docker", "--host", endpoint])
                    self.assertNotIn("DOCKER_HOST", d.env)
                    self.assertEqual(run.call_count, 2)
                else:
                    with self.assertRaises(m.Refused):
                        m.Docker("kiri")

    def test_cli_requires_delivery_before_docker(self):
        with patch.object(m, "labels", return_value=LABELS), patch.object(m, "Docker") as docker, patch("sys.stderr", new=io.StringIO()):
            self.assertEqual(m.main(["cleanup", "--task", "test"]), 2)
        docker.assert_not_called()

    def test_real_local_git_worktree_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            origin, repo, task = (Path(temp) / n for n in ("origin.git", "repo", "task"))
            m.run(["git", "init", "--bare", str(origin)])
            m.run(["git", "clone", str(origin), str(repo)])
            m.git(repo, "config", "user.email", "test@example.invalid")
            m.git(repo, "config", "user.name", "Test")
            m.git(repo, "checkout", "-b", "dev")
            m.git(repo, "commit", "--allow-empty", "-m", "baseline")
            m.git(repo, "push", "origin", "dev")
            m.git(repo, "worktree", "add", "-b", "task/test", str(task), "dev")
            self.assertEqual(m.labels(repo, "test"), m.labels(task, "test"))
            m.git(task, "commit", "--allow-empty", "-m", "candidate")
            sha = m.git(task, "rev-parse", "HEAD")
            with self.assertRaises(m.Refused):
                m.verify_delivery(task, sha, "origin")
            m.git(repo, "merge", "--ff-only", "task/test")
            m.git(repo, "push", "origin", "dev")
            m.verify_delivery(task, sha, "origin")

    def test_kiri_config_digest_and_type(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Path(temp)
            blobs = store / "blobs/sha256"
            blobs.mkdir(parents=True)
            raw = json.dumps({"config": {"Labels": LABELS}}).encode()
            digest = hashlib.sha256(raw).hexdigest()
            path = blobs / digest
            path.write_bytes(raw)
            self.assertEqual(m.kiri_image_labels(store, "sha256:" + digest), LABELS)
            path.write_bytes(b"tampered")
            with self.assertRaises(m.Refused):
                m.kiri_image_labels(store, "sha256:" + digest)
            path.unlink()
            path.symlink_to(blobs / "other")
            with self.assertRaises(OSError):
                m.kiri_image_labels(store, "sha256:" + digest)
            with self.assertRaises(m.Refused):
                m.kiri_image_labels(store, "sha256:../../escape")
            invalid = b"[]"
            invalid_digest = hashlib.sha256(invalid).hexdigest()
            (blobs / invalid_digest).write_bytes(invalid)
            with self.assertRaises(m.Refused):
                m.kiri_image_labels(store, "sha256:" + invalid_digest)

    def test_installer_syncs_policy_block(self):
        spec = importlib.util.spec_from_file_location(
            "install_task_resources", ROOT / "scripts/install_task_resources.py")
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as temp:
            home, repo = Path(temp) / "home", Path(temp) / "repo"
            (repo / "docs").mkdir(parents=True)
            (repo / "docs/task-resources-policy.md").write_text(
                (ROOT / "docs/task-resources-policy.md").read_text())
            (repo / "pi-defaults").mkdir()
            (repo / "pi-defaults/AGENTS.md").write_text("# Pi\n")
            stale = home / ".claude/CLAUDE.md"
            stale.parent.mkdir(parents=True)
            stale.write_text("# Claude\n\n" + installer.BEGIN + "\nold\n" + installer.END + "\n\ntail\n")
            changed = installer.install(home=home, repo=repo)
            self.assertIn(str(stale), changed)
            self.assertIn(installer.policy_block(), stale.read_text())
            self.assertTrue(stale.read_text().endswith("tail\n"))
            self.assertTrue(os.access(home / ".local/bin/megai-task-resources", os.X_OK))
            self.assertEqual(installer.install(home=home, repo=repo),
                             [str(home / ".local/bin/megai-task-resources")])
            (repo / "docs/task-resources-policy.md").write_text("no markers")
            with self.assertRaises(installer.Refused):
                installer.policy_block(repo / "docs/task-resources-policy.md")

    def test_shared_policy_bytes(self):
        policy = (ROOT / "docs/task-resources-policy.md").read_text().strip()
        self.assertIn(policy, (ROOT / "pi-defaults/AGENTS.md").read_text())
        self.assertIn("--apply", (ROOT / "docs/task-resources.md").read_text())


def real_repo(temp):
    repo = Path(temp) / "repo"
    m.run(["git", "init", "-b", "dev", str(repo)])
    m.git(repo, "config", "user.email", "test@example.invalid")
    m.git(repo, "config", "user.name", "Test")
    m.git(repo, "commit", "--allow-empty", "-m", "baseline")
    return repo


OLD = "2020-01-01T00:00:00.000000000Z"
NEW = "2099-01-01T00:00:00.000000000Z"


class SweepTests(unittest.TestCase):
    def grouped(self, repo_id, task="old-task", when=OLD):
        d = FakeDocker()
        d.items = {}
        lab = {m.PREFIX + "repo": repo_id, m.PREFIX + "task": task, m.PREFIX + "disposable": "true"}
        d.add("container", "1" * 64, lab, State={"Running": False}, Created=when)
        d.add("network", "2" * 64, lab, Containers={}, Created=when)
        d.add("volume", "deadbeef", lab, CreatedAt=when)
        return d, lab

    def sweep(self, d, **kwargs):
        out = io.StringIO()
        with patch("sys.stdout", new=out):
            m.sweep(d, emit=lambda line: out.write(line + "\n"), **kwargs)
        return [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]

    def test_unresolvable_repo_is_skipped(self):
        d, _ = self.grouped("c" * 64)
        lines = self.sweep(d, apply=True)
        self.assertEqual({line["action"] for line in lines}, {"skip"})
        self.assertEqual({line["reason"] for line in lines}, {"repo-unresolved"})
        self.assertEqual(d.calls, [])

    def test_finished_task_group_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = real_repo(temp)
            d, lab = self.grouped(m.labels(repo, "old-task")[m.PREFIX + "repo"])
            self.sweep(d, hints=[repo], apply=True)
            self.assertEqual(sorted(d.items), [])
            self.assertFalse(any("--force" in c or "prune" in c for c in d.calls))
            with tempfile.TemporaryDirectory() as registry:
                self.assertEqual(m.resolve_repo(lab[m.PREFIX + "repo"], path=Path(registry) / "r.json"), None)

    def test_active_task_branch_and_worktree_block(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = real_repo(temp)
            m.git(repo, "branch", "task/old-task")
            d, _ = self.grouped(m.labels(repo, "old-task")[m.PREFIX + "repo"])
            lines = self.sweep(d, hints=[repo], apply=True)
            self.assertEqual({line["reason"] for line in lines}, {"task-branch-active"})
            self.assertEqual(d.calls, [])
            m.git(repo, "branch", "-D", "task/old-task")
            worktree = Path(temp) / "wt"
            m.git(repo, "worktree", "add", "-b", "task/old-task", str(worktree), "dev")
            lines = self.sweep(d, hints=[repo], apply=True)
            self.assertEqual({line["reason"] for line in lines}, {"task-branch-active"})
            self.assertEqual(d.calls, [])

    def test_recent_group_is_skipped(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = real_repo(temp)
            d, _ = self.grouped(m.labels(repo, "old-task")[m.PREFIX + "repo"], when=NEW)
            lines = self.sweep(d, hints=[repo], apply=True)
            self.assertEqual({line["reason"] for line in lines}, {"too-recent"})
            self.assertEqual(d.calls, [])

    def test_invalid_labels_are_reported_not_deleted(self):
        d = FakeDocker()
        d.items = {}
        d.add("volume", "bad-one", {m.PREFIX + "repo": "--help", m.PREFIX + "task": "x",
                                    m.PREFIX + "disposable": "true"}, CreatedAt=OLD)
        d.add("volume", "retained", {**LABELS, m.PREFIX + "disposable": "false"}, CreatedAt=OLD)
        lines = self.sweep(d, apply=True)
        self.assertEqual([line["reason"] for line in lines], ["invalid-labels"])
        self.assertEqual(d.calls, [])

    def test_preview_mutates_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = real_repo(temp)
            d, _ = self.grouped(m.labels(repo, "old-task")[m.PREFIX + "repo"])
            lines = self.sweep(d, hints=[repo])
            self.assertEqual({line["action"] for line in lines}, {"preview"})
            self.assertEqual(d.calls, [])

    def test_anonymous_volume_rules(self):
        d = FakeDocker()
        d.items = {}
        referenced = "a" * 64
        d.add("container", "9" * 64, {}, State={"Running": True}, Created=OLD,
              Mounts=[{"Type": "volume", "Name": referenced}])
        d.add("volume", referenced, None, CreatedAt=OLD)
        d.add("volume", "b" * 64, None, CreatedAt=OLD)
        d.add("volume", "b" * 64 + "x", None, CreatedAt=OLD)
        d.add("volume", "labelled", {m.PREFIX + "disposable": "false"}, CreatedAt=OLD)
        d.add("volume", "c" * 64, None, CreatedAt=NEW)
        out = io.StringIO()
        m.sweep(d, anonymous=True, apply=True, emit=lambda line: out.write(line + "\n"))
        actions = {(json.loads(l)["action"], json.loads(l).get("id")) for l in out.getvalue().splitlines()}
        self.assertIn(("remove", "b" * 64), actions)
        volumes = {i for k, i in d.items if k == "volume"}
        self.assertEqual(volumes, {referenced, "b" * 64 + "x", "labelled", "c" * 64})

    def test_registry_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = real_repo(temp)
            registry = Path(temp) / "state/registry.json"
            identity = m.remember(repo, "old-task", path=registry)
            self.assertEqual(registry.stat().st_mode & 0o777, 0o600)
            self.assertEqual(m.resolve_repo(identity, path=registry), m.repo_common(repo))
            self.assertEqual(m.load_registry(registry)[identity], str(m.repo_common(repo)))
            self.assertEqual(m.resolve_repo("d" * 64, path=registry), None)
            registry.write_text("[]")
            self.assertEqual(m.load_registry(registry), {})

    def test_age_helpers(self):
        self.assertAlmostEqual(m.elapsed_hours("02-13:14:54"), 61.2483, places=3)
        self.assertEqual(m.elapsed_hours("30:00"), 0.5)
        self.assertEqual(m.elapsed_hours("1:00:00"), 1.0)
        self.assertEqual(m.age_hours(None), 0.0)
        self.assertEqual(m.age_hours("2020-01-01T00:00:00Z") > 24 * 365, True)
        # Docker emits nanoseconds and Python 3.9 rejects both `Z` and >6 digits.
        self.assertGreater(m.age_hours("2020-01-01T00:00:00.123456789Z"), 24 * 365)
        self.assertGreater(m.age_hours("2020-01-01T00:00:00"), 24 * 365)
        self.assertEqual(m.age_hours("2999-01-01T00:00:00Z"), 0.0)
        self.assertEqual(m.age_hours("not a stamp"), 0.0)


class TempClusterTests(unittest.TestCase):
    def test_orphan_only_inside_temp_and_old(self):
        with tempfile.TemporaryDirectory() as inside:
            keep = Path(tempfile.mkdtemp(dir="/tmp"))
            try:
                ps = "\n".join([
                    f"  10     1    02-13:14:54 /opt/postgres/bin/postgres -D {keep} -p 51105",
                    f"  11    42    02-13:14:54 /opt/postgres/bin/postgres -D {keep} -p 51106",
                    f"  12     1    00:05 /opt/postgres/bin/postgres -D {keep} -p 51107",
                    f"  13     1    02-13:14:54 /opt/postgres/bin/postgres -D {inside} -p 51108",
                ])
                with patch.object(m, "run", return_value=ps):
                    clusters = m.temp_clusters([Path("/tmp").resolve()])
                self.assertEqual([c["pid"] for c in clusters], [10])
            finally:
                keep.rmdir()

    def test_apply_stops_and_removes(self):
        keep = Path(tempfile.mkdtemp(dir="/tmp"))
        (keep / "data.txt").write_text("x")
        ps = f"  10     1    02-13:14:54 /opt/postgres/bin/postgres -D {keep} -p 51105"
        out = io.StringIO()
        with patch.object(m, "run", return_value=ps), patch.object(m.os, "kill") as kill, \
                patch.object(m.subprocess, "run", return_value=subprocess.CalledProcessError(1, "ps")):
            m.sweep_temp([Path("/tmp").resolve()], apply=True,
                         emit=lambda line: out.write(line + "\n"))
        kill.assert_called_once_with(10, m.signal.SIGTERM)
        self.assertFalse(keep.exists())
        self.assertEqual(json.loads(out.getvalue().splitlines()[0])["action"], "remove")

    def test_swapped_symlink_is_not_removed(self):
        keep = Path(tempfile.mkdtemp(dir="/tmp"))
        target = Path(tempfile.mkdtemp())
        ps = f"  10     1    02-13:14:54 /opt/postgres/bin/postgres -D {keep} -p 51105"
        with patch.object(m, "run", return_value=ps), patch.object(m.os, "kill"), \
                patch.object(m.subprocess, "run", return_value=subprocess.CalledProcessError(1, "ps")):
            keep.rmdir()
            keep.symlink_to(target, target_is_directory=True)
            try:
                out = io.StringIO()
                m.sweep_temp([Path("/tmp").resolve()], apply=True,
                             emit=lambda line: out.write(line + "\n"))
                self.assertTrue(target.exists())
            finally:
                keep.unlink()
                target.rmdir()


class CacheTests(unittest.TestCase):
    def test_unused_gradle_versions_only(self):
        with tempfile.TemporaryDirectory() as temp:
            cache, projects = Path(temp) / "cache", Path(temp) / "projects"
            for name in ("9.6.0", "8.14", "modules-2", "jars-9"):
                (cache / name).mkdir(parents=True)
            wrapper = projects / "app/gradle/wrapper"
            wrapper.mkdir(parents=True)
            (wrapper / "gradle-wrapper.properties").write_text(
                "distributionUrl=https\\://services.gradle.org/distributions/gradle-9.6.0-bin.zip")
            used, stale = m.gradle_cache_plan(cache, projects)
            self.assertEqual(used, {"9.6.0"})
            self.assertEqual([name for name, _ in stale], ["8.14"])
            out = io.StringIO()
            m.sweep_caches(cache, projects, apply=True, emit=lambda line: out.write(line + "\n"))
            self.assertFalse((cache / "8.14").exists())
            self.assertTrue((cache / "modules-2").exists())
            self.assertTrue((cache / "9.6.0").exists())

    def test_unused_wrapper_distributions_only(self):
        with tempfile.TemporaryDirectory() as temp:
            cache, projects = Path(temp) / "cache", Path(temp) / "projects"
            cache.mkdir(parents=True)
            dists = Path(temp) / "wrapper/dists"
            kept, stale = dists / "gradle-9.6.0-bin", dists / "gradle-9.2.0-all"
            for path in (kept, stale, dists / "CACHEDIR.TAG"):
                path.mkdir(parents=True) if path != dists / "CACHEDIR.TAG" else path.write_text("x")
            wrapper = projects / "app/gradle/wrapper"
            wrapper.mkdir(parents=True)
            (wrapper / "gradle-wrapper.properties").write_text(
                "distributionUrl=https\\://services.gradle.org/distributions/gradle-9.6.0-bin.zip")
            out = io.StringIO()
            m.sweep_caches(cache, projects, emit=lambda line: out.write(line + "\n"))
            preview = [json.loads(line) for line in out.getvalue().splitlines()]
            dists_preview = [line for line in preview if line["kind"] == "gradle-dist"]
            self.assertEqual([line["dist"] for line in dists_preview], ["gradle-9.2.0-all"])
            out = io.StringIO()
            m.sweep_caches(cache, projects, apply=True, emit=lambda line: out.write(line + "\n"))
            self.assertFalse(stale.exists())
            self.assertTrue(kept.exists())
            self.assertTrue((dists / "CACHEDIR.TAG").exists())


class FakeSystem:
    """Routes ps/sysctl/vm_stat/lsof calls used by the memory checks."""

    def __init__(self, ps="", mem=8589934592,
                 swap="total = 4096.00M  used = 3072.00M  free = 1024.00M",
                 vm=("Mach Virtual Memory Statistics: (page size of 16384 bytes)\n"
                     "Pages stored in compressor: 1000.\n"
                     "Pages occupied by compressor: 900.\n"
                     "Pages wired down: 200.\n"),
                 clients=(), top=""):
        self.ps, self.mem, self.swap, self.vm = ps, mem, swap, vm
        self.top = top
        self.clients = set(clients)

    def __call__(self, argv, env=None):
        if argv[0] == "ps":
            return self.ps
        if argv[0] == "sysctl":
            if argv[2] == "hw.memsize":
                return str(self.mem)
            if argv[2] == "vm.swapusage":
                return self.swap
        if argv[0] == "vm_stat":
            return self.vm
        if argv[0] == "top":
            if self.top:
                return self.top
            raise m.Refused("Command failed (1): top")
        if argv[0] == "lsof":
            if argv[4] in self.clients:
                return ("COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME\n"
                        "node 1 user 18u IPv4 0x1 0t0 TCP 127.0.0.1:3015")
            raise m.Refused("Command failed (1): lsof")
        raise m.Refused(f"unexpected command: {argv[0]}")


SERVER_PS = (
    "   10     1 09:25:54 989000 node /work/node_modules/@craco/craco/scripts/start.js\n"
    "   11    10 09:25:50 764000 node /work/node_modules/.bin/craco start\n"
    "   20     1 00:20 500000 node /work/node_modules/.bin/vite --port 5173\n"
    "   30     1 12:00:00 8028000 /opt/emulator/emulator -avd Pixel -gpu swiftshader_indirect\n"
    "   40     1 03:45:00 1567000 java -Xmx8G -jar gradle-launcher.jar\n"
    "   50     1 02:15:00 1130000 node billion-context start --port 18788\n"
)

class MemoryTests(unittest.TestCase):
    def test_report_flags_pressure_and_heavy_processes(self):
        with patch.object(m, "run", new=FakeSystem(SERVER_PS)):
            report = m.memory_report(3)
        self.assertEqual(report["total_bytes"], 8589934592)
        self.assertEqual(report["swap"]["used_bytes"], 3 * 1024 ** 3)
        self.assertEqual(len(report["top"]), 3)
        self.assertEqual(report["top"][0]["pid"], 30)
        self.assertEqual({item["kind"] for item in report["heavy"]},
                         {"emulator", "dev-server", "jvm"})
        reasons = {item["reason"] for item in report["warnings"]}
        self.assertIn("swap-pressure", reasons)
        self.assertIn("oversized-jvm-heap", reasons)
        self.assertNotIn("compressor-pressure", reasons)

    def test_footprint_and_heavy_emulator_warning(self):
        top = ("PID    MEM    CMPRS  COMMAND\n"
               "  30  7889M  7381M  qemu-system-aarch\n"
               "  10   989M   931M  node start.js\n")
        with patch.object(m, "run", new=FakeSystem(SERVER_PS, top=top)):
            report = m.memory_report(2)
        self.assertTrue(report["footprint_available"])
        self.assertEqual(report["top"][0]["footprint"], 7889 * 1024 ** 2)
        emulator = next(item for item in report["heavy"] if item["kind"] == "emulator")
        self.assertEqual(emulator["footprint"], 7889 * 1024 ** 2)
        self.assertIn("heavy-emulator", {item["reason"] for item in report["warnings"]})

    def test_footprint_is_optional(self):
        with patch.object(m, "run", new=FakeSystem(SERVER_PS)):
            report = m.memory_report(2)
        self.assertFalse(report["footprint_available"])
        self.assertIsNone(report["top"][0]["footprint"])
        self.assertNotIn("heavy-emulator", {item["reason"] for item in report["warnings"]})

    def test_idle_servers_need_age_and_no_clients(self):
        system = FakeSystem(SERVER_PS, clients={"11"})
        with patch.object(m, "run", new=system):
            servers = m.stale_servers(8.0)
        self.assertEqual([server["pid"] for server in servers], [10])

    def test_preview_never_signals(self):
        out = io.StringIO()
        with patch.object(m, "run", new=FakeSystem(SERVER_PS, clients={"11"})), \
                patch.object(m.os, "kill") as kill:
            m.sweep_servers(8.0, emit=lambda line: out.write(line + "\n"))
        kill.assert_not_called()
        self.assertEqual([json.loads(line)["action"] for line in out.getvalue().splitlines()],
                         ["preview"])

    def test_apply_stops_server_tree(self):
        out = io.StringIO()
        with patch.object(m, "run", new=FakeSystem(SERVER_PS)), \
                patch.object(m.os, "kill") as kill, patch.object(m, "alive", return_value=False):
            m.sweep_servers(8.0, apply=True, emit=lambda line: out.write(line + "\n"))
        self.assertEqual([call.args[0] for call in kill.call_args_list], [10, 11])
        self.assertEqual(json.loads(out.getvalue())["action"], "remove")

    def test_apply_keeps_unrelated_processes(self):
        out = io.StringIO()
        with patch.object(m, "run", new=FakeSystem(SERVER_PS)), \
                patch.object(m.os, "kill") as kill, patch.object(m, "alive", return_value=False):
            m.sweep_servers(8.0, apply=True, emit=lambda line: out.write(line + "\n"))
        killed = {call.args[0] for call in kill.call_args_list}
        self.assertEqual(killed, {10, 11})
        self.assertNotIn(20, killed)
        self.assertNotIn(30, killed)
        self.assertNotIn(40, killed)

    def test_unstopped_server_is_not_reported_removed(self):
        out = io.StringIO()
        with patch.object(m, "run", new=FakeSystem(SERVER_PS)), \
                patch.object(m.os, "kill"), patch.object(m, "alive", return_value=True):
            m.sweep_servers(8.0, apply=True, emit=lambda line: out.write(line + "\n"))
        self.assertEqual(json.loads(out.getvalue().splitlines()[-1])["reason"], "still-running")

    def test_mem_rejects_apply(self):
        with patch.object(m, "run", new=FakeSystem(SERVER_PS)), \
                patch("sys.stdout", new=io.StringIO()), patch("sys.stderr", new=io.StringIO()):
            self.assertEqual(m.main(["mem", "--apply"]), 2)
        self.assertEqual(m.main(["mem", "--top", "0"]), 2)

    def test_mem_prints_json(self):
        out = io.StringIO()
        with patch.object(m, "run", new=FakeSystem(SERVER_PS)), \
                patch("sys.stdout", new=out):
            self.assertEqual(m.main(["mem", "--top", "2"]), 0)
        self.assertEqual(json.loads(out.getvalue())["kind"], "memory")


if __name__ == "__main__":
    unittest.main()


BLOCK = 1024
FIRST_DATA = 1
PER_GROUP = 16
GROUPS = 4
BITMAPS = (3, 4, 5, 6)


def make_ext4(path, free_each=8, declared=None, recover=False, state=1):
    """Synthetic ext4 image: block_size 1024, descriptors at block 2, free-first bitmaps."""
    blocks = FIRST_DATA + GROUPS * PER_GROUP
    image = bytearray(blocks * BLOCK)
    image[1024 + 56:1024 + 58] = b"\x53\xef"
    def put32(offset, value):
        image[offset:offset + 4] = value.to_bytes(4, "little")
    put32(1024 + 4, blocks)
    put32(1024 + 12, GROUPS * free_each if declared is None else declared)
    put32(1024 + 20, FIRST_DATA)
    put32(1024 + 24, 0)
    put32(1024 + 32, PER_GROUP)
    image[1024 + 0x3A:1024 + 0x3C] = state.to_bytes(2, "little")
    put32(1024 + 0x60, 0x4 if recover else 0)
    image[1024 + 0xFE:1024 + 0x100] = (32).to_bytes(2, "little")
    for group in range(GROUPS):
        desc = 2 * BLOCK + group * 32
        put32(desc, BITMAPS[group])
        bitmap = bytearray(BLOCK)
        for index in range(PER_GROUP):
            if index < free_each:
                continue
            bitmap[index >> 3] |= 1 << (index & 7)
        image[BITMAPS[group] * BLOCK:BITMAPS[group] * BLOCK + BLOCK] = bitmap
    Path(path).write_bytes(bytes(image))
    return Path(path)


def make_ext4_uninit(path, declared=55):
    """One uninitialised group (63 blocks from block 1) owning sb/gdt, bitmaps, inode table."""
    blocks = 64
    image = bytearray(blocks * BLOCK)

    def put32(offset, value):
        image[offset:offset + 4] = value.to_bytes(4, "little")

    image[1024 + 56:1024 + 58] = b"\x53\xef"
    put32(1024 + 4, blocks)
    put32(1024 + 12, declared)
    put32(1024 + 20, FIRST_DATA)
    put32(1024 + 24, 0)
    put32(1024 + 32, 64)
    put32(1024 + 0x28, 32)
    image[1024 + 0x3A:1024 + 0x3C] = (1).to_bytes(2, "little")
    image[1024 + 0x58:1024 + 0x5A] = (128).to_bytes(2, "little")
    image[1024 + 0xFE:1024 + 0x100] = (32).to_bytes(2, "little")
    desc = 2 * BLOCK
    put32(desc, 3)
    put32(desc + 4, 4)
    put32(desc + 8, 5)
    image[desc + 0x0C:desc + 0x0E] = declared.to_bytes(2, "little")
    image[desc + 0x12:desc + 0x14] = (0x0002).to_bytes(2, "little")
    Path(path).write_bytes(bytes(image))
    return Path(path)


class DiskTests(unittest.TestCase):
    def test_layout_reads_free_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            image = make_ext4(Path(temp) / "data.img")
            layout = m.ext4_layout(image)
            self.assertEqual(layout["block_size"], BLOCK)
            self.assertEqual(layout["counted_blocks"], GROUPS * 8)
            self.assertEqual(layout["free_blocks"], GROUPS * 8)
            self.assertEqual(layout["runs"][0], (FIRST_DATA, FIRST_DATA + 8))
            self.assertEqual(len(layout["runs"]), GROUPS)

    def test_uninit_group_free_blocks_exclude_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            image = make_ext4_uninit(Path(temp) / "data.img")
            layout = m.ext4_layout(image)
            self.assertEqual(layout["uninit_groups"], 1)
            self.assertEqual(layout["counted_blocks"], 55)
            self.assertEqual(layout["free_blocks"], 55)
            self.assertEqual(layout["runs"], [(9, 64)])
            punched, out = [], io.StringIO()
            m.compact_kiri(image, apply=True, emit=lambda line: out.write(line + "\n"),
                           running=lambda: False, min_reclaim=0,
                           punch=lambda fd, offset, length: punched.append((offset, length)))
            self.assertEqual(punched, [(9 * BLOCK, 55 * BLOCK)])
            self.assertEqual(json.loads(out.getvalue().splitlines()[-1])["action"], "compact")

    def test_uninit_group_count_mismatch_refuses(self):
        with tempfile.TemporaryDirectory() as temp:
            image = make_ext4_uninit(Path(temp) / "data.img", declared=60)
            with self.assertRaises(m.Refused):
                m.ext4_layout(image)

    @unittest.skipUnless(sys.platform == "darwin", "APFS hole punching")
    def test_punch_hole_releases_blocks_without_truncating(self):
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp) / "sparse.img"
            image.write_bytes(os.urandom(4 << 20))
            before = image.stat()
            handle = os.open(image, os.O_RDWR)
            try:
                m.punch_hole(handle, 1 << 20, 2 << 20)
                os.fsync(handle)
            finally:
                os.close(handle)
            after = image.stat()
            self.assertEqual(after.st_size, before.st_size)
            self.assertLess(after.st_blocks, before.st_blocks)

    def test_bad_geometry_refuses(self):
        with tempfile.TemporaryDirectory() as temp:
            image = make_ext4(Path(temp) / "data.img")
            data = bytearray(image.read_bytes())
            data[1024 + 32:1024 + 36] = (20).to_bytes(4, "little")
            Path(image).write_bytes(bytes(data))
            with self.assertRaises(m.Refused):
                m.ext4_layout(image)

    def test_free_count_mismatch_refuses(self):
        with tempfile.TemporaryDirectory() as temp:
            image = make_ext4(Path(temp) / "data.img", declared=99)
            with self.assertRaises(m.Refused):
                m.compact_kiri(image, apply=True, emit=lambda line: None, running=lambda: False,
                               punch=lambda *args: None)

    def test_recovery_pending_skips_and_never_punches(self):
        with tempfile.TemporaryDirectory() as temp:
            image = make_ext4(Path(temp) / "data.img", recover=True)
            calls = []
            out = io.StringIO()
            plan = m.compact_kiri(image, apply=True, emit=lambda line: out.write(line + "\n"),
                                  running=lambda: False, punch=lambda *args: calls.append(args))
            self.assertEqual(plan["reason"], "journal-recovery-pending")
            self.assertEqual(calls, [])

    def test_not_clean_filesystem_skips(self):
        with tempfile.TemporaryDirectory() as temp:
            image = make_ext4(Path(temp) / "data.img", state=0)
            out = io.StringIO()
            plan = m.compact_kiri(image, apply=True, emit=lambda line: out.write(line + "\n"),
                                  running=lambda: False, punch=lambda *args: None)
            self.assertEqual(plan["reason"], "filesystem-not-clean")

    def test_preview_never_punches(self):
        with tempfile.TemporaryDirectory() as temp:
            image = make_ext4(Path(temp) / "data.img", declared=None)
            # Preview needs a reclaimable size above the guard: scale the image instead.
            big = Path(temp) / "big.img"
            data = bytearray(image.read_bytes())
            Path(big).write_bytes(bytes(data) + b"\x00" * (1 << 29))
            calls = []
            out = io.StringIO()
            plan = m.compact_kiri(big, emit=lambda line: out.write(line + "\n"), min_reclaim=0,
                                  punch=lambda *args: calls.append(args))
            lines = [json.loads(line) for line in out.getvalue().splitlines()]
            self.assertEqual(lines[0]["action"], "inspect")
            self.assertEqual(plan["reclaimable_bytes"], GROUPS * 8 * BLOCK)
            self.assertEqual(calls, [])

    def test_small_reclaim_is_skipped(self):
        with tempfile.TemporaryDirectory() as temp:
            image = make_ext4(Path(temp) / "data.img")
            out = io.StringIO()
            plan = m.compact_kiri(image, emit=lambda line: out.write(line + "\n"))
            self.assertEqual(plan["reason"], "nothing-to-reclaim")

    def test_apply_punches_every_free_run(self):
        with tempfile.TemporaryDirectory() as temp:
            image = make_ext4(Path(temp) / "data.img")
            data = bytearray(image.read_bytes())
            Path(image).write_bytes(bytes(data) + b"\x00" * (1 << 29))
            punched = []
            out = io.StringIO()
            m.compact_kiri(image, apply=True, emit=lambda line: out.write(line + "\n"),
                           running=lambda: False, min_reclaim=0,
                           punch=lambda fd, offset, length: punched.append((offset, length)))
            self.assertEqual(punched, [(FIRST_DATA * BLOCK, 8 * BLOCK),
                                       ((FIRST_DATA + 16) * BLOCK, 8 * BLOCK),
                                       ((FIRST_DATA + 32) * BLOCK, 8 * BLOCK),
                                       ((FIRST_DATA + 48) * BLOCK, 8 * BLOCK)])
            summary = json.loads(out.getvalue().splitlines()[-1])
            self.assertEqual(summary["action"], "compact")
            self.assertEqual(summary["punched_bytes"], GROUPS * 8 * BLOCK)

    def test_running_vm_refuses_compaction(self):
        with tempfile.TemporaryDirectory() as temp:
            image = make_ext4(Path(temp) / "data.img")
            Path(image).write_bytes(image.read_bytes() + b"\x00" * (1 << 29))
            with self.assertRaises(m.Refused):
                m.compact_kiri(image, apply=True, emit=lambda line: None, min_reclaim=0,
                               running=lambda: True, punch=lambda *args: None)

    def test_xcode_derived_data_preview_then_removal(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            derived = home / "Library/Developer/Xcode/DerivedData"
            (derived / "Build").mkdir(parents=True)
            (derived / "Build/blob").write_bytes(b"x" * 4096)
            out = io.StringIO()
            m.reclaim(emit=lambda line: out.write(line + "\n"), home=home, xcode=True)
            preview = [json.loads(line) for line in out.getvalue().splitlines()]
            self.assertEqual(preview[0]["action"], "preview")
            self.assertTrue(derived.exists())
            m.reclaim(apply=True, emit=lambda line: None, home=home, xcode=True)
            self.assertFalse(derived.exists())

    def test_xcode_refuses_while_building(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            (home / "Library/Developer/Xcode/DerivedData").mkdir(parents=True)
            rows = [{"pid": 1, "ppid": 0, "command": "/usr/bin/xcodebuild -scheme App"}]
            with self.assertRaises(m.Refused):
                m.xcode_derived_data(home, rows)

    def test_builder_caches_are_named_and_removable(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            go = home / "Library/Caches/go-build"
            go.mkdir(parents=True)
            (go / "blob").write_bytes(b"x" * 4096)
            keep = home / "Library/Caches/Homebrew"
            keep.mkdir(parents=True)
            self.assertIn(("go-build", go), m.builder_caches(home))
            m.reclaim(apply=True, emit=lambda line: None, home=home, builders=True)
            self.assertFalse(go.exists())
            self.assertTrue(keep.exists())

    def test_disk_report_shape(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            (home / "Library/Caches/go-build").mkdir(parents=True)
            image = make_ext4(home / "data.img")
            report = m.disk_report(home, image, var_root=home)
            self.assertGreater(report["volume"]["total_bytes"], 0)
            self.assertEqual(report["kiri"]["guest_free_bytes"], GROUPS * 8 * BLOCK)
            self.assertEqual(report["categories"]["kiri"], image.stat().st_blocks * 512)

    def test_disk_apply_with_kiri_only_reaches_the_reclaim_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            image = make_ext4(Path(temp) / "data.img")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = m.main(["disk", "--kiri-image", str(image), "--apply", "--home", temp,
                               "--var-root", temp])
            self.assertEqual(code, 0)
            self.assertIn('"reason": "nothing-to-reclaim"', out.getvalue())

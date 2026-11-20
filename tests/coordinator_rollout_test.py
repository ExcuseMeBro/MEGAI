"""Source-bound acceptance for the opt-in Coordinator CLI and local worker."""

import errno
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "lib"
SCRIPT = LIB / "coordinator_rollout.py"
sys.path.insert(0, str(LIB))
from coordinator_rollout import Coordinator, LocalWorker, RolloutError

PARTS = ("pi-runtime", "skills", "plugins", "managed-config")
CANARY = "canary"
FOLLOWERS = tuple(f"worker-{n}" for n in range(1, 7))
WORKERS = CANARY, *FOLLOWERS


def file_snapshot(path):
    return {
        str(p.relative_to(path)): (p.stat().st_ino, p.stat().st_mtime_ns, p.read_bytes())
        for p in path.rglob("*") if p.is_file()
    }


class Fixture(unittest.TestCase):
    def setUp(self):
        home_tmp = tempfile.TemporaryDirectory(prefix="megai-1132-home-")
        self.addCleanup(home_tmp.cleanup)
        self.home = Path(home_tmp.name)
        self.env = {"HOME": str(self.home), "TMPDIR": str(self.home)}
        for name in ("auth.json", "settings.json", "sessions/example.json", "extensions/example.py"):
            p = self.home / ".pi/agent" / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("do not touch this synthetic sentinel\n")
        self.outside = file_snapshot(self.home)
        args = [item for worker in FOLLOWERS for item in ("--follower", worker)]
        output = self.cli("init", "--canary", CANARY, *args, "--max-parallel", "2", use_root=False)
        self.root = Path(output["sandbox"])
        self.addCleanup(shutil.rmtree, self.root)
        self.coordinator = Coordinator(self.root)
        initial = self.make_bundle("v1")
        self.assertEqual(self.release("v1", initial)["run"]["status"], "succeeded")
        self.initial = {w: {"version": "v1", "sha256": initial} for w in WORKERS}

    def cli(self, command, *args, rc=0, use_root=True, error=None):
        scope = ("--sandbox", str(self.root)) if use_root else ()
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(SCRIPT), command, *scope, *args],
            check=False, capture_output=True, text=True, timeout=8, env=self.env,
        )
        self.assertEqual(result.returncode, rc, result.stderr or result.stdout)
        if error:
            self.assertIn(error, result.stderr)
        return json.loads(result.stdout) if result.stdout else None

    def make_bundle(self, version):
        return self.cli("bundle", "--version", version)["sha256"]

    def release(self, version, digest, **kwargs):
        return self.cli("rollout", "--bundle", version, "--sha256", digest, **kwargs)

    def worker_files(self, worker):
        return file_snapshot(self.root / "workers" / worker)

    def assert_initial(self):
        self.assertEqual(self.cli("status")["active"], self.initial)
        self.assertEqual(file_snapshot(self.home), self.outside)
        for worker in WORKERS:
            self.assert_payload(worker, "v1", self.initial[worker]["sha256"])

    def assert_payload(self, worker, version, digest):
        release = self.root / "workers" / worker / digest
        files = {p.name: p.read_text() for p in release.iterdir()}
        self.assertEqual(files, {f"{name}.txt": f"synthetic:{name}:{version}\n" for name in PARTS})


class Baseline(Fixture):
    def test_cli_installs_all_four_components_and_persists_state(self):
        self.assert_initial()
        state = self.cli("status")  # Separate invocation, not the writer's in-memory state.
        self.assertEqual(state["runs"]["v1"]["workers"], dict.fromkeys(WORKERS, "healthy"))
        self.assertIsNone(state["pending"])
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)
        self.assertNotEqual(self.root.parent, self.home)
        print("observed: CLI v1; 7 workers × 4 on-disk files; separate status read; Pi sentinels unchanged")


class HealthyParallel(Fixture):
    def test_canary_gates_real_overlapping_followers(self):
        case = self
        barrier = threading.Barrier(2, timeout=3)
        mutex = threading.Lock()
        timeline = []
        inside = set()
        overlaps = []
        peak = 0

        class ObservedWorker(LocalWorker):
            def stage(self, worker, manifest, digest):
                nonlocal peak
                with mutex:
                    inside.add(worker)
                    peak = max(peak, len(inside))
                    timeline.append(("stage", worker))
                if worker in FOLLOWERS[:2]:
                    barrier.wait()
                    with mutex:
                        overlaps.append(frozenset(inside))
                super().stage(worker, manifest, digest)
                if worker in FOLLOWERS[:2]:
                    barrier.wait()
                with mutex:
                    inside.remove(worker)

            def health(self, worker, manifest, digest):
                status = case.coordinator.status()
                case.assertEqual(status["active"][worker]["sha256"], digest)
                case.assertEqual(status["runs"]["v2"]["workers"][worker], "activated")
                if worker != CANARY:
                    case.assertEqual(status["runs"]["v2"]["workers"][CANARY], "healthy")
                super().health(worker, manifest, digest)
                with mutex:
                    timeline.append(("healthy", worker))

        self.coordinator.adapter = ObservedWorker(self.root)
        digest = self.make_bundle("v2")
        result = self.coordinator.rollout("v2", digest)
        self.assertEqual(result["run"]["status"], "succeeded")
        self.assertEqual(timeline[:2], [("stage", CANARY), ("healthy", CANARY)])
        self.assertEqual(overlaps, [frozenset(FOLLOWERS[:2])] * 2)
        self.assertEqual(peak, 2)
        for worker in WORKERS:
            self.assert_payload(worker, "v2", digest)
        self.assertEqual(self.cli("status")["active"], {worker: {"version": "v2", "sha256": digest} for worker in WORKERS})
        print("observed: canary healthy first; two barriers around real staging; peak 2 with 6 followers")


class FailingWorker(LocalWorker):
    def __init__(self, coordinator, rejected):
        super().__init__(coordinator.root)
        self.coordinator = coordinator
        self.rejected = rejected

    def health(self, worker, manifest, digest):
        super().health(worker, manifest, digest)
        if worker == self.rejected:
            state = self.coordinator.status()
            if state["active"][worker]["sha256"] != digest:
                raise AssertionError("failure fixture must observe real activation")
            raise RolloutError("synthetic health rejection")


class FailedCanary(Fixture):
    def test_post_activation_failure_never_touches_followers(self):
        digest = self.make_bundle("v2")
        untouched = {w: self.worker_files(w) for w in FOLLOWERS}
        self.coordinator.adapter = FailingWorker(self.coordinator, CANARY)
        run = self.coordinator.rollout("v2", digest)["run"]
        self.assertEqual(run["status"], "failed")
        self.assertEqual(run["failure"], {"phase": "health", "workers": [CANARY]})
        self.assertEqual(run["workers"], {CANARY: "rolled_back", **dict.fromkeys(FOLLOWERS, "unscheduled")})
        self.assertEqual({w: self.worker_files(w) for w in FOLLOWERS}, untouched)
        self.assert_initial()
        print("observed: canary was activated then restored to v1; 6 follower file inventories unchanged")


class FailedWave(Fixture):
    def test_later_wave_failure_rolls_back_all_touched_workers(self):
        later = FOLLOWERS[4:]
        untouched = {w: self.worker_files(w) for w in later}
        digest = self.make_bundle("v2")
        self.coordinator.adapter = FailingWorker(self.coordinator, FOLLOWERS[2])
        run = self.coordinator.rollout("v2", digest)["run"]
        self.assertEqual(run["status"], "failed")
        self.assertEqual(run["failure"], {"phase": "health", "workers": [FOLLOWERS[2]]})
        self.assertEqual(run["workers"], dict.fromkeys(WORKERS[:5], "rolled_back") | dict.fromkeys(later, "unscheduled"))
        for worker in WORKERS[:5]:
            self.assert_payload(worker, "v2", digest)  # Staged bytes persist, but v1 is active.
        self.assertEqual({w: self.worker_files(w) for w in later}, untouched)
        self.assert_initial()
        print("observed: failed wave 2 restored 5 touched workers; 2 never-scheduled workers unchanged")

    def test_staging_failure_does_not_publish_that_wave(self):
        case = self
        rejected, peer = FOLLOWERS[:2]

        class StageFails(LocalWorker):
            def stage(self, worker, manifest, digest):
                if worker == rejected:
                    raise OSError(errno.ENOSPC, "synthetic disk limit")
                super().stage(worker, manifest, digest)

            def health(self, worker, manifest, digest):
                case.assertEqual(worker, CANARY, "must not activate an incompletely staged wave")
                super().health(worker, manifest, digest)

        self.coordinator.adapter = StageFails(self.root)
        digest = self.make_bundle("v2")
        run = self.coordinator.rollout("v2", digest)["run"]
        self.assertEqual(run["failure"], {"phase": "staging", "workers": [rejected]})
        self.assert_payload(peer, "v2", digest)  # Waited for in-flight worker before rollback.
        self.assert_initial()


class Boundaries(Fixture):
    def test_duplicate_digest_is_a_read_only_no_op(self):
        initial = self.initial[CANARY]["sha256"]
        before = file_snapshot(self.root)
        same = self.release("v1", initial)
        self.assertTrue(same["duplicate"])
        self.assertEqual(same["run"]["status"], "succeeded")
        self.assertEqual(file_snapshot(self.root), before)
        path = self.root / "bundles/v1.json"
        raw = path.read_bytes() + b" "  # Valid manifest, different bytes/digest.
        path.write_bytes(raw)
        self.release("v1", hashlib.sha256(raw).hexdigest(), rc=2, error="different bundle digest")
        self.assert_initial()
        print("observed: duplicate changed no file; competing digest for same version rejected")

    def test_rejects_out_of_scope_roots_links_paths_and_bundle_contents(self):
        digest = self.make_bundle("v2")
        self.release("v2", "0" * 64, rc=2, error="digest mismatch")
        self.release("../v2", digest, rc=2, error="bundle ID")
        self.cli("status", "--sandbox", str(self.home), use_root=False, rc=2, error="sandbox path")
        self.cli("init", "--canary", "../outside", "--follower", "other", use_root=False, rc=2, error="worker IDs")
        self.cli("init", "--canary", "same", "--follower", "same", use_root=False, rc=2, error="worker IDs")
        self.cli("init", "--canary", CANARY, "--follower", "other", "--max-parallel", "9", use_root=False, rc=2, error="1–8")
        path = self.root / "bundles/v2.json"
        raw = path.read_bytes()
        with path.open("wb") as f:
            f.write(raw.replace(b'"managed-config":', b'"auth":'))
        self.release("v2", hashlib.sha256(path.read_bytes()).hexdigest(), rc=2, error="four exact synthetic")
        path.write_bytes(raw.replace(b'"schema":1', b'"schema":1,"schema":1'))
        self.release("v2", hashlib.sha256(path.read_bytes()).hexdigest(), rc=2, error="duplicate JSON field")
        path.write_bytes(b"x" * 4097)
        self.release("v2", digest, rc=2, error="size limit")
        path.unlink()
        # Dangling fixture links must not be read/written or replaced.
        target = self.home / "unused"
        path.symlink_to(target)
        self.release("v2", digest, rc=2)
        self.cli("bundle", "--version", "v2", rc=2)
        self.assertTrue(path.is_symlink())
        self.assertFalse(target.exists())
        path.unlink()
        real = self.home / ".pi/agent/auth.json"
        os.link(real, path)
        self.release("v2", digest, rc=2, error="non-linked file")
        path.unlink()
        path.write_bytes(raw)
        redirected = self.root / "workers" / CANARY / digest
        redirected.symlink_to(self.home / ".pi/agent", target_is_directory=True)
        failed = self.release("v2", digest, rc=1)["run"]
        self.assertEqual(failed["failure"], {"phase": "staging", "workers": [CANARY]})
        self.assertTrue(redirected.is_symlink())
        self.assert_initial()
        self.assertEqual(set(self.cli("status")["runs"]), {"v1", "v2"})
        print("observed: scope, symlink, hardlink, malformed/oversize, unsafe worker and wrong digest inputs rejected")


class Recovery(Fixture):
    def test_cross_process_exclusion_and_recovery_after_abrupt_exit(self):
        v2 = self.make_bundle("v2")
        v3 = self.make_bundle("v3")
        with self.coordinator.writer():
            self.release("v2", v2, rc=2, error="already has a writer")
            self.cli("bundle", "--version", "v4", rc=2, error="already has a writer")
            self.cli("recover", rc=2, error="already has a writer")
            self.assert_initial()  # A writer never blocks the atomic read path.
        fragment = """
import os, sys
sys.path.insert(0, sys.argv[1])
from coordinator_rollout import Coordinator, LocalWorker
class AbruptExit(LocalWorker):
    def health(self, worker, manifest, digest):
        super().health(worker, manifest, digest)
        os._exit(73)
coordinator = Coordinator(sys.argv[2])
coordinator.adapter = AbruptExit(coordinator.root)
coordinator.rollout('v2', sys.argv[3])
"""
        stopped = subprocess.run(
            [sys.executable, "-I", "-B", "-c", fragment, str(LIB), str(self.root), v2],
            env=self.env, check=False, timeout=8,
        )
        self.assertEqual(stopped.returncode, 73)
        state = self.cli("status")
        self.assertEqual(state["pending"], "v2")
        self.assertEqual(state["active"][CANARY]["version"], "v2")
        self.assertEqual(state["runs"]["v2"]["workers"][CANARY], "activated")
        self.release("v3", v3, rc=2, error="run recover")
        restored = self.cli("recover")
        self.assertTrue(restored["recovered"])
        self.assertEqual(restored["run"]["status"], "interrupted")
        self.assertEqual(restored["run"]["workers"], {CANARY: "rolled_back", **dict.fromkeys(FOLLOWERS, "unscheduled")})
        self.assert_initial()
        self.assertEqual(self.cli("recover"), {"recovered": False})
        before = file_snapshot(self.root)
        self.assertTrue(self.release("v2", v2, rc=1)["duplicate"])
        self.assertEqual(file_snapshot(self.root), before)
        self.assertEqual(self.release("v3", v3)["run"]["status"], "succeeded")
        print("observed: second process refused; abrupt exit after activation; explicit recovery to v1; v3 succeeds")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Fast offline lifecycle checks; no real Docker resources are touched."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
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
        with patch.object(d, "inspect", side_effect=m.Refused("failed")):
            with self.assertRaises(m.Refused):
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

        with patch.object(d, "inspect", side_effect=inspect), patch("sys.stdout", new=io.StringIO()):
            with self.assertRaises(m.Refused):
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
        with patch.object(d, "call", side_effect=m.Refused("in use")), patch("sys.stdout", new=io.StringIO()):
            with self.assertRaises(m.Refused):
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
            with self.subTest(results=results), patch.object(m, "git", side_effect=results):
                with self.assertRaises(m.Refused):
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

    def test_shared_policy_bytes(self):
        policy = (ROOT / "docs/task-resources-policy.md").read_text().strip()
        self.assertIn(policy, (ROOT / "pi-defaults/AGENTS.md").read_text())
        self.assertIn("--apply", (ROOT / "docs/task-resources.md").read_text())


if __name__ == "__main__":
    unittest.main()

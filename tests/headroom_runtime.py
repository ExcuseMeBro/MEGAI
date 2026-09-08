#!/usr/bin/env python3
"""Explicit real-Headroom acceptance. Uses prepared public assets; no provider calls.

HEADROOM_TEST_PYTHON=<isolated python> HEADROOM_TEST_ASSETS=<headroom-assets> python3 tests/headroom_runtime.py
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Runtime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.python = os.environ["HEADROOM_TEST_PYTHON"]
        assets = Path(os.environ["HEADROOM_TEST_ASSETS"])
        cls.temporary = tempfile.TemporaryDirectory(prefix="headroom-runtime-test-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.home = Path(cls.temporary.name).resolve()
        cls.megai = cls.home / ".megai"
        shutil.copytree(assets, cls.megai / "headroom-assets", symlinks=True)
        cls.project = cls.home / "project"
        cls.project.mkdir()
        subprocess.run(["git", "init", "-q", str(cls.project)], check=True)
        cls.env = {"HOME": str(cls.home), "MEGAI_HOME": str(cls.megai),
                   "PATH": os.environ["PATH"], "PYTHONDONTWRITEBYTECODE": "1"}
        cls.text = json.dumps([{"id": i, "status": "ok", "message": "unchanged successful operation", "value": 100}
                               for i in range(300)])

    def request(self, action, *, cwd=None, ok=True, **kwargs):
        result = subprocess.run([self.python, "-I", "-B", str(ROOT / "pi-skill/headroom/bridge.py"), "json"],
                                input=json.dumps({"action": action, **kwargs}), text=True,
                                capture_output=True, env=self.env, cwd=cwd or self.project, timeout=40)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        return result

    def test_compress_and_exact_paginated_retrieval_across_process_restart(self):
        result = self.request("compress", text=self.text)
        self.assertTrue(result["compressed"])
        self.assertLess(result["tokens_after"], result["tokens_before"])
        chunks, offset = [], 0
        while offset is not None:
            original = self.request("retrieve", id=result["id"], offset=offset, limit=7000)
            chunks.append(original["text"])
            offset = original["next_offset"]
        self.assertEqual("".join(chunks), self.text)

    def test_semantic_memory_survives_restart_and_is_project_scoped(self):
        text = "Approved deliveries use the slim branch. Main promotion requires separate user approval."
        saved = self.request("save", text=text)
        found = self.request("recall", text="Where should completed changes be delivered?")
        self.assertIn(saved["id"], [memory["id"] for memory in found["memories"]])
        self.assertIn(text, [memory["content"] for memory in found["memories"]])
        other = self.home / "other-project"
        other.mkdir(exist_ok=True)
        self.assertEqual(self.request("recall", cwd=other, text="approved deliveries")["memories"], [])

    def test_worktrees_share_the_repository_memory(self):
        subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                        "commit", "--allow-empty", "-m", "fixture", "-q"], cwd=self.project, check=True)
        worktree = self.home / "worktree"
        subprocess.run(["git", "worktree", "add", "--detach", str(worktree)], cwd=self.project,
                       check=True, capture_output=True)
        text = "The project deployment region is the synthetic fixture west zone."
        saved = self.request("save", text=text)
        result = self.request("recall", cwd=worktree, text="deployment region")
        self.assertIn(saved["id"], [memory["id"] for memory in result["memories"]])

    def test_unknown_original_and_cross_project_retrieval_fail(self):
        result = self.request("compress", text=self.text)
        other = self.home / "retrieval-project"
        other.mkdir(exist_ok=True)
        self.request("retrieve", cwd=other, id=result["id"], ok=False)
        for key in ("../../auth.json", "f" * 24, ""):
            self.request("retrieve", id=key, ok=False)

    def test_shape_uses_upstream_verbosity_without_effort_changes(self):
        text = self.request("steering", level=2)["text"]
        self.assertIn("headroom_output_shaping", text)
        self.assertIn("preamble", text)
        self.assertEqual(self.request("steering", level=0)["text"], "")
        for level in (-1, 5, "2", True):
            self.request("steering", level=level, ok=False)

    def test_offline_doctor_and_private_storage(self):
        result = self.request("doctor")
        self.assertEqual(result["headroom"], "0.37.0")
        self.assertEqual(result["memory"], "local-onnx")
        self.assertFalse(result["effort_routing"])
        for file in (self.megai / "headroom-data").rglob("*.db"):
            self.assertEqual(file.stat().st_mode & 0o077, 0, str(file))
        # The adapter's own network guard, not merely env flags, rejects sockets.
        code = f'''import sys,socket
sys.path.insert(0,{str(ROOT / "pi-skill/headroom")!r})
from bridge import setup
setup({str(self.project)!r})
try: socket.create_connection(("127.0.0.1",9),timeout=1)
except PermissionError: pass
else: raise AssertionError("network guard absent")
'''
        result = subprocess.run([self.python, "-I", "-B", "-c", code], env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_committed_save_with_lost_ack_is_idempotent_after_forced_kill(self):
        text = "Synthetic idempotency decision: keep the delivery branch slim."
        code = f'''import asyncio,sys,time
sys.path.insert(0,{str(ROOT / "pi-skill/headroom")!r})
from bridge import setup,handle
asyncio.run(handle({{"action":"save","text":{text!r}}}, setup({str(self.project)!r})))
print("committed",flush=True)
time.sleep(60)
'''
        process = subprocess.Popen([self.python, "-I", "-B", "-c", code], env=self.env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), "committed")
        finally:
            process.kill()
            process.communicate(timeout=5)
        saved = self.request("save", text=text)
        self.assertTrue(saved["deduplicated"])
        recalled = self.request("recall", text=text)["memories"]
        self.assertEqual(sum(row["id"] == saved["id"] for row in recalled), 1)

    def test_original_quota_survives_fresh_processes_without_evicting_live_data(self):
        project = self.home / "quota-project"
        project.mkdir()
        original = self.request("compress", cwd=project, text=self.text)
        identity = hashlib.sha256(str(project).encode()).hexdigest()[:32]
        storage = self.megai / "headroom-data" / identity
        code = f'''import sys
sys.path.insert(0,{str(ROOT / "pi-skill/headroom")!r})
from pathlib import Path
from persistence import Originals,CCR_ENTRIES
store=Originals(Path({str(storage)!r}))
for number in range(CCR_ENTRIES-1): assert store.put(str(number))
assert store.put("over quota") is None
'''
        subprocess.run([self.python, "-I", "-B", "-c", code], env=self.env, check=True)
        rejected = self.request("compress", cwd=project, text=self.text + " ")
        self.assertFalse(rejected["compressed"])
        self.assertEqual(rejected["text"], self.text + " ")
        retrieved = self.request("retrieve", cwd=project, id=original["id"])
        self.assertEqual(retrieved["text"], self.text[:8000])

    def test_runtime_ignores_credential_pythonpath_and_storage_override_canaries(self):
        injected = self.home / "injected-pythonpath"
        injected.mkdir()
        marker = self.home / "injected-import-ran"
        (injected / "sitecustomize.py").write_text(f"open({str(marker)!r},'w').write('bad')")
        redirected = self.home / "redirected.db"
        env = dict(self.env, OPENAI_API_KEY="synthetic-only", PYTHONPATH=str(injected),
                   HEADROOM_CCR_SQLITE_PATH=str(redirected))
        code = f'''import os,sys
sys.path.insert(0,{str(ROOT / "pi-skill/headroom")!r})
from bridge import setup
setup({str(self.project)!r})
assert "OPENAI_API_KEY" not in os.environ
assert "PYTHONPATH" not in os.environ
assert "HEADROOM_CCR_SQLITE_PATH" not in os.environ
'''
        subprocess.run([self.python, "-I", "-B", "-c", code], env=env, check=True)
        self.assertFalse(marker.exists())
        self.assertFalse(redirected.exists())

    def test_model_checksum_failure_precedes_inference(self):
        model = next((self.megai / "headroom-assets").rglob("model.onnx"))
        with model.open("r+b") as stream:
            original = stream.read(1)
            stream.seek(0)
            stream.write(bytes([original[0] ^ 1]))
        try:
            result = self.request("doctor", ok=False)
            self.assertIn("ValueError", result.stderr)
        finally:
            with model.open("r+b") as stream:
                stream.write(original)

    def test_symlinked_storage_is_refused_without_touching_target(self):
        other = self.home / "symlink-project"
        other.mkdir(exist_ok=True)
        identity = hashlib.sha256(str(other).encode()).hexdigest()[:32]
        path = self.megai / "headroom-data" / identity
        outside = self.home / "outside"
        outside.mkdir(exist_ok=True)
        path.symlink_to(outside)
        self.request("doctor", cwd=other, ok=False)
        self.assertEqual(list(outside.iterdir()), [])
        path.unlink()


if __name__ == "__main__":
    unittest.main()

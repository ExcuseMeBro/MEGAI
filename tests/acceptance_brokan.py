"""Brokan-native approval and frozen legacy compatibility at the real CLI seam."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

GATE = Path(__file__).resolve().parents[1] / "lib/acceptance_gate.py"


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "repo"
        self.root.mkdir()
        for command in (("init", "-q"), ("config", "user.email", "test@example.invalid"),
                        ("config", "user.name", "Test")):
            subprocess.run(["git", "-C", str(self.root), *command], check=True, capture_output=True)
        (self.root / "source").write_text("source")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "initial"],
                       check=True, capture_output=True)
        self.task = {"id": 7, "project": "megai", "status": "doing", "description": ""}
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != "/api/tasks/7":
                    self.send_error(404)
                    return
                body = json.dumps({"task": owner.task}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.addCleanup(self.server.server_close)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.addCleanup(self.worker.join, 5)
        self.addCleanup(self.server.shutdown)
        self.env = dict(os.environ, MEGAI_BROKAN_TEST_PORT=str(self.server.server_port))
        self.command = [sys.executable, "-c", "print('accepted')"]
        self.contract = {"schema": 4, "task_type": "change", "brokan": {"task_id": "megai#7"},
                         "implementer_session_id": "test-session", "runtime": {
                             "required": False, "authorized": False, "environment": "none",
                             "targets": [], "reason": "disposable local CLI test"},
                         "criteria": [{"id": "test", "kind": "test", "expected": "prints accepted",
                                       "command": self.command}]}
        self.cp = self.base / "contract.json"
        self.save_contract()

    def save_contract(self):
        self.cp.write_text(json.dumps(self.contract))
        self.digest = hashlib.sha256(self.cp.read_bytes()).hexdigest()
        self.task["description"] = f"Frozen acceptance SHA256: {self.digest}\n"

    def cli(self, *args):
        result = subprocess.run([sys.executable, "-B", str(GATE), *map(str, args)],
                                env=self.env, capture_output=True, text=True, timeout=20)
        self.assertNotIn("Traceback", result.stderr)
        return result

    def test_collect_and_check_require_matching_live_approval(self):
        out = self.base / "collected"
        collect = self.cli("collect", "--root", self.root, "--contract", self.cp,
                           "--contract-sha256", self.digest, "--out", out)
        self.assertEqual(collect.returncode, 2, collect.stdout)
        evidence = json.loads((out / "evidence.json").read_text())
        self.assertNotIn("review", evidence)
        evidence["checks"][0].update(status="PASS", observation="CLI printed accepted")
        (out / "evidence.json").write_text(json.dumps(evidence))
        command = ("check", "--root", self.root, "--contract", self.cp,
                   "--contract-sha256", self.digest, "--evidence", out / "evidence.json")
        self.assertEqual(self.cli(*command).returncode, 0)
        for mutation in ({"description": "revoked"}, {"status": "todo"},
                         {"project": "other"}, {"id": 8}):
            with self.subTest(mutation=mutation):
                old = dict(self.task)
                self.task.update(mutation)
                self.assertEqual(self.cli(*command).returncode, 2)
                self.task = old
        (self.root / "source").write_text("drift")
        self.assertEqual(self.cli(*command).returncode, 2)

    def test_invalid_identity_and_legacy_plane_mixture_block(self):
        for identity in ("MEGAI#7", "megai#0", "megai#07", "megai#7/extra"):
            with self.subTest(identity=identity):
                self.contract["brokan"]["task_id"] = identity
                self.save_contract()
                result = self.cli("collect", "--root", self.root, "--contract", self.cp,
                                  "--contract-sha256", self.digest,
                                  "--out", self.base / ("out-" + str(abs(hash(identity)))))
                self.assertEqual(result.returncode, 2, result.stdout)
        self.contract["brokan"]["task_id"] = "megai#7"
        self.contract["plane"] = {"project_id": "x", "work_item_id": "x"}
        self.save_contract()
        result = self.cli("collect", "--root", self.root, "--contract", self.cp,
                          "--contract-sha256", self.digest, "--out", self.base / "mixed")
        self.assertEqual(result.returncode, 2, result.stdout)


if __name__ == "__main__":
    unittest.main()

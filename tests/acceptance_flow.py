#!/usr/bin/env python3
"""Public CLI tests using real disposable Git repositories; review data is synthetic."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

GATE = Path(__file__).resolve().parents[1] / "lib/acceptance_gate.py"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value))


class Flow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "repo"
        self.root.mkdir()
        for args in (("init", "-q"), ("config", "user.email", "test@example.invalid"),
                     ("config", "user.name", "Test")):
            self.git(*args)
        (self.root / "source.txt").write_text("broken")
        (self.root / "regression.py").write_text(
            "from pathlib import Path\n"
            "assert Path('source.txt').read_text() == 'fixed', 'BUG-42 persists'\n"
        )
        self.git("add", ".")
        self.git("commit", "-qm", "buggy baseline")
        self.command = [sys.executable, "-B", "regression.py"]

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)

    def cli(self, *args):
        result = subprocess.run([sys.executable, "-B", str(GATE), *map(str, args)],
                                capture_output=True, text=True, timeout=20)
        self.assertNotIn("Traceback", result.stderr, result.stderr)
        return result

    def run_check(self, out, *flags):
        return self.cli("run", "--root", self.root, "--out", self.base / out,
                        *flags, "--", *self.command)

    def fixture(self):
        red = self.run_check("red", "--test-file", "regression.py")
        self.assertEqual(red.returncode, 1, red.stdout + red.stderr)
        receipt = self.base / "red/receipt.json"
        contract = {
            "schema": 2, "task_type": "bugfix",
            "plane": {"project_id": "59005e36-ecd4-46ed-bb42-f779858b20ce",
                      "work_item_id": "91a96143-9287-404b-a8e1-4f956498ec8a"},
            "implementer_session_id": "synthetic-implementer",
            "runtime": {"required": False, "authorized": False, "environment": "none",
                        "targets": [], "reason": "disposable regression fixture"},
            "criteria": [{"id": "fix", "kind": "test", "expected": "BUG-42 corrected",
                          "command": self.command, "regression": {
                              "receipt": {"path": "red/receipt.json", "sha256": digest(receipt)},
                              "exit_code": 1, "failure_contains": "AssertionError: BUG-42 persists"}}],
        }
        save(self.base / "contract.json", contract)
        (self.root / "source.txt").write_text("fixed")
        green = self.run_check("green")
        self.assertEqual(green.returncode, 0, green.stdout + green.stderr)
        snap = json.loads((self.base / "green/receipt.json").read_text())["snapshot_after"]
        (self.base / "review.txt").write_text("synthetic review only")
        evidence = {
            "schema": 1, "contract_sha256": digest(self.base / "contract.json"),
            "snapshot": snap, "checks": [{"id": "fix", "status": "PASS",
                "observation": "Regression assertion passes", "receipt": "green/receipt.json", "artifacts": []}],
            "review": {"session_id": "synthetic-reviewer", "harness": "pi",
                       "model": "openai-codex/gpt-5.6-sol", "thinking": "high", "verdict": "PASS",
                       "snapshot": snap, "contract_sha256": digest(self.base / "contract.json"),
                       "criteria": ["fix"], "artifact": {"path": "review.txt", "sha256": digest(self.base / "review.txt")}},
        }
        save(self.base / "evidence.json", evidence)
        return contract, evidence

    def check(self, expected):
        result = self.cli("check", "--root", self.root, "--contract", self.base / "contract.json",
                          "--contract-sha256", digest(self.base / "contract.json"),
                          "--evidence", self.base / "evidence.json")
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def amend(self, contract, evidence):
        save(self.base / "contract.json", contract)
        evidence["contract_sha256"] = digest(self.base / "contract.json")
        evidence["review"]["contract_sha256"] = evidence["contract_sha256"]
        save(self.base / "evidence.json", evidence)

    def test_bugfix_requires_real_red_then_green_with_same_test(self):
        self.fixture()
        self.check(0)

    def test_bugfix_without_regression_is_blocked(self):
        contract, evidence = self.fixture()
        del contract["criteria"][0]["regression"]
        self.amend(contract, evidence)
        self.assertIn("Bugfix requires", self.check(2).stdout)

    def test_wrong_expected_failure_is_blocked(self):
        contract, evidence = self.fixture()
        regression = contract["criteria"][0]["regression"]
        for key, wrong, original in (("exit_code", 2, 1),
                                     ("failure_contains", "unrelated failure", "AssertionError: BUG-42 persists")):
            with self.subTest(key=key):
                regression[key] = wrong
                self.amend(contract, evidence)
                self.check(2)
                regression[key] = original

    def test_tampered_baseline_receipt_and_log_are_blocked(self):
        self.fixture()
        for name in ("red/receipt.json", "red/output.txt"):
            path = self.base / name
            original = path.read_bytes()
            path.write_bytes(original + b" ")
            self.check(2)
            path.write_bytes(original)
        self.check(0)

    def test_missing_baseline_test_capture_and_unstable_snapshot_are_blocked(self):
        contract, evidence = self.fixture()
        path = self.base / "red/receipt.json"
        receipt = json.loads(path.read_text())
        for key, value in (("test_files", []), ("snapshot_after", "0" * 64),
                           ("exit_code", 0), ("argv", ["different-command"]),
                           ("cwd", str(self.base))):
            with self.subTest(key=key):
                changed = {**receipt, key: value}
                save(path, changed)
                contract["criteria"][0]["regression"]["receipt"]["sha256"] = digest(path)
                self.amend(contract, evidence)
                self.check(2)

    def test_changed_regression_test_cannot_be_laundered_by_new_green_snapshot(self):
        contract, evidence = self.fixture()
        (self.root / "regression.py").write_text("# weakened test\n")
        result = self.run_check("new-green")
        self.assertEqual(result.returncode, 0, result.stdout)
        receipt = json.loads((self.base / "new-green/receipt.json").read_text())
        evidence["snapshot"] = receipt["snapshot_after"]
        evidence["review"]["snapshot"] = evidence["snapshot"]
        evidence["checks"][0]["receipt"] = "new-green/receipt.json"
        self.amend(contract, evidence)
        self.assertIn("Artifact hash mismatch", self.check(2).stdout)

    def collect(self, name="collected", approved=None):
        return self.cli("collect", "--root", self.root,
                        "--contract", self.base / "contract.json",
                        "--contract-sha256", approved or digest(self.base / "contract.json"),
                        "--out", self.base / name)

    def test_collect_generates_private_receipts_but_never_invents_acceptance(self):
        _, _ = self.fixture()
        result = self.collect()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "BLOCKED")
        output = self.base / "collected"
        draft = json.loads((output / "evidence.json").read_text())
        self.assertEqual(draft["checks"][0]["status"], "PASS")
        self.assertEqual(draft["checks"][0]["observation"], "")
        self.assertEqual(draft["review"]["verdict"], "BLOCKED")
        self.assertEqual(draft["review"]["session_id"], "")
        self.assertEqual(output.stat().st_mode & 0o777, 0o700)
        self.assertEqual((output / "evidence.json").stat().st_mode & 0o777, 0o600)
        receipt = output / draft["checks"][0]["receipt"]
        self.assertEqual(json.loads(receipt.read_text())["argv"], self.command)
        self.assertEqual(self.collect().returncode, 2)
        result = self.cli("check", "--root", self.root, "--contract", self.base / "contract.json",
                          "--contract-sha256", digest(self.base / "contract.json"),
                          "--evidence", output / "evidence.json")
        self.assertEqual(result.returncode, 2, result.stdout)

    def test_collect_rejects_unapproved_contract_and_unsafe_output_without_running(self):
        self.fixture()
        self.assertEqual(self.collect(approved="0" * 64).returncode, 2)
        self.assertFalse((self.base / "collected").exists())
        result = self.collect(name="repo/inside")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertFalse((self.root / "inside").exists())

    def test_collect_preserves_failure_and_does_not_run_later_commands(self):
        contract, _ = self.fixture()
        contract["task_type"] = "change"
        contract["criteria"] = [
            {"id": "failure", "kind": "test", "expected": "failure preserved",
             "command": [sys.executable, "-c", "import sys; print('raw failure'); sys.exit(7)"]},
            {"id": "later", "kind": "test", "expected": "must not run",
             "command": [sys.executable, "-c", "raise RuntimeError('must not run')"]},
        ]
        save(self.base / "contract.json", contract)
        result = self.collect()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual((self.base / "collected/000/output.txt").read_text(), "raw failure\n")
        receipt = json.loads((self.base / "collected/000/receipt.json").read_text())
        self.assertEqual(receipt["exit_code"], 7)
        draft = json.loads((self.base / "collected/evidence.json").read_text())
        self.assertEqual([item["status"] for item in draft["checks"]], ["FAIL", "BLOCKED"])
        self.assertFalse((self.base / "collected/001").exists())

    def test_collect_stops_on_source_mutation_and_keeps_receipt(self):
        contract, _ = self.fixture()
        contract["task_type"] = "change"
        contract["criteria"] = [
            {"id": "mutation", "kind": "test", "expected": "source mutation blocks",
             "command": [sys.executable, "-c", "open('source.txt', 'w').write('changed')"]},
            {"id": "later", "kind": "test", "expected": "not executed",
             "command": [sys.executable, "-c", "print('later')"]},
        ]
        save(self.base / "contract.json", contract)
        result = self.collect()
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertTrue((self.base / "collected/000/receipt.json").is_file())
        self.assertTrue((self.base / "collected/evidence.json").is_file())
        self.assertFalse((self.base / "collected/001").exists())

    def test_test_file_scope_rejects_escape_and_symlink_before_execution(self):
        (self.root / ".gitignore").write_text("ignored.py\n")
        (self.root / "ignored.py").write_text("pass\n")
        for name in ("../outside", "/etc/hosts", ".git/config", "ignored.py", "link"):
            if name == "link":
                (self.root / "link").symlink_to(self.root / "regression.py")
            result = self.run_check("unsafe", "--test-file", name)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertFalse((self.base / "unsafe").exists())


if __name__ == "__main__":
    unittest.main()

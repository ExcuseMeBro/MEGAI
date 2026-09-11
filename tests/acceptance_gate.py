#!/usr/bin/env python3
"""Real Git/command tests; review metadata here is synthetic test data only."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

GATE = Path(__file__).resolve().parents[1] / "lib/acceptance_gate.py"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value))


def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


class AcceptanceGateTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "repository"
        self.root.mkdir()
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "user.name", "Test")
        (self.root / "source.txt").write_text("source")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "initial")

    def invoke(self, *args):
        result = subprocess.run(
            [sys.executable, "-B", str(GATE), *map(str, args)],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertNotIn("Traceback", result.stderr, result.stderr)
        return result

    def snapshot(self):
        result = self.invoke("snapshot", "--root", self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)["snapshot"]

    def execute(self, output, command):
        return self.invoke("run", "--root", self.root, "--out", output, "--", *command)

    def fixture(self, child_exit=0):
        directory = Path(tempfile.mkdtemp(dir=self.base))
        command = [
            sys.executable,
            "-c",
            f"import sys; print('observed output'); sys.exit({child_exit})",
        ]
        contract = {
            "schema": 1,
            "plane": {
                "project_id": "59005e36-ecd4-46ed-bb42-f779858b20ce",
                "work_item_id": "91a96143-9287-404b-a8e1-4f956498ec8a",
            },
            "implementer_session_id": "implementer",
            "runtime": {
                "required": False,
                "authorized": False,
                "environment": "none",
                "targets": [],
                "reason": "test fixture does not need a service",
            },
            "criteria": [
                {
                    "id": "local",
                    "kind": "test",
                    "expected": "command prints observed output",
                    "command": command,
                }
            ],
        }
        cp = directory / "contract.json"
        save(cp, contract)
        result = self.execute(directory / "output", command)
        self.assertEqual(result.returncode, 0 if child_exit == 0 else 1, result.stdout)
        review = directory / "review.txt"
        review.write_text("synthetic independent review for schema tests")
        snap = self.snapshot()
        evidence = {
            "schema": 1,
            "contract_sha256": sha256(cp),
            "snapshot": snap,
            "checks": [
                {
                    "id": "local",
                    "status": "PASS",
                    "observation": "observed output appeared",
                    "receipt": "output/receipt.json",
                    "artifacts": [],
                }
            ],
            "review": {
                "session_id": "reviewer",
                "harness": "pi",
                "model": "openai-codex/gpt-5.6-sol",
                "thinking": "high",
                "verdict": "PASS",
                "snapshot": snap,
                "contract_sha256": sha256(cp),
                "criteria": ["local"],
                "artifact": {"path": "review.txt", "sha256": sha256(review)},
            },
        }
        save(directory / "evidence.json", evidence)
        return directory, contract, evidence

    def check(self, directory, expected=0, reason=None):
        cp = directory / "contract.json"
        result = self.invoke(
            "check",
            "--root",
            self.root,
            "--contract",
            cp,
            "--contract-sha256",
            sha256(cp),
            "--evidence",
            directory / "evidence.json",
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["status"], {0: "PASS", 1: "FAIL", 2: "BLOCKED"}[expected]
        )
        if reason:
            self.assertIn(reason, " ".join(payload["reasons"]))

    def amend_contract(self, directory, contract, evidence):
        save(directory / "contract.json", contract)
        digest = sha256(directory / "contract.json")
        evidence["contract_sha256"] = digest
        evidence["review"]["contract_sha256"] = digest
        save(directory / "evidence.json", evidence)

    def test_pass_private_files_and_raw_output(self):
        directory, _, _ = self.fixture()
        self.check(directory)
        output = directory / "output"
        self.assertEqual(output.stat().st_mode & 0o777, 0o700)
        for name in ("receipt.json", "output.txt"):
            self.assertEqual((output / name).stat().st_mode & 0o777, 0o600)
        self.assertEqual((output / "output.txt").read_text(), "observed output\n")

    def test_nonzero_child_cannot_claim_pass(self):
        directory, _, _ = self.fixture(child_exit=4)
        self.check(directory, 1)
        receipt = json.loads((directory / "output/receipt.json").read_text())
        self.assertEqual(receipt["exit_code"], 4)

    def test_declared_fail_and_blocked(self):
        for status, exit_code in (("FAIL", 1), ("BLOCKED", 2)):
            with self.subTest(status=status):
                directory, _, evidence = self.fixture()
                evidence["checks"][0]["status"] = status
                save(directory / "evidence.json", evidence)
                self.check(directory, exit_code)

    def test_missing_duplicate_unknown_criteria(self):
        for variant in ("missing", "duplicate", "unknown"):
            with self.subTest(variant=variant):
                directory, _, evidence = self.fixture()
                if variant == "missing":
                    evidence["checks"] = []
                elif variant == "duplicate":
                    evidence["checks"] *= 2
                else:
                    evidence["checks"][0]["id"] = "unknown"
                save(directory / "evidence.json", evidence)
                self.check(directory, 2)

    def test_missing_and_tampered_log_or_review(self):
        for relative, delete in (
            ("output/output.txt", True),
            ("output/output.txt", False),
            ("review.txt", False),
        ):
            with self.subTest(relative=relative, delete=delete):
                directory, _, _ = self.fixture()
                path = directory / relative
                path.unlink() if delete else path.write_text("tampered")
                self.check(directory, 2)

    def test_stale_tracked_source(self):
        directory, _, _ = self.fixture()
        (self.root / "source.txt").write_text("changed")
        self.check(directory, 2, "snapshot")

    def test_stale_untracked_source(self):
        directory, _, _ = self.fixture()
        (self.root / "new.py").write_text("changed")
        self.check(directory, 2, "snapshot")

    def test_index_only_content_invalidates_evidence(self):
        directory, _, _ = self.fixture()
        source = self.root / "source.txt"
        source.write_text("staged but not the tested worktree")
        git(self.root, "add", "source.txt")
        source.write_text("source")
        self.check(directory, 2, "snapshot")

    def test_index_only_mode_changes_snapshot(self):
        before = self.snapshot()
        git(self.root, "update-index", "--chmod=+x", "source.txt")
        self.assertNotEqual(self.snapshot(), before)

    def test_deleted_source_changes_snapshot(self):
        before = self.snapshot()
        (self.root / "source.txt").unlink()
        self.assertNotEqual(self.snapshot(), before)

    def test_changed_contract_cannot_reuse_evidence(self):
        directory, contract, _ = self.fixture()
        contract["criteria"][0]["expected"] = "weakened requirement"
        save(directory / "contract.json", contract)
        self.check(directory, 2)

    def test_independent_review_identity_and_verdict(self):
        for key, value in (
            ("session_id", "implementer"),
            ("harness", "codex"),
            ("model", "unknown"),
            ("thinking", "low"),
            ("verdict", "UNKNOWN"),
            ("criteria", []),
        ):
            with self.subTest(key=key):
                directory, _, evidence = self.fixture()
                evidence["review"][key] = value
                save(directory / "evidence.json", evidence)
                self.check(directory, 2)

    def test_review_fail_and_blocked(self):
        for verdict, expected in (("FAIL", 1), ("BLOCKED", 2)):
            directory, _, evidence = self.fixture()
            evidence["review"]["verdict"] = verdict
            save(directory / "evidence.json", evidence)
            self.check(directory, expected)

    def test_malformed_json_and_schema(self):
        for value in ('{"schema":1,"schema":1}', '{"schema":NaN}', "[]", "{"):
            directory, _, _ = self.fixture()
            (directory / "evidence.json").write_text(value)
            self.check(directory, 2)
        for schema in (True, 1.0, 2):
            directory, _, evidence = self.fixture()
            evidence["schema"] = schema
            save(directory / "evidence.json", evidence)
            self.check(directory, 2)

    def test_receipt_types_and_scope(self):
        for key, value in (
            ("schema", True),
            ("exit_code", False),
            ("duration_seconds", float("nan")),
            ("duration_seconds", -1),
            ("cwd", "wrong"),
            ("argv", ["wrong"]),
        ):
            with self.subTest(key=key, value=value):
                directory, _, _ = self.fixture()
                path = directory / "output/receipt.json"
                receipt = json.loads(path.read_text())
                receipt[key] = value
                save(path, receipt)
                self.check(directory, 2)

    def test_runtime_requires_authorization_and_exact_target(self):
        for authorized, target, expected in (
            (True, "local-cli:test", 0),
            (False, "local-cli:test", 2),
            (True, "unapproved", 2),
        ):
            directory, contract, evidence = self.fixture()
            contract["runtime"] = {
                "required": True,
                "authorized": authorized,
                "environment": "local",
                "targets": ["local-cli:test"],
                "reason": "real local command",
            }
            contract["criteria"][0].update(kind="runtime", target=target)
            self.amend_contract(directory, contract, evidence)
            self.check(directory, expected)

    def test_artifact_traversal_and_intermediate_symlink(self):
        for path in ("../outside.json", "linked/receipt.json"):
            directory, _, evidence = self.fixture()
            (directory / "linked").symlink_to(
                directory / "output", target_is_directory=True
            )
            evidence["checks"][0]["receipt"] = path
            save(directory / "evidence.json", evidence)
            self.check(directory, 2)

    def test_external_evidence_ancestor_symlink(self):
        directory, _, _ = self.fixture()
        alias = self.base / "alias"
        alias.symlink_to(directory, target_is_directory=True)
        self.check(alias, 2, "Symlink")

    def test_output_reuse_inside_repo_and_symlink(self):
        (self.base / "existing").mkdir()
        (self.base / "linked").symlink_to(
            self.base / "existing", target_is_directory=True
        )
        for output in (
            self.base / "existing",
            self.root / "inside",
            self.base / "linked/new",
            self.base / "linked",
        ):
            result = self.execute(output, [sys.executable, "-c", "pass"])
            self.assertEqual(result.returncode, 2, result.stdout)
        self.assertFalse((self.base / "existing/new").exists())

    def test_source_symlink_ancestor(self):
        folder = self.root / "folder"
        folder.mkdir()
        (folder / "child").write_text("tracked")
        git(self.root, "add", ".")
        (folder / "child").unlink()
        folder.rmdir()
        folder.symlink_to(self.base, target_is_directory=True)
        result = self.invoke("snapshot", "--root", self.root)
        self.assertEqual(result.returncode, 2, result.stdout)

    def test_subdirectory_root_and_fifo_rejected(self):
        child = self.root / "child"
        child.mkdir()
        result = self.invoke("snapshot", "--root", child)
        self.assertEqual(result.returncode, 2, result.stdout)
        if hasattr(os, "mkfifo"):
            source = self.root / "source.txt"
            source.unlink()
            os.mkfifo(source)
            result = self.invoke("snapshot", "--root", self.root)
            self.assertEqual(result.returncode, 2, result.stdout)

    def test_mutation_and_missing_executable_preserve_receipts(self):
        for name, command in (
            ("mutation", [sys.executable, "-c", "open('new', 'w').write('x')"]),
            ("missing", ["acceptance-no-such-executable"]),
        ):
            output = self.base / name
            result = self.execute(output, command)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertTrue((output / "receipt.json").is_file())
            self.assertTrue((output / "output.txt").is_file())


if __name__ == "__main__":
    unittest.main()

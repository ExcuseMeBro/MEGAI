#!/usr/bin/env python3
"""Deterministic regressions for queue lease accounting and history lookup cost."""

import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("queue_audit_target", ROOT / "lib/integration_queue.py")
queue_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue_module)


class QueueAudit(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="queue-audit-")
        self.addCleanup(temporary.cleanup)
        self.queue = queue_module.Queue(Path(temporary.name) / "private")
        self.addCleanup(self.queue.db.close)
        self.request = {
            "schema": 1, "id": "target", "project_id": "prj_fixture", "root": "/fixture",
            "plane": {"project_id": "00000000-0000-4000-8000-000000000001",
                      "work_item_id": "00000000-0000-4000-8000-000000000002"},
            "repositories": [{"path": "/fixture/repo", "common_dir": "/fixture/repo/.git",
                              "branch": "refs/heads/dev", "checkout_branch": "refs/heads/dev",
                              "expected_head": "a" * 40, "checkout_head": "a" * 40,
                              "candidate_head": "b" * 40}],
            "resources": [], "depends_on": [],
        }
        queue_module.validate_request(self.request)
        self.insert("target", "queued")

    def insert(self, key, state):
        request = dict(self.request, id=key)
        self.queue.db.execute("INSERT INTO requests(id,request,state,updated) VALUES (?,?,?,?)",
                              (key, json.dumps(request), state, 100.0))

    def test_claim_lease_starts_after_slow_preflight(self):
        clock = [100.0]

        def slow_preflight(request, key):
            self.assertEqual(request, self.request)
            self.assertEqual(key, "expected_head")
            clock[0] += 10.0  # Several valid Git/project checks may exceed a short lease.

        args = argparse.Namespace(action="claim", id="target", owner="fixture", lease_seconds=1)
        with patch.object(queue_module.time, "time", side_effect=lambda: clock[0]), \
                patch.object(queue_module, "vector_matches", side_effect=slow_preflight):
            grant = self.queue.mutate(args)
            self.assertGreater(grant["expires"], clock[0],
                               "claim returned an already-expired grant after successful preflight")
            self.assertEqual(grant["expires"], 111.0)
            self.assertFalse(grant["needs_reconcile"])
            heartbeat = argparse.Namespace(action="heartbeat", id="target", owner="fixture",
                                           token=grant["token"], lease_seconds=1)
            self.assertEqual(self.queue.mutate(heartbeat)["state"], "active")

    def test_terminal_lookup_does_not_decode_entire_history(self):
        self.queue.db.execute("UPDATE requests SET state='completed' WHERE id='target'")
        for number in range(200):
            self.insert(f"history-{number}", "completed")
        with patch.object(queue_module.json, "loads", wraps=json.loads) as decode:
            result = self.queue.public(self.queue.row("target"))
            self.assertEqual(result["state"], "completed")
            self.assertNotIn("token", result)
            self.assertEqual(decode.call_count, 1,
                             "single terminal lookup decoded unrelated queue history")
        with self.assertRaisesRegex(queue_module.Blocked, "Unknown queue request"):
            self.queue.row("missing")


if __name__ == "__main__":
    unittest.main(verbosity=2)

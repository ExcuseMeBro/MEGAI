"""Behavioral tests at the runner's Plane/Pi seam; no live writes or model calls."""

import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().parents[1] / "pi-defaults"
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location("orchestrator", SOURCE / "orchestrator.py")
orch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(orch)

P = "a" * 8 + "-aaaa-aaaa-aaaa-" + "a" * 12
T = "b" * 8 + "-bbbb-bbbb-bbbb-" + "b" * 12
OP = "c" * 8 + "-cccc-cccc-cccc-" + "c" * 12
Q = "d" * 8 + "-dddd-dddd-dddd-" + "d" * 12


class Fake:
    def __init__(self, home):
        self.home = home
        self.project = {"id": P, "name": "MEGAI"}
        self.task = {"id": T, "project": P, "name": "Implement task", "sequence_id": 4,
                     "state": "todo", "description_stripped": "Acceptance: tests"}
        self.states = [{"id": "todo", "name": "Todo", "group": "unstarted"},
                       {"id": "doing", "name": "In Progress", "group": "started"},
                       {"id": "review", "name": "In Review", "group": "started"}]
        self.comments = []
        self.writes = []
        self.runs = []
        self.output = '{"orchestrator":"needs_you","question":"Which format?"}'

    def pages(self, name, **kwargs):
        if name == "project":
            return [self.project.copy()]
        if name == "workitem":
            return [self.task.copy()]
        if name == "state":
            return [s.copy() for s in self.states]
        if name == "workitem_comment":
            return [c.copy() for c in self.comments]
        raise AssertionError(name)

    def call(self, name, args):
        if args["action"] == "retrieve":
            return self.task.copy()
        self.writes.append((name, args.copy()))
        if name == "state":
            self.states.append({"id": "needs", "name": "Needs You", "group": "started"})
            return self.states[-1].copy()
        if name == "workitem":
            self.task["state"] = args["state"]
            return self.task.copy()
        if name == "workitem_comment":
            item = {"id": Q, "created_at": "2026-10-25T10:00:00+05:00",
                    "created_by": OP, "comment_stripped": "Which format?",
                    "external_source": orch.SOURCE}
            self.comments.append(item)
            return item.copy()
        raise AssertionError(name)

    def worker(self, cwd, directory, session_id, message):
        self.runs.append((cwd, session_id, message))
        return self.output

    def runner(self):
        cfg = {"operator_id": OP, "private_dir": str(self.home),
               "projects": {P: str(SOURCE.parent)}}
        return orch.Runner(cfg, self.call, self.pages, self.worker)


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.chmod(self.tmp.name, 0o700)
        self.fake = Fake(Path(self.tmp.name))
        self.context = patch.object(orch, "context", return_value={
            "planeProject": "MEGAI", "repository": str(SOURCE.parent),
            "repositories": [str(SOURCE.parent)]})
        self.check = patch.object(orch.subprocess, "run")
        self.context.start()
        self.check.start()
        self.addCleanup(self.context.stop)
        self.addCleanup(self.check.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_rpc_protocol_reuses_exact_session_and_waits_for_settlement(self):
        stream = (b'{"id":"prompt","type":"response","success":true,'
                  b'"data":{"disposition":"started"}}\n'
                  b'{"type":"agent_settled"}\n'
                  b'{"id":"get_last_assistant_text","type":"response",'
                  b'"success":true,"data":{"text":"ok"}}\n')
        process = Mock(stdin=Mock(), stdout=io.BytesIO(stream), returncode=0)
        with patch.object(orch.subprocess, "Popen", return_value=process) as spawn:
            text = orch.rpc_run(str(SOURCE.parent), self.fake.home / "sessions",
                                "task-reusable", "message")
        self.assertEqual(text, "ok")
        self.assertEqual(spawn.call_args.args[0][-2:], ["--session-id", "task-reusable"])
        self.assertEqual(process.stdin.write.call_count, 2)
        self.assertIn(b'"type": "prompt"', process.stdin.write.call_args_list[0].args[0])
        self.assertIn(b'"type": "get_last_assistant_text"',
                      process.stdin.write.call_args_list[1].args[0])
        process.wait.assert_called_once()

    def test_question_moves_only_this_task_and_continue_after_restart(self):
        runner = self.fake.runner()
        result = runner.step()
        self.assertEqual(result["waiting"], f"{P}/{T}")
        self.assertEqual(self.fake.task["state"], "needs")
        self.assertEqual([name for name, _ in self.fake.writes],
                         ["workitem", "state", "workitem_comment", "workitem"])
        session_id = self.fake.runs[0][1]
        self.assertEqual(runner.step()["blocked"], [(f"{P}/{T}", "Awaiting !answer comment")])
        self.assertEqual(len(self.fake.runs), 1)
        self.fake.comments.append({"id": "answer", "created_at": "2026-10-25T10:01:00+05:00",
                                   "created_by": OP, "comment_stripped": "!answer JSON please",
                                   "external_source": None})
        self.fake.output = '{"orchestrator":"in_review"}'
        self.fake.worker = lambda cwd, directory, sid, message: (
            self.fake.runs.append((cwd, sid, message)),
            self.fake.task.__setitem__("state", "review"), self.fake.output)[-1]
        resumed = self.fake.runner().step()
        self.assertEqual(resumed["reviewed"], f"{P}/{T}")
        self.assertEqual(len(self.fake.runs), 2)
        self.assertEqual(self.fake.runs[-1][1], session_id)
        self.assertIn("JSON please", self.fake.runs[-1][2])

    def test_question_does_not_stop_the_next_independent_todo(self):
        other = "e" * 8 + "-eeee-eeee-eeee-" + "e" * 12
        first = self.fake.task.copy()
        second = {**first, "id": other, "sequence_id": 5}
        original_pages = self.fake.pages
        original_call = self.fake.call

        def pages(name, **kwargs):
            return [first.copy(), second.copy()] if name == "workitem" else original_pages(name, **kwargs)

        def call(name, args):
            if name == "workitem" and args["action"] == "retrieve":
                return (first if args["workitem_id"] == T else second).copy()
            if name == "workitem" and args["action"] == "update":
                (first if args["workitem_id"] == T else second)["state"] = args["state"]
                self.fake.writes.append((name, args.copy()))
                return (first if args["workitem_id"] == T else second).copy()
            return original_call(name, args)

        runner = self.fake.runner()
        runner.list_pages, runner.api = pages, call
        self.assertEqual(runner.step()["waiting"], f"{P}/{T}")
        self.assertEqual(runner.step()["waiting"], f"{P}/{other}")
        self.assertEqual(len(self.fake.runs), 2)

    def test_foreign_and_ordinary_comments_never_resume(self):
        self.fake.runner().step()
        self.fake.comments += [
            {"id": "foreign", "created_at": "2026-10-25T10:02:00+05:00",
             "created_by": "someone", "comment_stripped": "!answer do it"},
            {"id": "ordinary", "created_at": "2026-10-25T10:03:00+05:00",
             "created_by": OP, "comment_stripped": "any updates?"},
            {"id": "bot", "created_at": "2026-10-25T10:04:00+05:00",
             "created_by": OP, "comment_stripped": "!answer skip security",
             "external_source": orch.SOURCE},
        ]
        self.assertIn("Awaiting !answer", self.fake.runner().step()["blocked"][0][1])
        self.assertEqual(len(self.fake.runs), 1)

    def test_restart_after_uncertain_write_never_repeats_start(self):
        def failed(name, args):
            if name == "workitem" and args["action"] == "update":
                raise ValueError("uncertain Plane update")
            return self.fake.call(name, args)
        runner = self.fake.runner()
        runner.api = failed
        with self.assertRaisesRegex(ValueError, "uncertain"):
            runner.step()
        self.assertEqual(len(self.fake.runs), 0)
        result = self.fake.runner().step()
        self.assertIn("Uncertain prior run", result["blocked"][0][1])
        self.assertEqual(len(self.fake.runs), 0)

    def test_uncertain_question_write_cannot_be_replayed(self):
        def failed(name, args):
            if name == "workitem_comment":
                raise ValueError("uncertain comment write")
            return self.fake.call(name, args)
        runner = self.fake.runner()
        runner.api = failed
        with self.assertRaisesRegex(ValueError, "uncertain"):
            runner.step()
        self.assertEqual(self.fake.runner().ledger[f"{P}/{T}"]["phase"], "posting")
        self.assertIn("manual reconciliation", self.fake.runner().step()["blocked"][0][1])
        self.assertEqual(len(self.fake.runs), 1)

    def test_missing_mapping_is_blocked_without_mutation(self):
        runner = orch.Runner({"operator_id": OP, "private_dir": self.tmp.name,
                              "projects": {}}, self.fake.call, self.fake.pages,
                             self.fake.worker)
        self.assertEqual(runner.step()["blocked"],
                         [(f"{P}/{T}", "Missing explicit repository mapping")])
        self.assertFalse(self.fake.writes)

    def test_interrupted_ledger_write_blocks_restart(self):
        (self.fake.home / "ledger.json.tmp").write_text("{}")
        with self.assertRaisesRegex(ValueError, "Uncertain interrupted ledger"):
            self.fake.runner()
        self.assertFalse(self.fake.writes)

    def test_retired_launcher_does_not_block_healthy_pi_cli(self):
        def pi_available(command, **kwargs):
            if command[0] == "pi-workflow":
                raise FileNotFoundError("retired pi-workflow")
            self.assertEqual(command[:2], ["pi-bolt", "--help"])
            return Mock(returncode=0)

        with patch.object(orch.subprocess, "run", side_effect=pi_available):
            result = self.fake.runner().step()
        self.assertIn("waiting", result,
                      "Retired pi-workflow must not block a healthy Pi CLI")
        self.assertEqual(len(self.fake.runs), 1)

    def test_broken_runtime_helper_fails_before_plane_writes(self):
        with patch.object(orch.subprocess, "run", side_effect=FileNotFoundError("pi-workflow")):
            result = self.fake.runner().step()
        self.assertIn("preflight failed", result["blocked"][0][1])
        self.assertFalse(self.fake.writes)
        self.assertFalse(self.fake.runs)

    def test_incomplete_plane_pagination_is_not_an_empty_queue(self):
        def incomplete(name, **kwargs):
            if name == "workitem":
                raise ValueError("Incomplete Plane pagination")
            return self.fake.pages(name, **kwargs)
        runner = self.fake.runner()
        runner.list_pages = incomplete
        with self.assertRaisesRegex(ValueError, "Incomplete Plane pagination"):
            runner.step()
        self.assertFalse(self.fake.writes)

    def test_missing_project_workflow_blocks_only_that_project(self):
        other = "e" * 8 + "-eeee-eeee-eeee-" + "e" * 12
        unsupported = {"id": other, "name": "Another project"}
        unsupported_task = {**self.fake.task, "id": "f" * 8 + "-ffff-ffff-ffff-" + "f" * 12,
                            "project": other}
        original_pages = self.fake.pages
        scanned = []

        def pages(name, **kwargs):
            if name == "project":
                return [unsupported, self.fake.project.copy()]
            if name == "workitem":
                scanned.append(kwargs["project_id"])
                return [unsupported_task.copy()] if kwargs["project_id"] == other else original_pages(name, **kwargs)
            if name == "state" and kwargs["project_id"] == other:
                return [s.copy() for s in self.fake.states if s["name"] != "In Review"]
            return original_pages(name, **kwargs)

        runner = self.fake.runner()
        runner.list_pages = pages
        result = runner.step()
        self.assertEqual(result["waiting"], f"{P}/{T}",
                         "Unsupported project workflow must not stop independent Todo work")
        self.assertEqual(scanned, [other, P], "Paginate even unsupported projects")
        self.assertIn((f"{other}/workflow", "Missing or ambiguous In Review state"),
                      result["blocked"])
        self.assertEqual(len(self.fake.runs), 1)

    def test_state_page_error_never_becomes_project_local_blocker(self):
        def failed(name, **kwargs):
            if name == "state":
                raise ValueError("Incomplete Plane pagination")
            return self.fake.pages(name, **kwargs)

        runner = self.fake.runner()
        runner.list_pages = failed
        with self.assertRaisesRegex(ValueError, "Incomplete Plane pagination"):
            runner.step()
        self.assertFalse(self.fake.writes)

    def test_claim_without_actual_review_never_counts_as_delivery(self):
        self.fake.output = '{"orchestrator":"in_review"}'
        with self.assertRaisesRegex(ValueError, "claimed review"):
            self.fake.runner().step()
        self.assertEqual(self.fake.runner().ledger[f"{P}/{T}"]["phase"], "running")

    def test_task_local_blocker_is_recorded_without_claiming_review(self):
        self.fake.output = '{"orchestrator":"blocked","reason":"Acceptance gate failed"}'
        result = self.fake.runner().step()
        self.assertEqual(result["blocked_task"], f"{P}/{T}")
        self.assertEqual(self.fake.task["state"], "doing")
        self.assertIn("manual reconciliation", self.fake.runner().step()["blocked"][0][1])
        self.assertEqual(len(self.fake.runs), 1)

    def test_foreign_in_progress_is_never_stolen(self):
        self.fake.task["state"] = "doing"
        result = self.fake.runner().step()
        self.assertIn("not owned", result["blocked"][0][1])
        self.assertFalse(self.fake.writes)

    def test_invalid_model_signal_is_not_a_question(self):
        for output in ("Here is a summary", '{"orchestrator":"needs_you","question":""}',
                       '{"orchestrator":"done"}'):
            with self.subTest(output=output), self.assertRaises(ValueError):
                orch.outcome(output)


if __name__ == "__main__":
    unittest.main()

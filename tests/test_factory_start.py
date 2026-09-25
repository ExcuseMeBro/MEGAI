"""Factory starts only the selected existing Plane item; never creates substitutes."""

import copy
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

source = Path(__file__).resolve().parents[1] / "pi-defaults/workflow.py"
spec = importlib.util.spec_from_file_location("factory_workflow", source)
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


class FactoryStart(unittest.TestCase):
    def setUp(self):
        self.item = {"id": "task", "name": "Build feature", "state": "todo",
                     "labels": ["ready"], "description_stripped": "Acceptance: tests pass"}
        self.calls = []
        self.reads = 0
        self.drift = None

    def api(self, tool, args):
        self.calls.append((tool, args))
        if tool == "project":
            return {"results": [{"name": "APP", "id": "project"}], "next_page_results": False}
        if tool == "label":
            return {"results": [{"name": "factory-ready", "id": "ready"}], "next_page_results": False}
        if args["action"] == "retrieve":
            self.reads += 1
            if self.item is None:
                raise ValueError("Selected item disappeared")
            if self.drift and self.reads == 2:
                self.item.update(self.drift)
            return dict(self.item)
        if args["action"] == "update":
            return {**self.item, "state": args["state"]}
        raise AssertionError(args)

    def run_factory(self):
        with (patch.object(sys, "argv", ["pi-workflow", "factory-start", "--cwd", "/tmp",
                                         "--project-id", "project", "--task-id", "task",
                                         "--title", "Build feature"]),
              patch.object(workflow, "context", return_value={"planeProject": "APP"}),
              patch.object(workflow, "states", return_value={"Todo": "todo", "In Progress": "started"}),
              patch.object(workflow, "call", side_effect=self.api)):
            return workflow.main()

    def test_selected_item_starts_once_without_create(self):
        self.assertEqual(self.run_factory()["task_id"], "task")
        self.assertEqual([args["action"] for _, args in self.calls if args["action"] == "update"], ["update"])
        self.assertFalse(any(args["action"] == "create" for _, args in self.calls))

    def test_no_label_required_and_expanded_labels_are_supported(self):
        for labels in ([], [{"id": "custom", "name": "feature"}]):
            with self.subTest(labels=labels):
                self.setUp()
                self.item["labels"] = labels
                self.assertEqual(self.run_factory()["state"], "In Progress")
                self.assertFalse(any(tool == "label" for tool, _ in self.calls))

    def test_resume_in_progress_without_redundant_write(self):
        self.item["state"] = "started"
        self.assertEqual(self.run_factory()["task_id"], "task")
        self.assertEqual(self.reads, 2)
        self.assertFalse(any(args["action"] in ("create", "update") for _, args in self.calls))

    def test_disappearance_reassignment_and_ineligibility_cause_no_mutation(self):
        for changed in (None, {"name": "Other"}, {"id": "other"}, {"project": "foreign"},
                        {"state": "review"}, {"description_stripped": ""}):
            with self.subTest(changed=changed):
                self.calls = []
                original = {"id": "task", "name": "Build feature", "state": "todo",
                            "labels": ["ready"], "description_stripped": "Acceptance: tests pass"}
                self.item = None if changed is None else {**original, **changed}
                with self.assertRaises(ValueError):
                    self.run_factory()
                self.assertFalse(any(args["action"] in ("create", "update") for _, args in self.calls))

    def test_drift_before_update_causes_no_mutation(self):
        for drift in ({"name": "Reassigned"}, {"labels": []}, {"state": "started"},
                      {"description_stripped": "Changed acceptance"}, {"assignees": ["other"]}):
            with self.subTest(drift=drift):
                self.setUp()
                self.drift = drift
                with self.assertRaises(ValueError):
                    self.run_factory()
                self.assertEqual(self.reads, 2)
                self.assertFalse(any(args["action"] in ("create", "update")
                                     for _, args in self.calls))


class FactoryPlan(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.rows = [
            {"id": "00000000-0000-4000-8000-000000000012", "sequence_id": 12,
             "name": "Build twelve", "project": "project", "state": "todo"},
            {"id": "00000000-0000-4000-8000-000000000034", "sequence_id": 34,
             "name": "Resume thirty four", "project": "project", "state": "started"},
            {"id": "00000000-0000-4000-8000-000000000056", "sequence_id": 56,
             "name": "Review only", "project": "project", "state": "review"},
        ]

    def api(self, name, args):
        self.calls.append((name, copy.deepcopy(args)))
        self.assertEqual(args["action"], "list", "Planning must never mutate Plane")
        if name == "project":
            return {"results": [{"id": "project", "name": "APP", "identifier": "PRJ"}],
                    "next_page_results": False}
        if name == "state":
            return {"results": [
                {"id": id_, "name": label, "group": group}
                for id_, label, group in (("todo", "Todo", "unstarted"),
                    ("started", "In Progress", "started"), ("review", "In Review", "started"),
                    ("done", "Done", "completed"))], "next_page_results": False}
        self.assertEqual(name, "workitem")
        self.assertEqual(args["project_id"], "project")
        if args.get("cursor") == "second":
            return {"results": copy.deepcopy(self.rows[1:]), "next_page_results": False}
        return {"results": copy.deepcopy(self.rows[:1]), "next_page_results": True,
                "next_cursor": "second"}

    def plan(self, selection, expected_project=None, api=None):
        with (patch.object(workflow, "context", return_value={"planeProject": "APP"}),
              patch.object(workflow, "call", side_effect=api or self.api)):
            return workflow.factory_plan("/tmp", selection, expected_project)

    def test_all_reads_every_page_and_resumes_started_first(self):
        result = self.plan("all")
        self.assertEqual([row["sequence_id"] for row in result["tasks"]], [34, 12])
        self.assertEqual(result["remaining"], 2)
        self.assertFalse(result["queue_empty"])
        self.assertTrue(any(args.get("cursor") == "second" for _, args in self.calls))

    def test_explicit_ids_preserve_order_dedupe_and_never_broaden(self):
        for selection in ("12,34,12", "APP-12, PRJ-34,12",
                          self.rows[0]["id"] + ",34,12"):
            with self.subTest(selection=selection):
                result = self.plan(selection)
                self.assertEqual(result["mode"], "ids")
                self.assertEqual([row["sequence_id"] for row in result["tasks"]], [12, 34])
        self.assertEqual([row["sequence_id"] for row in self.plan("12")["tasks"]], [12])

    def test_bad_or_foreign_selection_fails_without_mutation(self):
        for selection in ("", "all,12", "12,", ",12", "12 34", "OTHER-12", "999",
                          "12,999", "Build twelve", "0", "12; touch /tmp/no"):
            with self.subTest(selection=selection), self.assertRaises(ValueError):
                self.plan(selection)

    def test_protected_states_are_reported_not_reopened(self):
        for state in ("review", "done", "backlog", "cancelled"):
            self.rows[2]["state"] = state
            result = self.plan("56")
            self.assertEqual(result["tasks"], [])
            self.assertEqual(result["skipped"][0]["sequence_id"], 56)

    def test_refresh_discovers_new_tasks_and_proves_empty_only_after_handoff(self):
        frozen = self.rows[0]["id"]
        self.rows[0]["state"] = "review"
        self.rows.append({**self.rows[0], "id": "new", "sequence_id": 99, "state": "todo"})
        self.assertEqual([r["sequence_id"] for r in self.plan("all")["tasks"]], [34, 99])
        self.assertEqual(self.plan(frozen)["tasks"], [])
        for row in self.rows:
            row["state"] = "review"
        self.assertTrue(self.plan("all")["queue_empty"])

    def test_project_drift_duplicate_or_foreign_rows_block(self):
        with self.assertRaisesRegex(ValueError, "project changed"):
            self.plan("all", "foreign")
        for mutation in ({"id": self.rows[0]["id"]}, {"project": "foreign"},
                         {"state": None}, {"sequence_id": True}):
            with self.subTest(mutation=mutation):
                original = self.rows[1].copy()
                self.rows[1].update(mutation)
                with self.assertRaises(ValueError):
                    self.plan("all")
                self.rows[1] = original
        self.rows[1]["sequence_id"] = 12
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            self.plan("12")

    def test_failed_incomplete_or_repeating_pagination_never_means_empty(self):
        original = self.api
        for mode in ("error", "incomplete", "loop"):
            def api(name, args):
                if name == "workitem" and args.get("cursor"):
                    if mode == "error":
                        raise ValueError("Plane unavailable")
                    if mode == "incomplete":
                        return {"results": []}
                    return {"results": [], "next_page_results": True, "next_cursor": "second"}
                return original(name, args)
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.plan("all", api=api)


if __name__ == "__main__":
    unittest.main()

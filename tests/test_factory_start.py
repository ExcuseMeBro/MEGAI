"""Factory starts only the selected existing Plane item; never creates substitutes."""

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

    def test_disappearance_reassignment_and_ineligibility_cause_no_mutation(self):
        for changed in (None, {"name": "Other"}, {"id": "other"}, {"labels": []},
                        {"state": "started"}, {"description_stripped": ""}):
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
                      {"description_stripped": "Changed acceptance"}):
            with self.subTest(drift=drift):
                self.setUp()
                self.drift = drift
                with self.assertRaises(ValueError):
                    self.run_factory()
                self.assertEqual(self.reads, 2)
                self.assertFalse(any(args["action"] in ("create", "update")
                                     for _, args in self.calls))


if __name__ == "__main__":
    unittest.main()

"""Check that independent acceptance rejects broken starter implementations."""
from pathlib import Path
import tempfile
import unittest

from live_tasks import TASKS
from mac_live_coding import acceptance, refactor_checks

class LiveAcceptanceTests(unittest.TestCase):
    def baseline(self, name):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); cwd=root/'work'; artifact=root/'artifact'
            cwd.mkdir(); artifact.mkdir()
            task=TASKS[name]
            for path,source in task['files'].items(): (cwd/path).write_text(source)
            result=acceptance(cwd,artifact,task)
            structural=refactor_checks(cwd,task) if name=='order-refactor' else []
            return result,structural

    def test_query_suite_rejects_starter(self):
        result,_=self.baseline('query-bugfix')
        self.assertEqual(result['tests'],16)
        self.assertNotEqual(result['exit_code'],0)
        self.assertGreater(result['failures'],0)

    def test_cache_suite_rejects_unimplemented_feature(self):
        result,_=self.baseline('ttl-lru-feature')
        self.assertEqual(result['tests'],19)
        self.assertEqual(result['errors'],19)
        self.assertNotEqual(result['exit_code'],0)

    def test_refactor_needs_behavior_and_structural_change(self):
        result,structural=self.baseline('order-refactor')
        self.assertEqual(result['tests'],12)
        self.assertEqual(result['exit_code'],0)
        self.assertTrue(any('unchanged' in p for p in structural))
        self.assertTrue(any('duplicated' in p for p in structural))

if __name__=='__main__': unittest.main()

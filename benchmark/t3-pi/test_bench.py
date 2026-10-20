import concurrent.futures
import tempfile
import threading
import unittest
from pathlib import Path
from bench import Receipts, Uncertain


class ReceiptsTest(unittest.TestCase):
    def test_completed_receipt_survives_reopen_and_binds_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'db'
            calls = []
            result = Receipts(path).dispatch('id', {'a': 1}, lambda: calls.append(1) or {'value': 3})
            self.assertEqual(result, {'value': 3})
            self.assertEqual(Receipts(path).dispatch('id', {'a': 1}, lambda: self.fail('replayed side effect')), result)
            self.assertEqual(len(calls), 1)
            with self.assertRaisesRegex(ValueError, 'payload mismatch'):
                Receipts(path).dispatch('id', {'a': 2}, lambda: None)

    def test_all_uncommitted_failures_block_even_before_send(self):
        for phase in ('before_send', 'action', 'before_commit'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / 'db'
                effects = []
                def fail():
                    raise ConnectionError('injected')
                def action():
                    effects.append(1)
                    return {'ok': True}
                hooks = {phase: fail} if phase != 'action' else {}
                with self.assertRaises(ConnectionError):
                    Receipts(path).dispatch('id', {}, fail if phase == 'action' else action, **hooks)
                with self.assertRaises(Uncertain):
                    Receipts(path).dispatch('id', {}, lambda: self.fail('unsafe retry'))
                self.assertEqual(len(effects), int(phase == 'before_commit'))

    def test_concurrent_duplicate_does_not_duplicate_external_action(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'db'
            store = Receipts(path)
            entered = threading.Event()
            release = threading.Event()
            def action():
                entered.set()
                self.assertTrue(release.wait(5))
                return {'ok': True}
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                task = pool.submit(store.dispatch, 'id', {}, action)
                try:
                    self.assertTrue(entered.wait(5))
                    with self.assertRaises(Uncertain):
                        Receipts(path).dispatch('id', {}, lambda: self.fail('duplicate'))
                    self.assertEqual(Receipts(path).dispatch('other', {}, lambda: {'independent': True}), {'independent': True})
                finally:
                    release.set()
                self.assertEqual(task.result(timeout=5), {'ok': True})


if __name__ == '__main__':
    unittest.main()

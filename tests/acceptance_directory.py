#!/usr/bin/env python3
"""Real non-Git acceptance CLI tests; review identities are synthetic fixtures only."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from acceptance_gate import AcceptanceGateTest, save, sha256


class DirectoryAcceptanceTest(unittest.TestCase):
    invoke = AcceptanceGateTest.invoke
    snapshot = AcceptanceGateTest.snapshot
    execute = AcceptanceGateTest.execute
    fixture = AcceptanceGateTest.fixture
    check = AcceptanceGateTest.check

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / 'configuration'
        self.root.mkdir()
        (self.root / 'source.txt').write_text('configuration')

    def test_directory_run_and_check_without_git(self):
        result = self.invoke('snapshot', '--root', self.root)
        self.assertEqual(result.returncode, 0,
                         'non-Git configuration acceptance must work: ' + result.stdout)
        directory, _, _ = self.fixture()
        self.check(directory)
        (self.root / 'source.txt').write_text('changed configuration')
        self.check(directory, 2, 'snapshot')

    def test_full_inventory_changes_invalidate(self):
        original = self.snapshot()
        file = self.root / '.hidden-config'
        file.write_text('hidden files are included')
        self.assertNotEqual(original, self.snapshot())
        current = self.snapshot()
        file.chmod(0o700)
        self.assertNotEqual(current, self.snapshot())
        file.unlink()
        self.assertEqual(original, self.snapshot())
        (self.root / 'empty').mkdir()
        self.assertNotEqual(original, self.snapshot())

    def test_symlink_fifo_and_git_metadata_rejected(self):
        for kind in ('symlink', 'fifo', 'git'):
            with self.subTest(kind=kind):
                path = self.root / ('.git' if kind == 'git' else 'unsafe')
                if kind == 'symlink':
                    path.symlink_to(self.root / 'source.txt')
                elif kind == 'fifo':
                    os.mkfifo(path)
                else:
                    path.write_text('gitdir: /missing/broken\n')
                result = self.invoke('snapshot', '--root', self.root)
                self.assertEqual(result.returncode, 2, result.stdout)
                path.unlink()
        child = self.root / 'nested'
        (child / '.git').mkdir(parents=True)
        result = self.invoke('snapshot', '--root', self.root)
        self.assertEqual(result.returncode, 2, result.stdout)

    def test_capture_tests_and_detect_mutation(self):
        test = self.root / 'check.py'
        test.write_text('raise SystemExit(1)\n')
        result = self.invoke('run', '--root', self.root, '--out', self.base / 'red',
                             '--test-file', 'check.py', '--', sys.executable, '-B', 'check.py')
        self.assertEqual(result.returncode, 1, result.stdout)
        receipt = json.loads((self.base / 'red/receipt.json').read_text())
        self.assertEqual(receipt['test_files'], [{'path': 'check.py', 'sha256': sha256(test)}])
        mutation = self.execute(self.base / 'mutation', [sys.executable, '-c',
            "from pathlib import Path; Path('new-config').write_text('new')"])
        self.assertEqual(mutation.returncode, 2, mutation.stdout)
        self.assertIn('Source changed', mutation.stdout)

    def test_collect_still_requires_review(self):
        directory, contract, evidence = self.fixture()
        output = directory / 'collection'
        result = self.invoke('collect', '--root', self.root, '--contract', directory / 'contract.json',
                             '--contract-sha256', sha256(directory / 'contract.json'), '--out', output)
        self.assertEqual(result.returncode, 2, result.stdout)
        draft = json.loads((output / 'evidence.json').read_text())
        self.assertEqual(draft['checks'][0]['status'], 'PASS')
        self.assertEqual(draft['review']['verdict'], 'BLOCKED')
        evidence['review']['session_id'] = contract['implementer_session_id']
        save(directory / 'evidence.json', evidence)
        self.check(directory, 2, 'independent review')


if __name__ == '__main__':
    unittest.main()

"""Focused measurement/fixture checks; no model credentials or network services."""
import ctypes
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from mac_workloads import TaskInfo, TreeSampler, make_session

class MeasurementTests(unittest.TestCase):
    def test_macos_task_info_layout(self):
        self.assertEqual(ctypes.sizeof(TaskInfo), 96)

    def test_sampler_counts_children_and_memory(self):
        # The measured process deliberately spawns a live allocating child.
        code = "import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c','import time; b=bytearray(32*1024*1024); time.sleep(0.4)']); p.wait()"
        process = subprocess.Popen([sys.executable, '-c', code])
        with TreeSampler(process.pid) as sampler:
            self.assertEqual(process.wait(timeout=5), 0)
        self.assertGreater(sampler.samples, 5)
        self.assertGreaterEqual(sampler.max_processes, 2)
        self.assertGreater(sampler.peak, 32 * 1024 * 1024)

    def test_session_fixture_has_valid_parent_chain_and_2000_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            make_session(path, Path(directory))
            entries = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(len(entries), 4001)
        self.assertEqual(entries[0]['version'], 3)
        parent = None
        seen = set()
        for i, entry in enumerate(entries[1:]):
            self.assertEqual(entry['parentId'], parent)
            self.assertNotIn(entry['id'], seen)
            self.assertEqual(entry['message']['role'], 'user' if i % 2 == 0 else 'assistant')
            seen.add(entry['id'])
            parent = entry['id']
        self.assertIn('HISTORY_0000', str(entries[1]))
        self.assertIn('HISTORY_1999', str(entries[-1]))

if __name__ == '__main__':
    unittest.main()

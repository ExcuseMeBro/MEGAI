"""Native policy migration accepts managed blocks but preserves custom base text."""
import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
spec = importlib.util.spec_from_file_location("pi_model_policy", ROOT / "lib/pi_model_policy.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class UnchangedPlan:
    changes = {}

    def stage(self, *args):
        raise AssertionError("An already-current policy must not be rewritten")


class NativePolicyParity(unittest.TestCase):
    def test_current_engineering_and_runtime_blocks_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "source"
            defaults = source / "pi-defaults"
            defaults.mkdir(parents=True)
            shutil.copy2(ROOT / "pi-defaults/install.py", defaults / "install.py")
            native = (b"Native policy.\n\n<!-- megai:engineering:begin -->\n"
                      b"Use the current engineering workflow.\n<!-- megai:engineering:end -->\n")
            (defaults / "AGENTS.md").write_bytes(native)
            agent = root / "agent"
            agent.mkdir()
            installed = native + (b"\n<!-- megai:slim:begin -->\n"
                                  b"Keep runtime policy.\n<!-- megai:slim:end -->\n")
            agents = agent / "AGENTS.md"
            agents.write_bytes(installed)
            policy.migrate_known_agy_policy(UnchangedPlan(), agent, source)
            self.assertEqual(agents.read_bytes(), installed)
            agents.write_bytes(installed + b"Custom base instruction.\n")
            with self.assertRaisesRegex(ValueError, "unrecognized/custom"):
                policy.migrate_known_agy_policy(UnchangedPlan(), agent, source)
            self.assertEqual(agents.read_bytes(), installed + b"Custom base instruction.\n")


if __name__ == "__main__":
    unittest.main()

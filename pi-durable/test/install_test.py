"""Real offline scoped installs with disposable homes and preserved sentinel configs."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
from install import install  # noqa: E402


class InstallTests(unittest.TestCase):
    def test_scoped_install_and_reinstall_preserve_configs(self):
        with tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve()) as temporary:
            root = Path(temporary)
            home = root / "megai"
            bin_dir = root / "bin"
            sentinel_paths = []
            for scope in ["pi", "other-app"]:
                directory = root / scope
                directory.mkdir(mode=0o700)
                for name in ["settings.json", "auth.json", "models.json", "sessions.jsonl"]:
                    path = directory / name
                    path.write_text(f"{scope} existing {name}\n")
                    path.chmod(0o600)
                    sentinel_paths.append(path)
            hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in sentinel_paths}
            result = install(SOURCE, home, bin_dir)
            self.assertEqual(result["status"], "preflight")
            self.assertFalse(home.exists())
            installed = install(SOURCE, home, bin_dir, apply=True, offline=True)
            self.assertEqual(installed["status"], "installed")
            runtime = Path(installed["runtime"])
            for name in ["runtime.mjs", "worker.mjs", "launcher.py"]:
                self.assertNotIn("paseo", (runtime / name).read_text().lower())
            lock = json.loads((runtime / "package-lock.json").read_text())
            self.assertEqual(lock["packages"]["node_modules/@earendil-works/pi-durable"]["version"], "1.1.0")
            command = bin_dir / "pi-durable"
            help_result = subprocess.run([command, "--help"], capture_output=True, text=True, timeout=10)
            self.assertEqual(help_result.returncode, 0, help_result.stdout + help_result.stderr)
            self.assertIn("resume", help_result.stdout)
            # Same-version install does not remove/reinstall dependencies under active runtimes.
            dependency = runtime / "node_modules/@earendil-works/pi-durable/package.json"
            before = dependency.stat().st_mtime_ns
            again = install(SOURCE, home, bin_dir, apply=True, offline=True)
            self.assertEqual(again["version"], installed["version"])
            self.assertEqual(dependency.stat().st_mtime_ns, before)
            for path, value in hashes.items():
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), value)
            command.write_text("custom user command\n")
            with self.assertRaisesRegex(ValueError, "Custom/changed"):
                install(SOURCE, home, bin_dir)
            self.assertEqual(command.read_text(), "custom user command\n")

    def test_symlinks_and_runtime_drift_refused(self):
        with tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve()) as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            alias = root / "alias"
            alias.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "Symlink refused"):
                install(SOURCE, alias, root / "bin")
            installed = install(SOURCE, root / "megai", root / "bin", apply=True, offline=True)
            file = Path(installed["runtime"]) / "runtime.mjs"
            file.write_text(file.read_text() + "\n// changed\n")
            with self.assertRaisesRegex(ValueError, "runtime drift"):
                install(SOURCE, root / "megai", root / "bin")
            self.assertEqual(list(outside.iterdir()), [])

    def test_concurrent_destination_publication_never_clobbers_a_new_command(self):
        with tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve()) as temporary:
            root = Path(temporary)
            launcher = root / 'bin/pi-durable'
            original_replace, original_link = os.replace, os.link

            def competing_publication(source, destination, *args, **kwargs):
                if Path(destination) == launcher and not launcher.exists():
                    launcher.write_text('concurrent human-owned command\\n')
                return original_replace(source, destination, *args, **kwargs)

            def competing_link(source, destination, *args, **kwargs):
                if Path(destination) == launcher and not launcher.exists():
                    launcher.write_text('concurrent human-owned command\\n')
                return original_link(source, destination, *args, **kwargs)

            with mock.patch('os.replace', competing_publication), mock.patch('os.link', competing_link):
                with self.assertRaises((ValueError, OSError)):
                    install(SOURCE, root / 'megai', root / 'bin', apply=True, offline=True)
            self.assertEqual(launcher.read_text(), 'concurrent human-owned command\\n')

    def test_different_installation_homes_share_the_destination_lock(self):
        with tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve()) as temporary:
            root = Path(temporary)
            destination = root / 'bin'
            destination.mkdir()
            fd = os.open(destination / '.pi-durable-install.lock', os.O_RDWR | os.O_CREAT, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError):
                    install(SOURCE, root / 'other-home', destination, apply=True, offline=True)
                self.assertFalse((destination / 'pi-durable').exists())
                self.assertFalse((root / 'other-home/pi-durable/install.json').exists())
            finally:
                os.close(fd)

    def test_launcher_conflicts_and_private_state(self):
        with tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve()) as temporary:
            root = Path(temporary)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            command = bin_dir / "pi-durable"
            command.write_text("human-owned\n")
            with self.assertRaisesRegex(ValueError, "Custom/changed"):
                install(SOURCE, root / "megai", bin_dir)
            self.assertFalse((root / "megai").exists())
            task = root / "public-task"
            task.mkdir()
            task.chmod(0o755)
            result = subprocess.run([sys.executable, "-B", SOURCE / "launcher.py", "status", "--task", task],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertIn("private and user-owned", result.stdout)
            self.assertFalse((task / "owner.lock").exists())
            self.assertEqual(command.read_text(), "human-owned\n")


if __name__ == "__main__":
    os.umask(0o077)
    unittest.main()

#!/usr/bin/env python3
"""Offline contracts for the pinned local runtime installer.

The heavy step — the checkpoint download — is faked: a stub `uv` and a stub interpreter
record what the installer asked for, so ownership, the platform gate, the hash lock and
the checkpoint verification are all checkable without a network or a real 1 GB
download. The real download runs once in tests/pi-laya-live.sh.
"""
from __future__ import annotations

import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "lib/install_laya.sh"
LOCK = ROOT / "lib/laya.lock"

PYTHON_STUB = """#!/bin/bash
printf 'python %s\\n' "$*" >> "$LAYA_TEST_CALLS"
printf 'env device=%s lang=%s\\n' "${LAYA_DEVICE:-}" "${LAYA_LANG:-}" >> "$LAYA_TEST_CALLS"
version="${LAYA_TEST_PYTHONVERSION:-3.11}"
if [ "${LAYA_TEST_VENV_WRONG:-0}" = 1 ] && [ "$0" != "${LAYA_TEST_PYTHON:-}" ]; then
  version="3.10"
fi
case " $* " in
  *" --check "*)
    if [ "${LAYA_STUB_CHECKPOINT_FAIL:-0}" = 1 ]; then
      printf 'laya: multilingual checkpoint failed to load\\n' >&2
      exit 1
    fi
    printf 'english=convaiinnovations/laya\\nmultilingual=convaiinnovations/laya:multilingual\\n'
    ;;
  *"sys.version_info"*)
    printf '%s\\n' "$version"
    ;;
  *"m.version"*)
    printf '%s\\n' "${LAYA_TEST_LAYAVERSION:-0.3.5}"
    ;;
esac
exit 0
"""

UV_STUB = """#!/bin/bash
printf 'uv %s\\n' "$*" >> "$LAYA_TEST_CALLS"
case "$1" in
  venv)
    for last; do :; done
    mkdir -p "$last/bin"
    cp "$LAYA_TEST_PYTHON" "$last/bin/python"
    chmod +x "$last/bin/python"
    ;;
  pip)
    if [ "${LAYA_STUB_PIP_FAIL:-0}" = 1 ]; then
      printf 'uv pip: simulated install failure\\n' >&2
      exit 1
    fi
    ;;
esac
exit 0
"""


class RuntimeInstall(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="laya-runtime-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.megai = self.home / ".megai"
        self.megai.mkdir(parents=True)
        self.venv = self.megai / "venv/laya"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.calls = self.root / "calls"
        self.calls.write_text("")
        self.python = self.script("stub-python", PYTHON_STUB)
        self.uv = self.script("uv", UV_STUB)

    def script(self, name, body):
        path = self.bin / name
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
        return path

    def install(self, *args, **extra):
        env = dict(
            os.environ,
            MEGAI_HOME=str(self.megai),
            LAYA_VENV=str(self.venv),
            LAYA_INTERPRETER=str(self.python),
            LAYA_UV=str(self.uv),
            LAYA_TEST_CALLS=str(self.calls),
            LAYA_TEST_PYTHON=str(self.python),
            PATH=f"{self.bin}:{os.environ['PATH']}",
        )
        for name in ("LAYA_DEVICE", "LAYA_LANG", "LAYA_PLATFORM", "LAYA_STUB_CHECKPOINT_FAIL",
                     "LAYA_STUB_PIP_FAIL", "LAYA_TEST_LAYAVERSION", "LAYA_TEST_PYTHONVERSION",
                     "LAYA_TEST_VENV_WRONG"):
            env.pop(name, None)
        env.update({name: str(value) for name, value in extra.items()})
        return subprocess.run(["bash", str(SCRIPT), *args], env=env, text=True, capture_output=True)

    def test_a_fresh_prepare_builds_an_owned_venv_from_the_hash_lock(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self.calls.read_text()
        self.assertIn(f"uv venv --python {self.python} {self.venv}", calls)
        self.assertIn(f"uv pip install --require-hashes --python {self.venv}/bin/python -r {LOCK}", calls)
        self.assertIn("--check", calls)
        marker = (self.venv / ".megai-owned").read_text()
        self.assertIn("model=convaiinnovations/laya", marker)
        self.assertIn("python=3.11", marker)
        self.assertIn("English + multilingual", result.stdout)

    def test_a_prepared_runtime_is_reused_and_still_verified(self):
        self.install()
        self.calls.write_text("")
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self.calls.read_text()
        self.assertNotIn("uv venv", calls)
        self.assertNotIn("uv pip install", calls)
        self.assertIn("already prepared", result.stdout)
        self.assertIn("--check", calls, "reuse must re-verify the checkpoints")

    def test_prepare_only_reports_a_ready_runtime(self):
        result = self.install("--prepare-only")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("runtime ready", result.stdout)
        self.assertTrue((self.venv / ".megai-owned").is_file())

    def test_an_unowned_venv_is_refused_and_left_alone(self):
        self.venv.mkdir(parents=True)
        (self.venv / "foreign").write_text("someone else's environment\n")
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not owned by MEGAI", result.stderr)
        self.assertEqual(self.calls.read_text(), "")
        self.assertTrue((self.venv / "foreign").is_file())

    def test_an_unsupported_platform_stops_before_any_write(self):
        result = self.install(LAYA_PLATFORM="Linux/i386")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no pinned runtime for Linux/i386", result.stderr)
        self.assertFalse(self.venv.exists())
        self.assertEqual(self.calls.read_text(), "")

    def test_the_lock_pins_every_requirement_with_a_wheel_hash(self):
        text = LOCK.read_text()
        entries = [line for line in text.splitlines() if "==" in line and not line.startswith((" ", "#"))]
        hashes = sum(1 for line in text.splitlines() if "--hash=sha256:" in line)
        self.assertGreater(len(entries), 30)
        self.assertGreaterEqual(hashes, len(entries), "every pinned requirement needs a wheel hash")
        for name in ("laya==0.3.5", "torch==", "transformers==", "huggingface-hub==",
                     "safetensors==", "numpy=="):
            with self.subTest(requirement=name):
                self.assertTrue(any(line.startswith(name) for line in entries), name)

    def test_a_failed_checkpoint_is_never_reported_as_ready(self):
        result = self.install(LAYA_STUB_CHECKPOINT_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checkpoints are not verified", result.stderr)
        self.assertNotIn("runtime ready", result.stdout)

    def test_check_only_never_installs(self):
        self.install()
        self.calls.write_text("")
        result = self.install("--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ready ->", result.stdout)
        self.assertNotIn("uv ", self.calls.read_text())

    def test_check_without_a_runtime_points_at_the_installer(self):
        result = self.install("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("run `bash lib/install_laya.sh`", result.stderr)

    def test_remove_takes_only_an_owned_runtime(self):
        self.install()
        result = self.install("--remove")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.venv.exists())
        self.venv.mkdir(parents=True)
        self.assertNotEqual(self.install("--remove").returncode, 0)

    def test_device_and_language_are_passed_to_the_checkpoint_check(self):
        result = self.install(LAYA_DEVICE="cpu", LAYA_LANG="uz")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("env device=cpu lang=uz", self.calls.read_text())

    def test_a_failed_install_is_retried_without_being_refused_as_unowned(self):
        failed = self.install(LAYA_STUB_PIP_FAIL="1")
        self.assertNotEqual(failed.returncode, 0, failed.stdout + failed.stderr)
        marker = (self.venv / ".megai-owned").read_text()
        self.assertIn("owner=megai-laya", marker)
        self.assertIn("state=partial", marker)
        self.calls.write_text("")
        retried = self.install()
        self.assertEqual(retried.returncode, 0, retried.stdout + retried.stderr)
        self.assertNotIn("not owned by MEGAI", retried.stderr)
        self.assertIn("state=installed", (self.venv / ".megai-owned").read_text())

    def test_a_stale_lock_pin_rebuilds_the_owned_runtime(self):
        self.install()
        marker = self.venv / ".megai-owned"
        marker.write_text(re.sub(r"^lock=.*$", "lock=" + "0" * 64, marker.read_text(), flags=re.M))
        self.calls.write_text("")
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("rebuilding", result.stdout)
        self.assertIn("uv venv", self.calls.read_text())
        self.assertNotIn("lock=" + "0" * 64, marker.read_text())

    def test_a_wrong_installed_laya_version_is_never_reported_ready(self):
        self.install()
        result = self.install(LAYA_TEST_LAYAVERSION="9.9.9")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not have laya 0.3.5 installed", result.stderr)
        self.assertNotIn("runtime ready", result.stdout)

    def test_check_rejects_a_runtime_that_no_longer_matches_the_pin(self):
        self.install()
        marker = self.venv / ".megai-owned"
        marker.write_text(re.sub(r"^interpreter=.*$", "interpreter=/somewhere/else/python",
                                 marker.read_text(), flags=re.M))
        self.calls.write_text("")
        result = self.install("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match the current pin", result.stderr)
        self.assertNotIn("uv ", self.calls.read_text())

    def test_a_wrong_selected_interpreter_never_creates_a_venv(self):
        result = self.install(LAYA_TEST_PYTHONVERSION="3.10")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reports Python 3.10", result.stderr)
        self.assertIn("pins Python 3.11", result.stderr)
        self.assertNotIn("uv venv", self.calls.read_text())
        self.assertFalse(self.venv.exists())

    def test_a_wrong_reused_venv_interpreter_rebuilds_then_fails_safely(self):
        self.install()
        self.calls.write_text("")
        result = self.install(LAYA_TEST_VENV_WRONG="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("venv interpreter", result.stderr)
        self.assertIn("rebuilding", result.stdout)
        self.assertIn("uv venv", self.calls.read_text())
        self.assertNotIn("runtime ready", result.stdout)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Contracts for the opt-in context budget installer.

The installer must merge only `contextWindow` fields, refuse user-owned values,
restore the original bytes on removal and fail loudly when the installed file
does not change native model budgets. Native verification runs the real Pi model
loader offline and is skipped only when Node or the Pi package is unavailable.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
sys.path.insert(0, str(LIB))

import pi_context_budget as budget  # noqa: E402

PACKAGE_ROOT = os.environ.get("PI_PACKAGE_ROOT", "").strip()
NATIVE = bool(shutil.which("node")) and (
    bool(PACKAGE_ROOT) or bool(shutil.which("pi")))


class BudgetCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = Path(tempfile.mkdtemp(prefix="pi-context-budget-"))
        self.addCleanup(shutil.rmtree, self.temporary, ignore_errors=True)
        self.agent = self.temporary / "agent"
        self.agent.mkdir()
        self.models = self.agent / "models.json"
        self.env = dict(
            os.environ,
            HOME=str(self.temporary / "home"),
            MEGAI_HOME=str(self.temporary / "megai"),
            MEGAI_SOURCE=str(ROOT),
            PI_CODING_AGENT_DIR=str(self.agent),
        )
        Path(self.env["MEGAI_HOME"]).mkdir()
        if PACKAGE_ROOT:
            self.env["PI_PACKAGE_ROOT"] = PACKAGE_ROOT

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-B", str(LIB / "pi_context_budget.py"), *args],
                              capture_output=True, text=True, env=self.env, check=False)

    def write_models(self, data: dict) -> bytes:
        payload = json.dumps(data, indent=2).encode() + b"\n"
        self.models.write_bytes(payload)
        return payload

    def read_models(self) -> dict:
        return json.loads(self.models.read_text())


class TemplateTests(BudgetCase):
    def test_template_targets_are_positive_integers(self):
        targets = budget.template_targets()
        self.assertEqual(sorted(targets), ["openai-codex/gpt-5.6-sol", "openai-codex/gpt-6-astra"])
        for target, window in targets.items():
            with self.subTest(target=target):
                self.assertIsInstance(window, int)
                self.assertGreaterEqual(window, budget.MIN_WINDOW)

    def test_window_bounds_and_types(self):
        for value in (0, budget.MIN_WINDOW - 1, budget.MAX_WINDOW + 1):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    budget.check_window(value)
        for value in (True, "65536", None, 1.5):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    budget.check_window(value)  # type: ignore[arg-type]
        self.assertEqual(budget.check_window(budget.MIN_WINDOW), budget.MIN_WINDOW)
        for target, window in budget.resolved(131072).items():
            self.assertEqual(window, 131072, target)


class MegaiLauncherTests(unittest.TestCase):
    """`megai report`/`megai budget` must reach the installed or profile copy."""

    def test_launcher_dispatches_both_subcommands_from_either_lib_copy(self):
        temporary = Path(tempfile.mkdtemp(prefix="megai-launcher-"))
        self.addCleanup(shutil.rmtree, temporary, ignore_errors=True)
        megai = temporary / "megai"
        for directory in (megai / "lib", megai / "pi-profile/lib"):
            directory.mkdir(parents=True)
            for name in ("ui.sh", "state.sh"):
                shutil.copy2(ROOT / "lib" / name, directory / name)
        for name in ("slim_wiring.py", "pi_context_budget.py", "pi_usage_report.py"):
            shutil.copy2(LIB / name, megai / "pi-profile/lib" / name)
        env = dict(os.environ, MEGAI_HOME=str(megai), MEGAI_SOURCE=str(ROOT))
        for command in ("report", "budget"):
            with self.subTest(command=command):
                result = subprocess.run(["bash", str(ROOT / "bin/megai"), command, "--help"],
                                        capture_output=True, text=True, env=env, check=False)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("--help", result.stdout)
        installed = subprocess.run(["bash", str(ROOT / "bin/megai"), "help"],
                                   capture_output=True, text=True, env=env, check=False)
        self.assertIn("report [args]", installed.stdout)
        self.assertIn("budget [args]", installed.stdout)

    def test_launcher_reports_a_missing_script(self):
        temporary = Path(tempfile.mkdtemp(prefix="megai-launcher-empty-"))
        self.addCleanup(shutil.rmtree, temporary, ignore_errors=True)
        lib = temporary / "megai/lib"
        lib.mkdir(parents=True)
        for name in ("ui.sh", "state.sh"):
            shutil.copy2(ROOT / "lib" / name, lib / name)
        env = dict(os.environ, MEGAI_HOME=str(temporary / "megai"), MEGAI_SOURCE=str(ROOT))
        result = subprocess.run(["bash", str(ROOT / "bin/megai"), "report"],
                                capture_output=True, text=True, env=env, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not installed", result.stderr)


class InstallerTests(BudgetCase):
    def test_check_never_writes(self):
        before = self.write_models({"theme": "dark"})
        result = self.run_cli("--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("preflight ready", result.stdout)
        self.assertEqual(self.models.read_bytes(), before)
        self.assertFalse((Path(self.env["MEGAI_HOME"]) / "slim-wiring.json").exists())

    def test_apply_merges_only_context_window(self):
        self.write_models({
            "theme": "dark",
            "providers": {"deepseek": {"modelOverrides": {"deepseek-flash": {"contextWindow": 200000}}}},
        })
        result = self.run_cli("--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self.read_models()
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(data["providers"]["deepseek"]["modelOverrides"]["deepseek-flash"],
                         {"contextWindow": 200000})
        targets = budget.template_targets()
        for target, window in targets.items():
            provider, model = target.split("/")
            self.assertEqual(data["providers"][provider]["modelOverrides"][model]["contextWindow"], window)
        again = self.run_cli("--apply")
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(self.read_models(), data, "re-apply must be idempotent")

    def test_apply_without_existing_file_creates_and_removes_it(self):
        self.assertFalse(self.models.exists())
        self.assertEqual(self.run_cli("--apply").returncode, 0)
        self.assertTrue(self.models.is_file())
        self.assertEqual(self.run_cli("--remove").returncode, 0)
        self.assertFalse(self.models.exists(), "a receipt-owned created file is removed")
        self.assertEqual(self.models.exists(), False)

    def test_user_owned_window_is_preserved(self):
        before = self.write_models({
            "providers": {"openai-codex": {"modelOverrides": {"gpt-6-astra": {"contextWindow": 300000}}}},
        })
        result = self.run_cli("--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("custom contextWindow preserved", result.stderr)
        self.assertEqual(self.models.read_bytes(), before, "refusal must not write")
        self.assertEqual(self.run_cli("--remove").returncode, 0)
        self.assertEqual(self.models.read_bytes(), before, "removal never deletes a foreign value")

    def test_owned_window_can_be_reapplied_with_another_value(self):
        self.assertEqual(self.run_cli("--apply").returncode, 0)
        self.assertEqual(self.run_cli("--apply", "--window", "131072").returncode, 0)
        data = self.read_models()
        self.assertEqual(data["providers"]["openai-codex"]["modelOverrides"]["gpt-6-astra"]["contextWindow"],
                         131072)
        self.assertEqual(self.run_cli("--remove").returncode, 0)
        self.assertEqual(self.read_models(), {}, "removal leaves no owned residue")

    def test_remove_restores_unrelated_content(self):
        original = self.write_models({
            "theme": "dark",
            "providers": {"deepseek": {"modelOverrides": {"deepseek-v4-pro": {"contextWindow": 200000}}}},
            "unknown": {"keep": [1, 2, 3]},
        })
        self.assertEqual(self.run_cli("--apply").returncode, 0)
        self.assertEqual(self.run_cli("--remove").returncode, 0)
        self.assertEqual(self.models.read_bytes(), original, "removal restores the original bytes")

    def test_remove_preserves_a_foreign_modification(self):
        self.assertEqual(self.run_cli("--apply").returncode, 0)
        data = self.read_models()
        data["providers"]["openai-codex"]["modelOverrides"]["gpt-6-astra"]["contextWindow"] = 123456
        self.write_models(data)
        result = self.run_cli("--remove")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read_models()["providers"]["openai-codex"]["modelOverrides"]
                         ["gpt-6-astra"]["contextWindow"], 123456,
                         "an edited user value is not deleted as if it were ours")

    def test_malformed_models_file_is_refused(self):
        self.models.write_text("{not json")
        result = self.run_cli("--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.models.read_text(), "{not json")

    def test_non_object_provider_entry_is_refused(self):
        before = self.write_models({"providers": {"openai-codex": "nonsense"}})
        result = self.run_cli("--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.models.read_bytes(), before)

    def test_verify_without_apply_is_blocked(self):
        self.write_models({"theme": "dark"})
        result = self.run_cli("--verify")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing or stale", result.stderr)


@unittest.skipUnless(NATIVE, "native Pi package or Node unavailable")
class NativeTests(BudgetCase):
    def test_applied_budget_changes_native_model_budgets(self):
        self.assertEqual(self.run_cli("--apply").returncode, 0)
        result = self.run_cli("--verify")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("openai-codex/gpt-6-astra=65536", result.stdout)

    def test_verify_fails_on_a_tampered_installed_value(self):
        self.assertEqual(self.run_cli("--apply").returncode, 0)
        data = self.read_models()
        data["providers"]["openai-codex"]["modelOverrides"]["gpt-6-astra"]["contextWindow"] = 131072
        self.write_models(data)
        result = self.run_cli("--verify")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("preserved", result.stderr)

    def test_window_override_is_confirmed_natively(self):
        self.assertEqual(self.run_cli("--apply", "--window", "131072").returncode, 0)
        result = self.run_cli("--verify", "--window", "131072")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("gpt-5.6-sol=131072", result.stdout)


if __name__ == "__main__":
    unittest.main()

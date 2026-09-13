#!/usr/bin/env python3
"""Opt-in native skill-profile contracts and read-only snippet generator tests.

Covers optimization 1: explicit profile templates narrow only known optional
global design/mobile skills, never core/safety/a11y, and never write global
configuration. The native-package cases load the real Pi `DefaultResourceLoader`
against disposable fixtures, so the exclusion semantics are Pi's own.
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

import pi_skill_profiles as profiles  # noqa: E402

LOADER = ROOT / "tests/pi-skill-profile-loader.mjs"


def find_package_root() -> Path | None:
    configured = os.environ.get("PI_PACKAGE_ROOT", "").strip()
    if configured and (Path(configured) / "dist/index.js").is_file():
        return Path(configured)
    pi = shutil.which("pi")
    if not pi:
        return None
    candidate = Path(pi).resolve()
    for parent in (candidate, *candidate.parents):
        manifest = parent / "package.json"
        if not manifest.is_file():
            continue
        try:
            name = json.loads(manifest.read_text()).get("name", "")
        except ValueError:
            continue
        if isinstance(name, str) and name.endswith("/pi-coding-agent") and (parent / "dist/index.js").is_file():
            return parent
    return None


PACKAGE_ROOT = find_package_root()
NEEDS_NATIVE = unittest.skipUnless(
    PACKAGE_ROOT and shutil.which("node"),
    "native loader regression needs node and the installed Pi package",
)


def write_skill(base: Path, name: str) -> Path:
    path = base / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: {name}\ndescription: synthetic fixture skill {name}\n---\n# {name}\n")
    return path


class SkillProfiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="megai-skill-profiles-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.home = self.root / "home"
        self.agent = self.root / "agent"
        self.project = self.root / "project"
        self.home.mkdir()
        self.agent.mkdir()
        self.project.mkdir()

    def snapshot(self) -> dict[str, bytes]:
        return {
            str(path.relative_to(self.root)): path.read_bytes()
            for path in sorted(self.root.rglob("*"))
            if path.is_file()
        }

    def run_cli(self, *args, ok: bool = True) -> subprocess.CompletedProcess:
        result = subprocess.run(
            [sys.executable, str(LIB / "pi_skill_profiles.py"), *args],
            capture_output=True, text=True, check=False,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        )
        if ok and result.returncode != 0:
            self.fail(f"CLI failed: {' '.join(args)}\n{result.stderr}")
        return result

    def load_skills(self, *, trusted: bool, agent: Path | None = None, cwd: Path | None = None) -> set[str]:
        env = dict(os.environ, HOME=str(self.home), PI_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")
        env.pop("PI_CODING_AGENT_DIR", None)
        result = subprocess.run(
            ["node", str(LOADER), "--package-root", str(PACKAGE_ROOT),
             "--agent-dir", str(agent or self.agent), "--cwd", str(cwd or self.project),
             "--trusted", "1" if trusted else "0"],
            capture_output=True, text=True, check=False, env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload.get("diagnostics"), [], payload.get("diagnostics"))
        return set(payload["skills"])

    def apply_profile(self, profile: str, agent: Path | None = None) -> None:
        target = agent or self.agent
        (target / "settings.json").write_text(json.dumps({"skills": profiles.snippet(profile)}))

    # --- Generator logic (unit) -------------------------------------------------

    def test_exclusions_are_known_optional_only(self):
        known = profiles.OPTIONAL_DESIGN | profiles.OPTIONAL_MOBILE
        for name, excluded in profiles.PROFILES.items():
            with self.subTest(profile=name):
                self.assertTrue(set(excluded) <= known, set(excluded) - known)
                self.assertTrue(profiles.snippet(name))

    def test_profiles_never_exclude_protected_skills(self):
        for name, excluded in profiles.PROFILES.items():
            with self.subTest(profile=name):
                self.assertEqual(set(excluded) & set(profiles.PROTECTED), set())
                self.assertNotIn("a11y-audit", excluded)
                self.assertNotIn("megai-acceptance", excluded)

    def test_snippet_is_deterministic_native_exclusion_json(self):
        first = profiles.snippet("coding")
        self.assertEqual(first, profiles.snippet("coding"))
        self.assertEqual(first, sorted(first))
        for pattern in first:
            self.assertTrue(pattern.startswith("!"))
            self.assertEqual(pattern.count("/"), 0, "patterns must stay relative, not absolute paths")
        parsed = json.loads(self.run_cli("snippet", "coding").stdout)
        self.assertEqual(parsed, {"skills": first})

    def test_profiles_and_explain_are_available(self):
        listed = self.run_cli("profiles").stdout.split()
        self.assertEqual(listed, sorted(profiles.PROFILES))
        explained = self.run_cli("explain", "coding").stdout
        self.assertIn("coding", explained)
        self.assertIn("a11y", explained.lower())

    def test_scan_is_read_only_and_reports_matches(self):
        skills = self.root / "skills"
        for name in ("design-code", "megai", "a11y-audit", "appllama-app-design-skill"):
            write_skill(skills, name)
        before = self.snapshot()
        result = self.run_cli("scan", "coding", "--skills-dir", str(skills))
        self.assertEqual(self.snapshot(), before, "scan must not write")
        matched = set(json.loads(result.stdout)["matched"])
        self.assertEqual(matched, {"design-code", "appllama-app-design-skill"})

    def test_unknown_profile_fails_clearly(self):
        result = self.run_cli("snippet", "no-such-profile", ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no-such-profile", result.stderr)
        with self.assertRaises(ValueError):
            profiles.missing_exclusions("no-such-profile", [])

    def test_missing_exclusions_respect_preexisting_entries_and_order(self):
        existing = ["!design-code", "!fixture-custom"]
        missing = profiles.missing_exclusions("coding", existing)
        self.assertNotIn("!design-code", missing, "a pre-existing identical exclusion is not re-added")
        self.assertNotIn("!fixture-custom", missing)
        self.assertEqual(missing, [p for p in profiles.snippet("coding") if p not in set(existing)])
        self.assertEqual(profiles.missing_exclusions("coding", list(profiles.snippet("coding"))), [])

    # --- Native loader regression ----------------------------------------------

    def fixture_names(self) -> tuple[list[str], list[str]]:
        protected = ["megai", "megai-acceptance", "megai-task-flow", "a11y-audit",
                     "diagnosing-bugs", "git-guardrails-claude-code"]
        optional = sorted(profiles.OPTIONAL_DESIGN | profiles.OPTIONAL_MOBILE)
        return protected, optional

    def populate_global(self) -> tuple[list[str], list[str]]:
        protected, optional = self.fixture_names()
        for name in protected + optional:
            write_skill(self.agent / "skills", name)
        return protected, optional

    @NEEDS_NATIVE
    def test_native_loader_without_profile_sees_every_fixture_skill(self):
        protected, optional = self.populate_global()
        self.assertEqual(self.load_skills(trusted=False), set(protected) | set(optional))

    @NEEDS_NATIVE
    def test_native_coding_profile_narrows_optional_and_keeps_protected(self):
        protected, optional = self.populate_global()
        self.apply_profile("coding")
        self.assertEqual(self.load_skills(trusted=False), set(protected))
        self.assertFalse(set(protected) & set(optional))

    @NEEDS_NATIVE
    def test_native_force_include_reinstates_a_narrowed_skill(self):
        protected, optional = self.populate_global()
        keep = optional[0]
        settings = {"skills": profiles.snippet("coding") + ["+" + str(self.agent / "skills" / keep / "SKILL.md")]}
        (self.agent / "settings.json").write_text(json.dumps(settings))
        self.assertEqual(self.load_skills(trusted=False), set(protected) | {keep})

    @NEEDS_NATIVE
    def test_native_narrowing_applies_to_the_shared_agents_dir(self):
        _, optional = self.populate_global()
        shared = self.home / ".agents/skills"
        write_skill(shared, "tdd")
        write_skill(shared, optional[0])
        self.apply_profile("coding")
        loaded = self.load_skills(trusted=False)
        self.assertIn("tdd", loaded)
        self.assertNotIn(optional[0], loaded)

    @NEEDS_NATIVE
    def test_native_project_selection_and_trust_are_honored(self):
        protected, _ = self.populate_global()
        self.apply_profile("coding")
        write_skill(self.project / ".pi/skills", "project-extra")
        write_skill(self.project / ".agents/skills", "project-agents-extra")
        self.assertFalse((self.project / ".pi/settings.json").exists())
        untrusted = self.load_skills(trusted=False)
        self.assertNotIn("project-extra", untrusted)
        self.assertNotIn("project-agents-extra", untrusted)
        trusted = self.load_skills(trusted=True)
        self.assertIn("project-extra", trusted)
        self.assertIn("project-agents-extra", trusted)
        self.assertTrue(set(protected) <= trusted)

    @NEEDS_NATIVE
    def test_native_preexisting_exclusions_are_preserved_and_restored(self):
        protected, optional = self.populate_global()
        self.assertIn("brandkit", optional)
        write_skill(self.agent / "skills", "fixture-custom")
        path = self.agent / "settings.json"
        original = {"defaultModel": "keep", "skills": ["!fixture-custom", "!design-code"]}
        path.write_text(json.dumps(original))
        original_bytes = path.read_bytes()

        baseline = self.load_skills(trusted=False)
        self.assertTrue(set(protected) <= baseline)
        self.assertIn("brandkit", baseline, "an optional skill not yet narrowed stays loaded")
        self.assertNotIn("design-code", baseline, "pre-existing user exclusion is honored")
        self.assertNotIn("fixture-custom", baseline, "unrelated pre-existing exclusion is honored")

        newly = profiles.missing_exclusions("coding", original["skills"])
        self.assertNotIn("!design-code", newly)
        self.assertIn("!brandkit", newly)
        merged = {"defaultModel": "keep", "skills": original["skills"] + newly}
        path.write_text(json.dumps(merged))
        self.assertEqual(path.read_text().count("!design-code"), 1)
        narrowed = self.load_skills(trusted=False)
        self.assertEqual(narrowed, set(protected))
        self.assertNotIn("design-code", narrowed)
        self.assertNotIn("fixture-custom", narrowed)

        restored = [entry for entry in merged["skills"] if entry not in set(newly)]
        path.write_text(json.dumps({"defaultModel": "keep", "skills": restored}))
        self.assertEqual(path.read_bytes(), original_bytes, "restore must not drop pre-existing entries")
        self.assertEqual(json.loads(path.read_text()), original)
        self.assertEqual(self.load_skills(trusted=False), baseline)

        before = self.snapshot()
        self.run_cli("snippet", "coding")
        self.run_cli("explain", "design")
        self.assertEqual(self.snapshot(), before, "the generator never writes settings")


if __name__ == "__main__":
    unittest.main()

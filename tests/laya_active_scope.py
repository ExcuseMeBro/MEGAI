#!/usr/bin/env python3
"""Strict tracked-source scope for the Laya-only Pi decision stack.

The retired hosted decision product must not survive anywhere in the tracked tree:
no file, directory, code, test, benchmark, result, installer, document, package
identifier or descriptive reference. Git history and the untouched separate
branches are the archive; the tree itself is Laya-only.

The retired token is assembled at runtime so this guard does not reintroduce the
very name it asserts is absent from the tree it scans.
"""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Assembled fragment: the retired tool, package and descriptive prefix.
RETIRED = "je" + "v"

TEXT_SUFFIXES = {
    ".py", ".sh", ".ts", ".mjs", ".js", ".md", ".json", ".yaml", ".yml", ".toml",
    ".in", ".txt", ".lock", ".cfg", ".ini",
}
# Generated npm integrity checksums are base64 digests of unrelated packages, not
# descriptive references. Only these exact fields are exempt; package names, paths
# and every other lockfile line are still scanned.
CHECKSUM_FIELD = re.compile(r'^\s*"(integrity|resolved)":\s*"')
CHECKSUM_FILES = {"pi-defaults/package-lock.json"}

# The positive Laya surface that must exist after the cleanup.
LAYA_ASSETS = (
    "pi-skill/laya/index.ts",
    "pi-skill/laya/bridge.py",
    "pi-skill/laya/compaction.ts",
    "lib/laya_shadow.py",
    "tests/pi-laya.sh",
    "tests/pi-laya-live.sh",
)
# Retired installations that must be gone, assembled from the fragment.
RETIRED_PATHS = (
    f"pi-skill/{RETIRED}",
    f"pi-skill/{RETIRED}-compaction",
    f"lib/{RETIRED}_shadow.py",
)


def tracked_files() -> list[str]:
    """Every file in the index, i.e. the tracked tree, sorted for a stable report."""
    result = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return sorted(line for line in result.stdout.splitlines() if line)


def text_files() -> list[str]:
    found: list[str] = []
    for relative in tracked_files():
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            continue
        if path.suffix and path.suffix not in TEXT_SUFFIXES:
            continue
        found.append(relative)
    return found


def retired_offences() -> list[str]:
    """Tracked paths and content lines still carrying the retired token."""
    found: list[str] = []
    for relative in tracked_files():
        if RETIRED in relative.lower():
            found.append(f"path: {relative}")
            continue
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            continue
        if path.suffix and path.suffix not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if relative in CHECKSUM_FILES and CHECKSUM_FIELD.match(line):
                continue
            if RETIRED in line.lower():
                found.append(f"{relative}:{number}: {line.strip()[:120]}")
    return found


class ActiveScope(unittest.TestCase):
    def test_no_retired_reference_remains_in_the_tracked_tree(self) -> None:
        offences = retired_offences()
        self.assertEqual(
            offences, [],
            "the retired decision stack is still present in the tracked tree:\n"
            + "\n".join(offences),
        )

    def test_no_retired_path_remains_in_the_tracked_tree(self) -> None:
        offenders = [p for p in tracked_files() if RETIRED in p.lower()]
        self.assertEqual(offenders, [], "the retired decision stack still owns tracked paths")

    def test_laya_surface_exists_and_the_retired_install_is_gone(self) -> None:
        for relative in LAYA_ASSETS:
            with self.subTest(path=relative):
                self.assertTrue((ROOT / relative).is_file(), f"missing required asset: {relative}")
        for relative in RETIRED_PATHS:
            with self.subTest(path=relative):
                self.assertFalse((ROOT / relative).exists(), f"retired asset still present: {relative}")
        self.assertFalse(list((ROOT / "tests").glob(f"pi-{RETIRED}*.mjs")),
                         "the retired test suites must be gone")

    def test_the_installer_places_only_laya_decision_assets(self) -> None:
        installer = (ROOT / "lib/pi_model_policy.py").read_text(encoding="utf-8")
        for asset in ("extensions/megai-laya/index.ts", "extensions/megai-laya/bridge.py",
                      "extensions/megai-laya/compaction.ts"):
            with self.subTest(asset=asset):
                self.assertIn(asset, installer, "the installer must place every Laya asset")
        ledger = (ROOT / "lib/laya_shadow.py").read_text(encoding="utf-8")
        self.assertIn("laya-calls.jsonl", ledger)

    def test_the_public_tool_is_laya(self) -> None:
        tool = (ROOT / "pi-skill/laya/index.ts").read_text(encoding="utf-8")
        self.assertIn('name: "laya"', tool, "the public tool must be `laya`")
        self.assertIn("bridge.py", tool, "the tool must drive the local stdio bridge")


if __name__ == "__main__":
    unittest.main()

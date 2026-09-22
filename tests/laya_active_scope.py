#!/usr/bin/env python3
"""Strict tracked-source scope for the Laya-only Pi decision stack.

The retired hosted decision product and its vendor must not survive anywhere in the
tracked tree: no file, directory, code, test, benchmark, result, installer, document,
package identifier or descriptive reference. Git history and the untouched separate
branches are the archive; the tree itself is Laya-only.

The retired tokens are assembled at runtime so this guard does not reintroduce the
very names it asserts are absent from the tree it scans.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Assembled fragments: the retired tool/package prefix and the retired hosted vendor.
RETIRED = "je" + "v"
VENDOR = "Type" + "Safe"
TOKENS = tuple(token.lower() for token in (RETIRED, VENDOR))

# A generated npm integrity checksum is a base64 digest, not a descriptive
# reference: only that exact field value is neutralized before scanning. `resolved`
# URLs and every other line of every tracked UTF-8 file are still scanned.
INTEGRITY_FIELD = re.compile(r'"integrity"\s*:\s*"[^"]*"')
INTEGRITY_FILES = {"package-lock.json", "npm-shrinkwrap.json"}

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


def scan_offences(root: Path, files: list[str]) -> list[str]:
    """Tracked paths and content lines still carrying a retired token."""
    found: list[str] = []
    for relative in files:
        if any(token in relative.lower() for token in TOKENS):
            found.append(f"path: {relative}")
            continue
        path = root / relative
        if not path.is_file() or path.is_symlink():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if Path(relative).name in INTEGRITY_FILES:
                line = INTEGRITY_FIELD.sub('"integrity":""', line)
            if any(token in line.lower() for token in TOKENS):
                found.append(f"{relative}:{number}: {line.strip()[:120]}")
    return found


def retired_offences() -> list[str]:
    return scan_offences(ROOT, tracked_files())


class ActiveScope(unittest.TestCase):
    def test_no_retired_reference_remains_in_the_tracked_tree(self) -> None:
        offences = retired_offences()
        self.assertEqual(
            offences, [],
            "the retired decision stack is still present in the tracked tree:\n"
            + "\n".join(offences),
        )

    def test_no_retired_path_remains_in_the_tracked_tree(self) -> None:
        offenders = [p for p in tracked_files() if any(t in p.lower() for t in TOKENS)]
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


class ScopeScan(unittest.TestCase):
    """Focused coverage for the scanner's acceptance boundary on tracked bytes."""

    def scan(self, files: dict[str, str]) -> list[str]:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        for relative, text in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return scan_offences(root, sorted(files))

    def test_a_non_listed_suffix_is_still_scanned(self) -> None:
        offences = self.scan({"evidence/report.unknownext": f"the {RETIRED} tool\n"})
        self.assertTrue(offences, "a tracked file with any suffix must be scanned")

    def test_a_resolved_url_naming_the_retired_tool_is_an_offence(self) -> None:
        offences = self.scan({
            "pi-defaults/package-lock.json":
                f'    "resolved": "https://registry.example/{RETIRED}/tool.tgz",\n',
        })
        self.assertTrue(offences, "resolved URLs are scanned, not exempted")

    def test_a_generated_integrity_checksum_is_the_only_exemption(self) -> None:
        offences = self.scan({
            "pi-defaults/package-lock.json": f'    "integrity": "sha512-{RETIRED}hash==",\n',
        })
        self.assertEqual(offences, [], "only the exact integrity field is exempt")

    def test_a_tracked_reference_to_the_retired_vendor_is_an_offence(self) -> None:
        offences = self.scan({"docs/study.md": f"the {VENDOR} hosted decision tool\n"})
        self.assertTrue(offences, "the retired vendor must not be described in the tree")

    def test_a_tracked_path_naming_the_retired_vendor_is_an_offence(self) -> None:
        offences = self.scan({f"benchmark/{VENDOR.lower()}-study.md": "results\n"})
        self.assertTrue(offences, "the retired vendor must not own a tracked path")


if __name__ == "__main__":
    unittest.main()

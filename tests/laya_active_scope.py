#!/usr/bin/env python3
"""Active-scope migration guard: no hosted decision runtime survives in active code.

The replacement is only complete if nothing active can still reach the retired hosted
service or expose its tool. This scans every active source, policy, installer and
focused-test path for the retired product name, its environment variables, its
credential service and its ledger, and checks the positive side too: the Laya tool,
bridge, compaction companion and ledger helper exist, are installed under Laya asset
names, and the installer retires the legacy extension bytes it owns.

Historical measurement artifacts are deliberately out of scope: they keep their
original names and text, they are listed here explicitly, and this test asserts they
are still present and still carry the old token so a later "cleanup" cannot silently
rewrite the record the old thresholds were measured on.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Active paths: everything that can run or steer a live Pi session.
ACTIVE = (
    "install.sh", "README.md", "bin", "lib", "pi-defaults", "pi-skill",
    "prompts", "skills", "task-flow", "tests", "docs",
)
SKIP_DIRS = {".git", ".codedb", "__pycache__", "node_modules", "benchmark", "openspec"}
SKIP_FILES = {
    # Historical Jev measurements and results: immutable, never active inputs.
    "docs/pi-jev-gate.md",
    "docs/pi-jev-compaction.md",
    "tests/jev_micro_bench.py",
    "tests/jev_routing_bench.py",
    # The guard names every forbidden token and historical path by design.
    "tests/laya_active_scope.py",
    # Unrelated local JevCache helper; it has never called the TypeSafe decision API.
    "docs/jevcache.md",
    "lib/install_jevcache.sh",
    # These migration tests name retired env/endpoint tokens only to assert absence.
    "tests/pi-laya.sh",
    "tests/pi-laya-live.sh",
}
# The retired product, its credential service, its ledger and its installed assets.
FORBIDDEN = (
    re.compile(r"typesafe", re.IGNORECASE),
    re.compile(r"TYPESAFE_[A-Z_]+"),
    re.compile(r"\bjev\b", re.IGNORECASE),
    re.compile(r"JEV_[A-Z_]+"),
    re.compile(r"jev-calls"),
    re.compile(r"pi-skill/jev"),
    re.compile(r"megai-jev"),
)
# One file has to name the retired extension paths: the installer's ownership-aware
# retirement. Those exact lines are allowed, nothing else in the file may carry the
# token, and the scanner proves the retirement call site exists below.
RETIREMENT_FILE = "lib/pi_model_policy.py"
RETIREMENT_LINES = {
    '"extensions/megai-jev/index.ts",',
    '"extensions/megai-jev-compaction/index.ts",',
    'old = b"When the `jev` tool is available"',
}
# Active verification must name the removed public tool so an accidental reinstall
# fails loudly. Permit only these exact guard assertions, not arbitrary references.
ALLOWED_LINES = {
    "pi-defaults/verify.mjs": {
        "const removedTools = ['subagent', 'jev'];",
    },
    "tests/pi_defaults.py": {
        'self.assertIn("jev", removed)',
    },
    "tests/pi_model_policy.py": {
        '"When the `jev` tool is available",',
        'self.assertNotIn("When the `jev` tool is available", installed)',
    },
}
TEXT_SUFFIXES = {
    ".py", ".sh", ".ts", ".mjs", ".js", ".md", ".json", ".yaml", ".yml", ".toml",
    ".in", ".txt", ".lock",
}


def active_paths(*, include_retirement: bool = False) -> list[Path]:
    """Every active file this guard scans, sorted for a stable report."""
    found: list[Path] = []
    for entry in ACTIVE:
        base = ROOT / entry
        candidates = [base] if base.is_file() else sorted(base.rglob("*"))
        for path in candidates:
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(ROOT).as_posix()
            if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
                continue
            if relative in SKIP_FILES:
                continue
            if not include_retirement and relative == RETIREMENT_FILE:
                continue
            if path.suffix and path.suffix not in TEXT_SUFFIXES:
                continue
            found.append(path)
    return sorted(set(found))


def offences(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    relative = path.relative_to(ROOT).as_posix()
    found: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for pattern in FORBIDDEN:
            if pattern.search(line) and line.strip() not in ALLOWED_LINES.get(relative, set()):
                found.append(f"{relative}:{number}: {line.strip()[:120]}")
                break
    return found


class ActiveScope(unittest.TestCase):
    def test_no_hosted_decision_path_remains_active(self) -> None:
        offences_found: list[str] = []
        for path in active_paths():
            offences_found.extend(offences(path))
        self.assertEqual(offences_found, [], "the retired hosted decision path is still active")

    def test_the_installer_only_names_the_retired_assets_to_retire_them(self) -> None:
        path = ROOT / RETIREMENT_FILE
        text = path.read_text(encoding="utf-8")
        self.assertIn("LEGACY_ASSETS", text, "the retired asset list must be explicit")
        self.assertIn("plan.retire(root / relative)", text, "owned legacy bytes must be retired")
        for line in text.splitlines():
            with self.subTest(line=line.strip()[:80]):
                if any(pattern.search(line) for pattern in FORBIDDEN):
                    self.assertIn(line.strip(), RETIREMENT_LINES,
                                  "only the retirement tuple may name the retired assets")

    def test_laya_surface_exists_and_the_old_tool_is_gone(self) -> None:
        for relative in ("pi-skill/laya/index.ts", "pi-skill/laya/bridge.py",
                         "pi-skill/laya/compaction.ts", "lib/laya_shadow.py",
                         "tests/pi-laya.sh", "tests/pi-laya-live.sh"):
            with self.subTest(path=relative):
                self.assertTrue((ROOT / relative).is_file(), f"missing required asset: {relative}")
        self.assertFalse((ROOT / "pi-skill/jev").exists(), "the retired tool directory must be gone")
        self.assertFalse((ROOT / "pi-skill/jev-compaction").exists())
        self.assertFalse((ROOT / "lib/jev_shadow.py").exists())
        self.assertFalse(list((ROOT / "tests").glob("pi-jev*.mjs")), "the retired suites must be gone")

    def test_the_active_tool_bridge_and_ledger_are_laya(self) -> None:
        tool = (ROOT / "pi-skill/laya/index.ts").read_text(encoding="utf-8")
        self.assertIn('name: "laya"', tool, "the public tool must be `laya`")
        self.assertIn("bridge.py", tool, "the tool must drive the local stdio bridge")
        self.assertIn('name: "sift"', tool, "the screen stays registered in the same extension")
        installer = (ROOT / "lib/pi_model_policy.py").read_text(encoding="utf-8")
        for asset in ("extensions/megai-laya/index.ts", "extensions/megai-laya/bridge.py",
                      "extensions/megai-laya/compaction.ts"):
            with self.subTest(asset=asset):
                self.assertIn(asset, installer, "the installer must place every Laya asset")
        ledger = (ROOT / "lib/laya_shadow.py").read_text(encoding="utf-8")
        self.assertIn("laya-calls.jsonl", ledger)

    def test_historical_artifacts_are_preserved_but_inert(self) -> None:
        history = {
            "tests/jev_micro_bench.py": "jev",
            "tests/jev_routing_bench.py": "jev",
            "docs/pi-jev-gate.md": "jev",
            "docs/pi-jev-compaction.md": "jev",
        }
        for relative, token in history.items():
            with self.subTest(path=relative):
                path = ROOT / relative
                self.assertTrue(path.is_file(), "a historical artifact was removed")
                self.assertIn(token, path.read_text(encoding="utf-8").lower(),
                              "a historical artifact was rewritten")
        for path in active_paths():
            if path.relative_to(ROOT).as_posix() in SKIP_FILES:
                continue
            text = path.read_text(encoding="utf-8")
            for name in history:
                with self.subTest(path=path, reference=name):
                    self.assertNotIn(Path(name).stem, text,
                                     "active code must not depend on a historical artifact")


if __name__ == "__main__":
    unittest.main()

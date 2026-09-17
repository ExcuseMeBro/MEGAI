#!/usr/bin/env python3
"""Materialize reviewer-visible case repos from the frozen base snapshots + patches.

The delivered `cases/case-*/base/**` snapshot plus `cases/case-*/change.patch`
are the artifacts of record.  This script only replays them into plain Git
repos under `work/` so a reviewer can run `git diff base head` or
`ocr delegate preview --from base --to head`.  It carries no ground truth.

Only the standard library is used.  Committer identity and timestamps are
fixed so the produced SHAs are stable across machines.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "cases"
WORK = ROOT / "work"

DATE = "2000-01-01T00:00:00+00:00"
ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "fixture",
    "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
    "GIT_COMMITTER_NAME": "fixture",
    "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    "GIT_AUTHOR_DATE": DATE,
    "GIT_COMMITTER_DATE": DATE,
}


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env=ENV,
    )
    return result.stdout.strip()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def case_files(case: Path) -> list[str]:
    base = case / "base"
    return sorted(str(p.relative_to(base)) for p in base.rglob("*") if p.is_file())


def prepare(case_id: str) -> dict[str, object]:
    case = CASES / case_id
    repo = WORK / case_id
    if repo.exists():
        shutil.rmtree(repo)
    repo.mkdir(parents=True)
    shutil.copytree(case / "base", repo, dirs_exist_ok=True)

    git(repo, "init", "-q", "-b", "base")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    base_sha = git(repo, "rev-parse", "HEAD")

    git(repo, "checkout", "-q", "-b", "candidate")
    subprocess.run(
        ["git", "-C", str(repo), "apply", str(case / "change.patch")],
        check=True, capture_output=True, text=True, env=ENV,
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "candidate")
    head_sha = git(repo, "rev-parse", "HEAD")

    assert git(repo, "rev-parse", "base") != git(repo, "rev-parse", "candidate")
    return {
        "id": case_id,
        "repo": str(repo.relative_to(ROOT)),
        "base_ref": "base",
        "head_ref": "candidate",
        "base_commit": base_sha,
        "head_commit": head_sha,
        "base_snapshot": str((case / "base").relative_to(ROOT)),
        "patch": str((case / "change.patch").relative_to(ROOT)),
        "files": case_files(case),
        "patch_sha256": file_sha256(case / "change.patch"),
    }


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    case_ids = sorted(p.name for p in CASES.iterdir() if p.is_dir())
    manifest = {
        "schema": 1,
        "note": "Reviewer-visible. No labels, defects or scoring information.",
        "brief": "briefs/review-brief.md",
        "cases": [prepare(case_id) for case_id in case_ids],
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

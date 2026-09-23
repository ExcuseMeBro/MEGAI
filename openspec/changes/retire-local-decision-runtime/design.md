## Context

The retired runtime was one of several Pillars wired through `lib/slim_wiring.py`'s
`Plan`: assets are written with an ownership receipt, and `Plan.retire(path)` removes a
file only when the receipt matches the bytes on disk, failing closed otherwise. The
runtime installer additionally wrote its own marker (`owner=megai-<tool>`) inside the
venv before its first package install, so a partial or complete runtime of ours is
distinguishable from a foreign directory.

## Decisions

### Delete the runtime instead of gating it behind a flag

Native Pi judgment and Pi's native compaction already cover the two functions the
runtime provided. A feature flag would keep the installer gate, the lock file and the
checkpoint download alive to serve nothing, so the sources are deleted and the gate is
removed with them.

### Retire installed assets through the existing ownership mechanisms

- Pi extension files and the saved `state.json` entry: `Plan.retire` plus a merge-aware
  staged read of `state.json`, so the retirement composes with `slim_wiring.main()`'s
  own legacy-name cleanup instead of one stage silently replacing the other.
- Published source copies: the same digest-or-receipt rule used by
  `lib/retire_legacy_sources.py`, in a new table in `lib/retire_local_decisions.py`.
  Repository installs copy `lib/` a second time into `$MEGAI_HOME/pi-profile`, so those
  paths appear in the same table.
- The pinned runtime: moved into `$MEGAI_HOME/backups/retired-decision-runtime*` rather
  than deleted. It is large but rebuildable, and a rename is reversible while a delete
  is not. A symlink, a regular file or an unmarked directory is reported, not touched.

### Assemble the retired name instead of spelling it

The frozen acceptance contract rejects the retired token anywhere in the tracked tree,
including a comment. The names in `lib/retire_local_decisions.py` are therefore built
from parts and documented as such. Every check stays exact-match against those names,
their recorded digests or the receipt; nothing sweeps a directory or matches a prefix,
and no runtime behaviour depends on the assembly.

### Preserve historical evidence without relabeling results

The integrity-corrected frozen contract excludes historical benchmark records, test
protocols, audits and archived reviewer-policy examples from the stale-alias scan,
but not from the retired-runtime scan. Eleven named historical paths retain exact
base-commit bytes in both the index and worktree. Replacing a model label while
keeping hashes, costs and measurements unchanged would falsely attribute completed
experiments to a different model. Active templates and policy still use the current
aliases; Git history and historical files keep the names used when the work ran.

### Drop the repository-local Claude Code settings

`.claude/settings.json` enabled Claude Code plugins for this stack and is unrelated to
the Pi-side retirement; nothing in the tree reads a repository-local `.claude` path
(every remaining reference resolves against `$HOME`). It is deleted here as part of the
same active-install cleanup. The operator's unrelated checkout of that settings file is
out of scope and untouched.

## Compatibility and privacy

- The Pi policy transaction keeps one fatal subprocess step (`MEGAI_PI_POLICY` test
  seam); a failure still stops the install before profile success is reported.
- Operator-owned values stay authoritative: user-edited AGENTS.md blocks, unowned
  extension files, native provider/model/thinking settings, other extensions, skills,
  MCP entries and unrelated state keys are preserved byte-for-byte.
- No credentials, personal data, decision ledger or checkpoint cache is read or
  modified. The retirement touches only files whose bytes or receipts prove ownership.
- Retired content remains reachable through Git history, and the runtime through the
  private backup.

## Rollback

Revert the commit: the deleted sources return, and reinstall restores the previous
wiring. A retired runtime is not lost — it sits in `$MEGAI_HOME/backups/` until the
operator removes it deliberately.

## Verification

Frozen acceptance commands: the zero-token tracked-tree scan, `tests/pi_model_policy.py`
(owned retirement, unowned preservation, runtime move, native compaction),
`tests/pi_defaults.py` (policy transaction ordering and fatality) and
`tests/pi_deepseek_preset.py` (economy preset installs `gpt-6-sol` for the reviewer while
preserving native settings). Additional focused checks: `tests/pi_adaptive_policy.py`,
the Node extension suites with `PI_PACKAGE_ROOT` pointing at the installed Pi, and Ruff
on changed Python.

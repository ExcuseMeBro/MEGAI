# Review brief — four candidate changes

You are the independent reviewer. Four small repositories each contain one
candidate change on top of a base revision. Review every case.

## Scope (identical for every review arm)

- `manifest.json` lists the four cases, their base/head refs and their files.
- `work/case-a` … `work/case-d` are plain Git repositories.
  `git -C work/case-<id> diff base candidate` is the proposed change; the full
  file and its surrounding module context are checked out in the worktree.
- `cases/case-<id>/base/` is the frozen base snapshot and
  `cases/case-<id>/change.patch` the same diff, for reference.
- Only `manifest.json`, `briefs/`, `cases/**` and `work/**` are in scope.
  Do not read, execute, or modify anything else in the benchmark tree
  (in particular not `private/` or any creator/agent state), and do not edit
  the reviewed repositories.

### Case identity
Case ids (`case-a` … `case-d`) are deliberately neutral. Nothing outside the
referenced source and diffs tells you which change, if any, is defective —
report what you can defend from the code alone.

## What to judge

For each case, judge the candidate change against the normal intended
behaviour of the code it touches. The modules are extracted from the MEGAI
project (Python 3.14, standard library only); behaviour depends only on the
code in the repository.

- `lib/asana_plane_import.py` — a fail-closed Asana→Plane importer. It writes
  through a paginated HTTP client, verifies every owned write by reading it
  back, and maps source identities (member e-mail → Plane member id) before
  use. Pagination must terminate exactly when the API signals it, and a
  readback must be rejected whenever it does not match what was submitted.
- `lib/acceptance_gate.py` — a fail-closed local acceptance evidence gate. A
  snapshot must deterministically fingerprint the complete source state that
  evidence was approved against, so that a later replay cannot reuse stale
  evidence.

Report defects the candidate change introduces or fails to remove. A change
that is fully correct is a valid result.

## Output

Emit a single JSON array of findings, then one verdict line per case:

```json
[
  {"case": "case-a", "severity": "high", "path": "lib/x.py", "line": 123,
   "issue": "...", "evidence": "input/state that triggers it", "confidence": "high"}
]
```

```
case-a: FINDINGS
case-b: CLEAN
case-c: CLEAN
case-d: FINDINGS
```

Severities: `critical`, `high`, `medium`, `low`. Use `line` as the new-side
line number in the candidate revision. Report only what you are confident
about; a false alarm costs more than a silent minor nit.

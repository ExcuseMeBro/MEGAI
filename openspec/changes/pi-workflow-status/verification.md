## Verification plan

`openspec validate pi-workflow-status` checks planning completeness only; it is
never implementation proof. Implementation proof is the real CLI regression
file, which mocks the documented Paseo read schemas rather than imagined fields.

| Requirement | Evidence |
| --- | --- |
| Read-only project-scoped status command | `tests/pi_workflow_status.py` runs the real CLI; asserts JSON keys, per-item blocked at exit 0, and `BLOCKED:` + no stdout on fatal failures |
| Fetch-fresh repository inventory | disposable monorepo/bare-`origin` fixture; remote-advanced/stale-local-tracking test, `show-ref` unchanged, remoteDev fresh, missing-remote multi-repo partial failure |
| Branch, worktree and pending-delivery inventory | clean unpublished task tip in `pendingDelivery`; extra preserve branch; detached HEAD; ignored untracked data and a locked worktree block eligibility though normal status is clean |
| Fail-closed ownership and scoped workspace observation | canonical project-id/common-dir mapping, ambiguous identity, foreign requested workspace, `--workspace` keeps full repository inventory, malformed payload |
| Affirmative release proof for cleanup | archived+known-idle matching-identity eligible case; no-agent blocked; idle-not-archived, running, pending-permission, unknown-status (even when archived) and current-runner blocked; local primary never eligible |
| Ref-race guard | hook moves a workspace branch during the Paseo pass; candidate blocked and never eligible |
| Existing commands preserved | unchanged `context` baseline assertion in the same file |

## Red receipt (Phase 1, before product edits)

Command: `python3 -m unittest tests.pi_workflow_status -v`.
Result: RED — `Ran 19 tests … FAILED (failures=18)`; the CLI rejects `status`
with argparse `invalid choice: 'status'` (exit 2) for all 18 status tests while
`test_context_baseline_unchanged` passes. Setup proof: the corrected mono
fixture reports an empty `git status --porcelain` and tracks
`.pi/project.json`. Product code stays unedited until the parent records the
formal red receipt and approves the criteria hash; this document does not claim
a frozen contract.

## Green proof (Phase 2, after implementation)

Frozen regression file (hash `183bffff…e2131c`, unchanged in Phase 2):
`python3 -B -m unittest tests.pi_workflow_status -v` → `Ran 19 tests … OK`
(exit 0), log `/tmp/m88-green2.log`. `test_status_is_read_only_for_named_refs`
asserts named refs and worktree HEADs are unchanged across a `status` run.

Supplementary checks:

- `ruff check --no-fix --no-fix-only --force-exclude --no-cache -- pi-defaults/workflow.py tests/pi_workflow_status.py` → `All checks passed!`, log `/tmp/m88-ruff.log`.
- `python3 -B -m unittest tests.pi_fast_workflow -v` → `Ran 9 tests … FAILED (failures=1)`, log `/tmp/m88-fast.log`. This is a **pre-existing, unrelated baseline failure**: `test_adaptive_keeps_economy_routing_clauses_under_char_budget` reports `ADAPTIVE.md` at 12839 chars over a 9600 ceiling; `pi-skill/ADAPTIVE.md` is byte-identical at `HEAD` (12855 bytes) and is not touched by this change, and `tests/pi_fast_workflow.py` does not import `pi-defaults/workflow.py`. No regression is introduced.
- `openspec validate pi-workflow-status` → `Change 'pi-workflow-status' is valid` (structural only, never implementation proof).

Independent GPT review of the exact diff is required before handoff. Actual
archive/cleanup remains a separate parent gate; `archiveEligible` is a report,
not authorization, and the documented `agent inspect` schema proves no unseen
terminal/service release.

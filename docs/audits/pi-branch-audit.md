# Pi branch audit — MEGAI-59

Baseline: `83f2b4586881a01c014d96c71523ded5bf9c572d`. Scope: active queue,
acceptance, provider/workspace guards, installation/ownership code and the user's
explicit request to remove the experimental Capy pack. This is a targeted source
and local-fixture audit, not a full dependency penetration test or a claim that
all branch behavior is flawless.

## Confirmed fixes

| Finding | Reproduction | Change |
| --- | --- | --- |
| Queue grant can already be expired when returned after slow target preflight. | Controlled clock: claim begins at 100, successful preflight ends at 110, one-second grant expires at 101. | Start the lease after preflight, under the same SQLite reservation transaction. A fresh claim expires at 111 and can immediately heartbeat. No expired-owner stealing or automatic replay. |
| Single-row queue lookup parses unrelated retained history twice. | 201 terminal rows cause 402 JSON decodes in `public(row(id))`. | Indexed `WHERE id=?` lookup and no history read for nonqueued status. Same fixture now decodes one row; `status --id` uses this path. Full queue listing and queued FIFO/dependency evaluation retain their semantics. |
| Unwanted experimental pack remains in the Pi distribution. | 19 tracked `capy/` files and an active root README pointer. | Remove the pack and pointer at the user's request. Retain Git history, the historical consolidation audit and separate benchmark worktree; do not delete other refs or promote main. |

The decode count is a deterministic work measurement, **not** an end-to-end
latency claim. The removal reduces distribution clutter; the pack was not an
active startup dependency, so no startup speedup is claimed.

## Verification

Frozen criteria and raw red/green receipts live outside source under
`~/.megai/acceptance/megai-59/`, linked from Plane item `AS4DABD7BE-59`.

- `python3 -B tests/integration_queue_audit.py`: two real baseline assertion
  failures, then two passes with unchanged assertions.
- `python3 -B tests/integration_queue.py`: public CLI suite covers 16 scenarios,
  including concurrent claims, FIFO, cancellation, expired tokens, partial
  integration/recovery, dirty checkouts and unchecked target refs.
- `python3 -B tests/pi_distribution_scope.py`: removed pack/pointer and retained
  supported runtime sources.
- Non-mutating Ruff on changed Python, and `git diff --check`.
- Audit baseline checks: acceptance gate 23, directory acceptance 28, acceptance
  flow 11 and Headroom wiring 14 tests passed. Native provider/workspace tests
  also passed, including active streaming, managed provenance and scoped writers.
  Native tests require `PI_PACKAGE_ROOT` pointing to the installed Pi package;
  initial missing-env errors were setup errors, not regressions. An aggregate
  acceptance command hit its operational timeout; the remaining suites passed
  when run separately. An interrupted queue rerun is not counted as a pass.

Final candidate receipts and an independent Pi review, not this document alone,
authorize delivery. The parent must recheck the current target and reserve it
through the shared integration queue. No host installation is part of this task.

## Rejected findings and remaining limits

- Installer scout's proposed preflight `NameError` is contradicted by source:
  `journal` is initialized before the transaction's `try`; preflight runs before
  that `try`. Its legacy PATH rejection claim is also contradicted by the
  explicit `(block, legacy)` acceptance check. No speculative fixes applied.
- Filesystem preflight is not an adversarial sandbox against a concurrent
  privileged writer replacing directories. No exploit or additional confirmed
  security defect was established in this audit.
- A pre-existing policy test fails at `tests/slim_distribution.py:849` because
  it expects the phrase `persistent branch` in the task-flow skill. Parent
  reproduced this with `Slim.test_policy_guards_and_public_branch` and handed
  the overlap to concurrent MEGAI-60, which owns policy text/tests and local
  installation. This task does not claim the entire repository suite is green.
- No remote/provider requests, host configuration changes, daemon/index startup
  or dependency upgrades were used as acceptance. Existing credentials, models,
  user settings and the shared `dev` checkout remain untouched.

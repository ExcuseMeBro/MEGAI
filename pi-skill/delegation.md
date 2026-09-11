# MEGAI execution and subagent policy

## Five-minute checkpoint — every task, including direct parent work

Record task/slice start time and acceptance before execution. If expected work
exceeds 5 minutes (300 seconds), split it before starting into independently
verifiable subtasks, each targeting at most five minutes. Count elapsed wall time,
including model/tool waits; changing models does not reset the slice clock.
At each control return check elapsed time. At the deadline, checkpoint evidence,
completed acceptance and the blocker; parent decomposes the remaining work rather
than continuing the same open-ended attempt. Children return this checkpoint to
the parent immediately; only the parent replans, delegates or updates Plane.

Keep the same Plane parent identity; parent records the slice acceptance there.
Parallelize only independent scopes with isolated writers, initially at most two
children; otherwise execute smaller slices directly. Give each child a deadline,
owned paths and a smallest observable result. Prefer completion notifications;
any supported wait/timeout must fit the remaining slice budget where safe.
Preserve in-flight non-interruptible writes: report the overrun and reconcile their
outcome before proceeding, rather than killing or replaying a mutation. This is a
mandatory agent checkpoint, not a runtime watchdog or a five-minute total-delivery
guarantee. Re-slicing must change scope or strategy, not just restart the clock.

## Model choice

Use the user's configured providers, models and thinking preferences. MEGAI adds
no model allowlist. Select an available model suitable for
the task; verify its exact identity and supported thinking before sending context.
Never silently change the parent's model, credentials or provider catalog.

Before selecting a delegated role, read `megai-roles.json` in the Pi agent directory
(`PI_CODING_AGENT_DIR`, otherwise `~/.pi/agent`) when present. Its roles are the
user-selected model/thinking defaults; explicit task choices override them. Missing
role configuration retains normal model choice, not an implicit preset. This is
parent-consumed policy data, not automatic dispatch or an allowlist; it is not a sandbox.
Use direct parent tools for bounded work; never require all four roles. Scout,
planner and reviewer are read-only; a worker gets only its assigned managed paths.
Read-only checks use `python3 -B` and Ruff with
`--no-fix --no-fix-only --force-exclude --no-cache`; avoid cache-producing checks.

## Immediate escalation — model failure or stalled progress

A model-specific error, timeout or reasoning dead-end returns immediately to the
parent with the exact error, attempted model, elapsed time, changed paths and test
evidence. The parent may continue on a suitable, available alternative permitted by the
user's configuration. Avoid a same-model retry loop or idle backoff: choose a
materially different approach and at most two escalation transitions per slice.
Keep attempted-model history across re-slicing of the same blocker; never cycle
back to a failed model. If alternatives are unavailable, report the blocker or
continue a smaller safe non-model-dependent step.

Auth/permission failures, shared quota/outages and uncertain writes are not fixed
by model hopping: report them, preserve evidence and reconcile writes read-only.
An ordinary code/test failure needs a focused diagnosis, not automatic rerouting.
Confirm the old writer has stopped before transferring write authority; retain
its diff and completed tests. Reuse a healthy child for refinements; replace a
failed child only for the bounded escalation, with the existing evidence rather
than restarting discovery. Preserve required tests, independent review and user
approval boundaries; never trade data integrity or claim unmeasured speed gains.

## Verified launch

Use structured Paseo `create_agent` with the selected provider/model and supported
thinking settings. First send only a neutral READY prompt; verify the returned
harness, exact model and effective thinking via agent status before sending task
context. Also confirm native Pi model/thinking: inspect the session's model and
thinking-level entries, or request only `PI_PROVIDER`, `PI_MODEL` and
`PI_REASONING_LEVEL` through a second neutral runtime-check prompt. Paseo labels
alone can misreport a clamped thinking level. If native evidence is unavailable,
stop as BLOCKED; on mismatch cancel the child and report the blocker. Re-check restored
agents before reuse. Children never delegate or mutate Plane. Writers use managed
isolated worktrees; direct parent tools suffice for bounded work. Main promotion
still needs separate explicit approval.

MEGAI does not install a model-selection tool-call guard. User permissions,
provider availability and project rules still apply to agent launches.

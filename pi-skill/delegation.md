# MEGAI execution and subagent policy

## Task scope and progress

Define acceptance and the smallest observable result before execution. Split work
when scope, dependencies or verification benefit, not according to a fixed duration.
Continue while making progress toward acceptance; report blockers promptly. Use
task-specific deadlines only when required by the user or operational constraints.

Keep the same Plane parent identity; only the parent replans, delegates or updates
Plane. Parallelize only independent scopes with isolated writers, initially at most
two children; otherwise use direct parent tools. Give each child owned paths,
authority and observable acceptance. Prefer completion notifications.
Preserve in-flight non-interruptible writes and reconcile their actual outcome
before proceeding, rather than killing or replaying a mutation. Operational tool
timeouts and queue leases remain separate from task decomposition.

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
materially different approach and at most two escalation transitions per blocker.
Keep attempted-model history for the same blocker; never cycle
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
agents before reuse. Children never delegate or mutate Plane. Follow the hybrid
`agent-worktree-lifecycle`: Git writers use one managed worktree per affected repo
with the same task branch/slug under the existing umbrella project; non-Git configuration
writers use scoped local workspaces and private backups. All affected repos require
acceptance before dev integration; reserve target resources through `megai queue`.
Main promotion still needs separate explicit approval of the exact commit vector.

MEGAI does not install a model-selection tool-call guard. User permissions,
provider availability and project rules still apply to agent launches.

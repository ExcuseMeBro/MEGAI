# MEGAI execution and subagent policy

Load only for actual delegation or model-error escalation. Routine Pi work follows
`megai` with one parent and self-review; delegation is not a required stage.
With an explicitly selected `economy` preset, use DeepSeek planning/implementation
roles first and reserve GPT for guarded review or a concrete model-specific failure.
Role preferences do not require launching agents: a healthy DeepSeek parent does its
own routine work. Keep GPT review bounded to the diff, criteria and test evidence.

## Task scope and progress

Define acceptance and the smallest observable result before execution. Split work
when scope, dependencies or verification benefit, not according to a fixed duration.
Continue while making progress toward acceptance; report blockers promptly. Use
task-specific deadlines only when required by the user or operational constraints.

Keep the same Plane parent identity; only the parent replans, delegates or updates
Plane. Parallelize only independent scopes with isolated writers, initially at most
two children; otherwise use direct parent tools. Give each child owned paths,
authority and observable acceptance. Use notification-driven waiting below.
Preserve in-flight non-interruptible writes and reconcile their actual outcome
before proceeding, rather than killing or replaying a mutation. Operational tool
timeouts and queue leases remain separate from task decomposition.

## Notification-driven waiting (Pi + Paseo)

1. At `create_agent`, set `notifyOnFinish: true` explicitly. Keep the neutral
   READY launch and identity verification below before task context. At every
   `send_agent_prompt`, including refinements, set `background: true` and
   `notifyOnFinish: true`; retain the returned agent/run identity. Describe the
   connected tool first if its schema differs; do not assume caller defaults.
2. Continue only independent work. When the next step depends on a child, end the
   parent turn with a short pending status and let the completion notification
   resume it. This is a yield, not task completion: keep the Plane item In Progress
   and the child's workspace intact. Do not keep the turn alive with shell
   `sleep`, repeated status/activity/file reads, or a heartbeat/scheduled poll.
3. On notification, match it to the expected child and current dispatch; read the
   result/evidence once when needed. Finished, errored and permission-needed events
   are distinct: idle/finished alone is not acceptance. Reconcile errors or request
   the required permission without automatically approving it. Ignore stale or
   duplicate events for already-consumed work; never replay a task just to wait.
4. Notifications require a supported delivery path to this parent; the flag alone
   is not proof. If unavailable, use an advertised native wait tool, or select
   `background: false` on the initial `send_agent_prompt` to use its synchronous
   result. There is no assumed Paseo `wait_agent` API. For an already-running child,
   never resend its prompt as a wait: one diagnostic status/activity read may
   reconcile a missing event; if still pending with no supported wait, report the
   delivery blocker and yield. On resume, reconcile that same child before reuse.

These rules cover child-result waiting, not test timing, provider inactivity
protection or integration-queue lease/claim semantics; those contracts stay intact.
MEGAI supplies instructions here, not a runtime sleep interceptor or notification
transport. Standalone Pi needs its connected adapter to deliver completion events.

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

## DeepSeek-first subagent fallback

For delegated planner/scout/worker roles whose configured primary is
`deepseek/deepseek-flash` (high), keep DeepSeek first. After a confirmed
provider/model-specific failure, timeout, reasoning dead-end or unavailable
primary, use this exact chain, all at high thinking:
`deepseek/deepseek-flash` -> `openai-codex/gpt-5.6-luna`.
Explicit task model/provider restrictions override this preference; do not replace
other configured primaries or the independent reviewer's configured model.
A confirmed provider-specific insufficient balance or unavailability permits the
next user-approved provider in this chain; do not stop at the first failed provider
while a safe, configured alternative remains.

This is parent-driven **subagent-only** routing, not a Pi runtime failover setting.
Keep the parent model, native startup defaults, model-thinking settings, credentials
and provider catalog unchanged. Keep primary roles in `megai-roles.json`; do not
reapply a preset merely to enable this fallback, because `--preset` also changes
native startup defaults.

Apply the escalation and verified-launch rules below to every fallback. Record the
reason and failed identity, reconcile writes and confirm the old writer has stopped
before a replacement. Verify the next model's availability and native model/thinking
before sending task context; missing evidence or a mismatch remains BLOCKED. At most
two transitions per blocker; never cycle back to a failed primary or start
speculative standby agents. New independent tasks start with the configured primary
unless its balance is already known to be exhausted in this parent session (below);
a healthy fallback child may handle the same task's refinements. Auth/permission
failures, shared quota/outages and uncertain writes still require reconciliation,
not blind fallback. Use completion notifications, not sleep polling.

### Confirmed DeepSeek balance exhaustion

A terminal child **provider** error with `model=deepseek/deepseek-flash`,
`stopReason=error`, HTTP `402` and message `Insufficient Balance` is an explicit
fallback trigger, even when the payload says `type=unknown_error` and
`code=invalid_request_error`. Classify the actual provider response, not those
broad type/code fields alone or a quoted error in repository/tool/test output.

For this confirmed case, the parent routes the unfinished subagent task to the next
provider in the chain — `openai-codex/gpt-5.6-luna` (high) — after the stopped-writer
and verified-launch checks. Notify the user briefly and continue without requesting
the same fallback
approval again, retrying DeepSeek, sleeping or waiting for a balance top-up. Carry
the task's existing diff/evidence and resume only unfinished work; never replay
uncertain mutations. Keep a confirmed-unavailable provider marked unavailable in this
parent session so additional eligible subagents skip it while the failure persists.
Return to the configured primary only after the user confirms funding is restored or
a separately authorized readiness check succeeds; do not poll the balance.
This is session-local routing knowledge, not a change to native defaults or roles.

Advance the chain only on an eligible confirmed provider/model-specific failure,
including a known provider-specific balance failure. Unresolved `401`/`403`, generic
`429`, shared quota/outages, unknown `402` responses and uncertain writes are BLOCKED
until reconciled, not fallback triggers. Do not cycle providers, buy credits or
modify credentials. If `openai-codex/gpt-5.6-luna` also fails, stop as BLOCKED: the
current parent does not silently implement in its place and the chain does not
restart. If no eligible chain provider is available, report BLOCKED.

A fallback plan's advertised concurrency is capacity, not a required
fanout. Keep the existing independent-scope/one-writer rules and initial two-child
limit. Do not rewrite native context limits or infer available quota from plan copy;
text, image and speech may share the account quota.

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
The confirmed DeepSeek `402` balance-exhaustion exception above permits the named
cross-provider fallback; it does not waive write reconciliation or authorization.
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
context. Verify the Paseo harness is `pi` separately from the model provider.
The status-provided session handle must identify the same current native session ID.
Match the provider-qualified status model to native `model_change.provider` and
`model_change.modelId`: `deepseek/deepseek-flash` means `deepseek` + `deepseek-flash`,
not `pi` + `deepseek-flash`. Match native `thinking_level_change.thinkingLevel` to the
effective thinking reported in status. When these current records agree, prefer those records
and do not run a second neutral runtime-check model prompt; identity is already proven. If
those native records are missing, stale, ambiguous, or come from a restored
session on a different branch, fall back to the second neutral runtime-check
prompt that requests only `PI_PROVIDER`, `PI_MODEL` and `PI_REASONING_LEVEL`. Do
not rely on Paseo labels alone: a clamped thinking level can be misreported.
If native evidence is still unavailable, stop as BLOCKED; on mismatch cancel the
child and report the blocker. Re-check restored agents before reuse. Children
never delegate or mutate Plane. Follow the hybrid `agent-worktree-lifecycle`:
Git writers use one managed worktree per affected repo with the same task
branch/slug under the existing umbrella project; non-Git configuration writers
use scoped local workspaces and private backups. All affected repos require
mode-appropriate acceptance before dev integration; guarded Pi tasks require the
formal gate, routine tasks retain actual tests and self-review. Reserve target
resources through `megai queue`.
Main promotion still needs separate explicit approval of the exact commit vector.

MEGAI does not install a model-selection tool-call guard. User permissions,
provider availability and project rules still apply to agent launches.

## Parent-side provider timeout, stall and replacement

Moved out of the always-loaded `AGENTS.md` so the parent pays for it only when it
delegates or escalates.

A confirmed DeepSeek provider timeout means no resend to DeepSeek and no second long
wait: use the approved `openai-codex/gpt-5.6-luna` (high) fallback once and report the
model that actually ran. A native wait timeout alone is not a provider failure.
For a suspected stall, do one bounded native wait of at most 180 seconds and inspect
progress/errors once — never repeated 600-second waits and never routine polling. If
no model or tool progress is observable in that interval while only a provider
response is pending, the owning parent may abort that request and use the fallback.
Never interrupt a progressing stream, an active tool or test, or a pending permission.

Before replacement: the original writer is idle, with no queued work and no pending
permission, its diff has been inspected and preserved, and the replacement runs in the
same task, workspace and cwd. With no safe in-place switch, allow exactly one
replacement after the original is quiescent — never two writers, and never take over
another parent's child. A fallback failure is reported as a blocker with no retry and
no fan-out. Keep the parent model and thinking level unchanged, and keep the required
review.

Runtime timeout settings bound SDK requests and idle transport, not total task
duration; keep-alive streaming can outlive them, so they are not a hard wall-clock SLA.

## Codex Spark helper (approved, blocked)

Preferred for bounded helper work — scoped code reading/discovery, log analysis, small
independent low-risk fixes with focused tests — through native Paseo's Pi provider, not
a separate runner:

```
paseo agent run --background --provider pi --model openai-codex/gpt-5.3-codex-spark \
  --thinking medium --workspace EXISTING_ID --cwd EXPLICIT_PATH --title TITLE PROMPT
```

`medium` is Spark's verified native default and the parent selection is unchanged.
Verify availability and native completion/control support before each new delegation
unless already verified in this session. Spark is text-only: no images.

Give only necessary paths/excerpts, one goal, explicit read-only or scoped write
authority and observable acceptance. Reading and log tasks stay read-only; fixes need a
safe checkout, one writer, focused tests and the same GPT review. Not for architecture,
security/data-integrity, consequential cross-module work or final approval. DeepSeek
remains the primary implementation worker with its Luna fallback; GPT remains the
reviewer. A Spark failure or outgrown scope returns to the parent with no silent
substitution — quiesce any writer first. No scout when direct tools suffice, no
splitting one fix across extra agents and no launches to consume quota. The existing
workspace, background launch, Plane tracking, leaf-agent and task-end archive rules
apply.

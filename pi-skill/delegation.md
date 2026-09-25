# MEGAI execution and subagent policy

Load only for actual delegation or model-error escalation. Routine Pi work follows
`megai` with one parent and self-review; delegation is not a required stage.
The optional `native` profile uses GPT Sol for coordination, DeepSeek Flash high for
implementation and GPT Astra high for independent review. The separate `economy`
preset retains its own DeepSeek role mix. `megai-roles.json` is parent-consumed
routing guidance, not automatic dispatch or an allowlist.

## Handoffs — fewer agents, not cheaper agents

The agent that gathers the evidence should be the agent that acts on it. Every
summary passed between agents is context the next agent never gets, and a writer
holding only a plan fixes symptoms instead of the root cause. Measured on a
comparable autofix pipeline after replacing triage + coordinator + up to 15
hypothesis agents + coding agent with one agent: median issue-to-PR 2.2 h -> 35 min,
p90 nine days -> under two hours, issues ending in a PR 0.6% -> 4.2%, spend per PR
$111 -> ~$18. Treat those as that system's numbers, not a prediction here.

- One context handoff per task, ideally zero. No planner/scout stage whose only
  output is a plan for the writer; a parent already holding the seam and evidence
  writes it.
- A delegated writer gets goal, acceptance, paths and authority, then gathers its
  own evidence in its own trace. Never a parent-written plan or summary as its
  primary context, and never a re-read of what the parent already read.
- Review verifies a delivered artifact (diff plus tests on that diff), not a second
  investigation stage.
- Judge the run end to end: per-stage green checks pass while the handoff fails.
- Cost is per delivered change, not per agent token; cutting writer tokens by adding
  a handoff is a loss until measured.
- Keep one trace per writer; a failed writer's diff, evidence and trace transfer to
  the replacement instead of restarting discovery.

Local handoff cost is measurable from Pi session logs with
`benchmark/handoff-cost/measure.py`; measure before claiming an improvement.

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
   `sleep` or a fixed-duration timer, repeated status/activity/file reads, or
   a heartbeat/scheduled poll. The parent yields instead of spinning.
3. On notification, match it to the expected child and current dispatch; read the
   result/evidence once when needed. Finished, errored and permission-needed events
   are distinct: idle/finished alone is not acceptance. Reconcile errors or request
   the required permission without automatically approving it. Ignore stale or
   duplicate events for already-consumed work; never replay a task just to wait.
4. Notifications require a supported delivery path to this parent; the flag alone
   is not proof. If delivery is unavailable and waiting is safe, use Paseo's
   event-backed native `paseo agent wait <id> --json` without a child deadline:
   it returns on idle, not at a guessed completion time. This is a blocking fallback,
   not a notification subscription; never present it as a delivered event. If a
   blocking wait is unsafe or unsupported, report the delivery blocker and yield.
   `paseo agent attach <id>` streams live output; synchronous `send_agent_prompt`
   is an option for an initial run, not a way to wait on an already-running child.
   Never resend a task merely to wait. One diagnostic status/activity read can
   reconcile a missed event, but never turn it into a polling loop. On resume,
   reconcile that same child before reuse.

These rules cover child-result waiting, not test timing, provider request timeout
and inactivity protection or integration-queue lease/claim semantics; those contracts
stay intact.
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

## Native provider fallback

Only a confirmed DeepSeek 402 insufficient-balance error permits one Pi continuation
on GPT Luna high. Authorization/permission failures, shared outages, other errors and
uncertain writes require reconciliation; never retry a possibly mutating request or
start a replacement writer before the original is quiescent. Preserve its diff and
evidence. A failed Luna continuation does not cycle back to DeepSeek. Keep the active
parent's own model and thinking unchanged.

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
context. Verify the Paseo harness is `pi` separately from the model provider.
The status-provided session handle must identify the same current native session ID.
Match the provider-qualified status model to native `model_change.provider` and
`model_change.modelId` (for example `openai-codex/gpt-6-astra` is not
`pi/gpt-6-astra`). Match native `thinking_level_change.thinkingLevel` to the
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

A confirmed provider timeout is not a reason to resend the same task blindly;
report the actual model and reconcile before choosing an explicitly approved next
step. A native wait timeout alone is not a provider failure.
For a suspected stall, do one bounded native wait of at most 180 seconds and inspect
progress/errors once — never repeated 600-second waits and never routine polling. If
no model or tool progress is observable in that interval while only a provider
response is pending, the owning parent may abort that request and reconcile before
assigning a different writer. Provider failures return to the owning Pi session with a worktree audit; inspect it
instead of assuming no writes occurred.
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
security/data-integrity, consequential cross-module work or final approval. The native
preset keeps Pi/Paseo in control; GPT coordinates and reviews while DeepSeek is an
optional implementation worker. A Spark failure or outgrown scope returns to the parent
with no silent substitution — quiesce any writer first. No scout when direct tools suffice, no
splitting one fix across extra agents and no launches to consume quota. The existing
workspace, background launch, Plane tracking, leaf-agent and task-end archive rules
apply.

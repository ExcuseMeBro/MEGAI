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

## Approved models

Every delegated scout, worker, debugger and reviewer uses the **Pi harness** and
exactly one of these models, including from local Pi sessions:

- `openai-codex/gpt-6-astra` — orchestration or exceptionally complex work, high.
- `openai-codex/gpt-5.6-luna` — bounded discovery, medium; scoped edits, high.
- `openai-codex/gpt-5.6-terra` — core implementation, high.
- `openai-codex/gpt-5.6-sol` — complex debugging and independent review, high.

Use only explicit medium/high thinking. Pick within this list; older GPT models,
other providers, aliases, wildcards and silent provider fallback are not allowed.
The user's current parent model, credentials and provider catalog stay unchanged.

## Immediate escalation — model failure or stalled progress

A model-specific error, timeout or reasoning dead-end returns immediately to the
parent with the exact error, attempted model, elapsed time, changed paths and test
evidence. The parent continues on the next suitable untried approved higher tier:
Luna -> Terra -> Sol -> Astra. This is an operational escalation order, not a
benchmark-proven quality/speed ranking; skip unsuitable/unavailable tiers.
Use high thinking for escalation. Avoid a same-model retry loop or idle backoff:
choose a materially different approach and at most two escalation transitions per slice.
Keep attempted-model history across re-slicing of the same blocker; never cycle
back to a failed model. At Astra/exhaustion, parent delivers verified partial
results and a precise blocker, or continues a smaller safe non-model-dependent
step. Unavailable Pi/approved alternatives block delegation, not authorize others.

Auth/permission failures, shared quota/outages and uncertain writes are not fixed
by model hopping: report them, preserve evidence and reconcile writes read-only.
An ordinary code/test failure needs a focused diagnosis, not automatic rerouting.
Confirm the old writer has stopped before transferring write authority; retain
its diff and completed tests. Reuse a healthy child for refinements; replace a
failed child only for the bounded escalation, with the existing evidence rather
than restarting discovery. Preserve required tests, independent review and user
approval boundaries; never trade data integrity or claim unmeasured speed gains.

## Verified launch

Use structured Paseo `create_agent`: `provider: "pi/openai-codex/gpt-5.6-luna"`,
`settings: { thinkingOptionId: "high" }`. First send only a neutral READY prompt;
verify returned harness **pi**, exact model and effective thinking via agent status
before sending task context. On mismatch cancel the child and report the blocker.
Re-check restored/existing agents before reuse. Children never delegate or mutate
Plane. Writers use managed isolated worktrees; direct parent tools suffice for
bounded work. Main promotion still needs separate explicit approval.

The local Pi `megai-model-guard` extension blocks unsupported/missing models and
thinking on structured Paseo creation, rejects out-of-list model updates and
blocks native subagent tools, opaque `mcpScript` calls and scheduled delegation.
Use individual structured MCP calls instead. Recognized CLI agent launches are
redirected to that path with an error, not silently rewritten. This is a tool-call
safety guard, **not an OS sandbox**: arbitrary shell scripts, external Paseo/UI
clients, disabled extensions and already-running children are outside its boundary.
Do not route around the guard. Reload local Pi after installation; if resource
filters exclude the guard, report the blocker rather than claim enforcement.

# Lean execution

Parent-only reference. System/developer instructions and repository restrictions win. Leaves follow their assigned scope and never create agents.

## Default path

Use direct parent tools for bounded work. Define acceptance, locate the responsible seam, patch, self-review, run focused tests, then stop. Do not delegate merely to select another model. Do not repeat a child's successful exploration or implementation.

Select the user's configured provider/model and supported thinking for the task.
MEGAI imposes no GPT-only model scope or provider allowlist. Never silently change
credentials, provider endpoints, permissions or test requirements for speed.

Pi users may explicitly select the [mixed preset](../../pi-skill/presets/README.md).
Its role mapping is parent-consumed configuration, not an automatic four-agent
pipeline. Existing user/task choices win; ordinary installation stays model-neutral.

## Five-minute slices

Split tasks over 5 minutes. Checkpoint at 5 minutes; no open-ended loops. Keep required gates.

## Delegate only when necessary

- Known seam: parent is the sole writer. Unknown seam: one scout only when isolated discovery saves work. A scoped worker replaces parent implementation, not duplicates it.
- Exactly one writer per checkout/configuration scope. Git and non-Git configuration/source writers use scoped local workspaces by default via `agent-worktree-lifecycle`, with private backups. Worktrees/task branches are explicit opt-in; child repositories need no separate Paseo registration. Serialize integration with other parents. Children never mutate trackers, merge, promote or drain queues.
- Give fresh context: acceptance, relevant paths, authority and focused verification only. No full parent transcript. Return verdict, changed paths, commands/results and risks in at most ten bullets.
- Use one fresh independent review for security/data-integrity risks, consequential cross-module changes or an explicit independent-review request. Otherwise parent diff review suffices. Keep existing tests, accessibility, compatibility and data-integrity gates.
- Permit one diagnosed transient retry or one focused correction. If acceptance still fails, preserve evidence and stop/escalate once to a suitable configured alternative; no model ping-pong or repeated repair chain.
- Use async completion notifications; do not poll running agents. Report actual blockers promptly. User-owned decisions remain with the user.

## Dispatch and trust

Inside Paseo, use visible Paseo children with an explicit model and thinking, using a configured model suitable for the task. Check the returned model identity. The lean Pi profile does not load native pi-subagents; do not reinstall it just to delegate. If no authorized delegation mechanism is available, work directly when safe or report the blocker.

A user who explicitly enables native delegation controls its model defaults and
scopes. Preserve those settings; MEGAI adds no model restrictions.

Use only approved providers and scope-relevant data. Never expose credentials, personal/production data or private transcripts to unauthorized tools or providers. Resource pruning does not authorize weaker security or task-tracker boundaries. Finish at In Review; main promotion needs separate explicit user approval.

## Resource and outcome evidence

Keep optional skill/tool packages installed but outside automatic discovery; load a specialist only for an explicit relevant request. Keep the required tracker lazy and reachable. Start memory/index services only when needed, not on every Pi launch.

Record available wall time, reported tokens/cache, correction count and acceptance on actual tasks without extra agents or synthetic task generation. Missing counters stay unknown. Smaller prompts and fewer startup jobs are resource measurements, not proof of faster completion or unchanged quality. TPS alone is not task quality. A fresh session is needed to shed old context and removed tool schemas.

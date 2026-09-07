# Lean GPT execution

Parent-only reference. System/developer instructions and repository restrictions win. Leaves follow their assigned scope and never create agents.

## Default path

Use direct parent tools for bounded work. Define acceptance, locate the responsible seam, patch, self-review, run focused tests, then stop. Do not delegate merely to select another model. Do not repeat a child's successful exploration or implementation.

| Work requiring delegation | Pi model ID | Thinking |
| --- | --- | --- |
| User-facing parent | `openai-codex/gpt-6-astra` | high |
| Bounded discovery/research | `openai-codex/gpt-5.6-luna` | medium |
| Scoped implementation, including high-risk work | `openai-codex/gpt-5.6-luna` | high |
| Complex debugging, independent review or security advice | `openai-codex/gpt-5.6-sol` | high |

GPT-only: no MiniMax routing or fallback. Use only medium or high thinking. These are operational defaults, not a benchmark-proven ranking. Never change credentials, provider endpoints, permissions or test requirements for speed.

## Five-minute slices

Split tasks over 5 minutes. Checkpoint at 5 minutes; no open-ended loops. Keep required gates.

## Delegate only when necessary

- Known seam: parent is the sole writer. Unknown seam: one scout only when isolated discovery saves work. A scoped worker replaces parent implementation, not duplicates it.
- Exactly one writer per checkout. Use a managed worktree; serialize integration with other parents. Children never mutate trackers, merge, promote or drain queues.
- Give fresh context: acceptance, relevant paths, authority and focused verification only. No full parent transcript. Return verdict, changed paths, commands/results and risks in at most ten bullets.
- Use one fresh Sol review for security/data-integrity risks, consequential cross-module changes or an explicit independent-review request. Otherwise parent diff review suffices. Keep existing tests, accessibility, compatibility and data-integrity gates.
- Permit one diagnosed transient retry or one focused correction. If acceptance still fails, preserve evidence and stop/escalate once to Sol; no model ping-pong or repeated repair chain.
- Use async completion notifications; do not poll running agents. Report actual blockers promptly. User-owned decisions remain with the user.

## Dispatch and trust

Inside Paseo, use visible Paseo children with an explicit model and thinking, e.g. `pi/openai-codex/gpt-5.6-luna` / high for a necessary writer. Check the returned model identity. The lean Pi profile does not load native pi-subagents; do not reinstall it just to delegate. If no authorized delegation mechanism is available, work directly when safe or report the blocker.

A user who explicitly enables native delegation retains Luna default/scout/researcher/delegate/worker, Sol reviewer/debugger/oracle, strict GPT-only model scopes, medium default thinking and a high ceiling. Project/per-run restrictions still win.

Use only approved providers and scope-relevant data. Never expose credentials, personal/production data or private transcripts to unauthorized tools or providers. Resource pruning does not authorize weaker security or task-tracker boundaries. Finish at In Review; main promotion needs separate explicit user approval.

## Resource and outcome evidence

Keep optional skill/tool packages installed but outside automatic discovery; load a specialist only for an explicit relevant request. Keep the required tracker lazy and reachable. Start memory/index services only when needed, not on every Pi launch.

Record available wall time, reported tokens/cache, correction count and acceptance on actual tasks without extra agents or synthetic task generation. Missing counters stay unknown. Smaller prompts and fewer startup jobs are resource measurements, not proof of faster completion or unchanged quality. TPS alone is not task quality. A fresh session is needed to shed old context and removed tool schemas.

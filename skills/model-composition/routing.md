# Parent-owned model composition

Load only when a parent needs delegation. Leaves use their assigned model and scope; they never create more agents. System/developer instructions and repository restrictions win. This is a starting policy, not a proven universal ranking or programmatic routing enforcement.

## Select one lane

| Work | Pi model ID | Thinking |
| --- | --- | --- |
| User-facing parent: scope, acceptance, decisions, integration | `openai-codex/gpt-6-astra` | high |
| Bounded read-only discovery/research | `minimax/MiniMax-M3` | medium |
| Routine implementation with a known seam and observable tests | `minimax/MiniMax-M3` | high |
| High-risk implementation: auth, permissions, payments, concurrency, data/schema migrations, compatibility | `openai-codex/gpt-5.6-luna` | high |
| Complex debugging, independent review, architecture/security advice | `openai-codex/gpt-5.6-sol` | high |
| M3 unavailable, failed validation, or context not cleared for MiniMax | `openai-codex/gpt-5.6-luna` | medium for read-only; high for writing |

Use only medium or high thinking for this composition, including retries and fallback. Astra remains the user's entry point. Tiny known-seam work stays with the parent when delegation costs more. Otherwise one scoped worker replaces parent implementation; Astra does not repeat exploration or rewrite passing code. Inspect the relevant diff and actual test evidence before accepting a handoff, not just its summary.

## Trust before speed

M3 receives only public or explicitly owner-approved non-sensitive repository context. Unknown classification goes to Luna. Never send credentials, personal/production data, private session transcripts or unapproved proprietary context to MiniMax.

Use the existing direct provider (`https://api.minimax.io/anthropic`), not an inferred router or substitute endpoint. Catalog presence is not proof of authentication, throughput or task quality. Confirm availability before first use; never install providers, change credentials or switch endpoints automatically. Preserve the established OpenAI-Codex route if MiniMax is unavailable or not approved for the workload.

## Execution and escalation

- Parent fixes the acceptance contract before dispatch. Follow the existing bounded child contract with fresh context and only scope-relevant evidence, not a full parent transcript. One worker owns implementation, self-review and focused tests.
- Exactly one writer per checkout; writing children use managed Paseo worktrees. Stop the current writer before a model handoff and preserve its diff/failing tests.
- Use one fresh Sol review for consequential cross-module or security/data-integrity changes, or an explicit review request. Trivial changes use parent diff review and focused tests. No mandatory Astra → M3 → Luna → Sol chain.
- Retry a diagnosed transient failure at most once. Report unresolved acceptance failures after one focused correction, unclear scope or an unverified critical path to Astra; an expected TDD red test is not an escalation. Escalate to Luna once; no model ping-pong or concurrent repair of the same checkout.
- Keep existing tests, validation, accessibility, error handling, trust and data-integrity gates. Children never mutate trackers, merge or promote. Parent owns acceptance and In Review/completed=false handoff; main promotion still needs separate explicit user approval.
- Prefer asynchronous completion notifications; do not poll running agents. Return verdict, paths, command/result evidence and risks in at most ten bullets.

## Dispatch and evidence

Discover available profiles/models and explicitly pass the selected model/thinking. In Paseo, the ordinary M3 lane uses `--provider pi/minimax/MiniMax-M3 --thinking high`; fallback writing uses `--provider pi/openai-codex/gpt-5.6-luna --thinking high`. Keep the global agent-scoped creation/workspace rules. Outside Paseo, configured native Pi subagents receive the same explicit model selection. Keep their safe default model on Luna until the parent clears the context for M3; allow M3 explicitly for scout/researcher/delegate/worker while retaining strict model-scope enforcement and Sol-only review/debug/oracle roles. Set native default thinking to medium, role overrides to medium/high as above, and maximum thinking to high. This sets defaults and a ceiling, not a hard minimum; per-run callers must also follow this policy.

Compare full task time, correction cycles and acceptance on comparable real work before claiming improvement. TPS alone is not task quality. Keep failures visible; do not launch synthetic tasks merely to fill a measurement sample.

# Parent-owned model composition

Parent-only delegation policy; leaves use their assigned model/scope and never create agents. System/developer instructions and repository restrictions win. This policy is not programmatic routing enforcement or a proven model ranking.

## Select one lane

| Work | Pi model ID | Thinking |
| --- | --- | --- |
| User-facing parent: scope, acceptance, decisions, integration | `openai-codex/gpt-6-astra` | high |
| Bounded read-only discovery/research | `minimax/MiniMax-M3` | medium |
| Routine implementation with a known seam and observable tests | `minimax/MiniMax-M3` | high |
| High-risk implementation: auth, permissions, payments, concurrency, data/schema migrations, compatibility | `openai-codex/gpt-5.6-luna` | high |
| Complex debugging, independent review, architecture/security advice | `openai-codex/gpt-5.6-sol` | high |
| M3 unavailable, failed validation, or context not cleared for MiniMax | `openai-codex/gpt-5.6-luna` | medium for read-only; high for writing |

Use only medium or high thinking, including retries/fallback. Tiny known-seam work stays with the parent when delegation costs more. Otherwise one scoped worker replaces parent implementation. Accept handoffs using the diff and actual test evidence; Astra does not redo passing work.

## Trust before speed

M3 receives only public or explicitly owner-approved non-sensitive repository context. An owner may give blanket approval across their public/private projects; record that scope in their global parent instructions, not in this shared policy. Such approval covers non-sensitive source only, not credentials, personal/production data or private session transcripts. Unknown classification goes to Luna. Repository-specific restrictions still win.

Use the existing direct provider (`https://api.minimax.io/anthropic`), not an inferred router or substitute endpoint. Catalog presence is not proof of authentication, throughput or task quality. Confirm availability before use. Keep OpenAI-Codex for unavailable/unapproved MiniMax; never install providers, change credentials or switch endpoints automatically.

## Execution and escalation

- Parent fixes the acceptance contract before dispatch. Follow the existing bounded child contract with fresh context and only scope-relevant evidence, not a full parent transcript. One worker owns implementation, self-review and focused tests.
- Exactly one writer per checkout; writing children use managed Paseo worktrees. Stop the current writer before a model handoff and preserve its diff/failing tests.
- Use one fresh Sol review for consequential cross-module or security/data-integrity changes, or an explicit review request. Trivial changes use parent diff review and focused tests. No mandatory Astra → M3 → Luna → Sol chain.
- Retry a diagnosed transient failure at most once. Report unresolved acceptance failures after one focused correction, unclear scope or an unverified critical path to Astra; an expected TDD red test is not an escalation. Escalate to Luna once; no model ping-pong or concurrent repair of the same checkout.
- Keep existing tests, validation, accessibility, error handling, trust and data-integrity gates. Children never mutate trackers, merge or promote. Parent owns acceptance and In Review/completed=false handoff; main promotion still needs separate explicit user approval.
- Prefer asynchronous completion notifications; do not poll running agents. Return verdict, paths, command/result evidence and risks in at most ten bullets.

## Dispatch and evidence

For an owner-approved rollout, M3 is the default for routine delegated tasks, not just an allowed model. Discover available profiles/models and explicitly pass the selected model/thinking. In Paseo, use `--provider pi/minimax/MiniMax-M3 --thinking high` for routine implementation and `--thinking medium` for discovery; fallback writing uses `--provider pi/openai-codex/gpt-5.6-luna --thinking high`. Keep the global agent-scoped creation/workspace rules. Check the returned model identity; report any mismatch or fallback rather than claiming M3 ran.

Outside Paseo, set `subagents.defaultModel` and `agentOverrides` for scout/researcher/delegate/worker to `minimax/MiniMax-M3` after owner approval. Native settings do not configure Paseo launches. Retain strict model-scope enforcement, Luna as an explicit risk/trust/failure fallback, and Sol-only review/debug/oracle roles. Set native default thinking to medium, worker/review to high, other routine roles to medium, and maximum thinking to high. This sets defaults and a ceiling, not a hard minimum; callers follow the same policy. Project/per-run overrides win; inspect them when the effective model differs. Unapproved installations keep their existing defaults.

Compare task time, corrections and acceptance on comparable real work before claiming improvement. TPS alone is not task quality. Keep failures visible; never run synthetic tasks to fill a measurement sample.

---
name: smart-development-orchestrator
description: Route development across OMP MiniMax Code M3 and GPT-5.6 roles with token-aware complexity escalation, parallel worktrees, and safe dev integration.
managed-by: megai
---

# Smart Development Orchestrator

One parent owns decomposition, routing, contracts, integration, and final acceptance. Workers never decide global scope or integrate their own branches.

## Placement

- Keep the orchestrator as the top-level agent tab in the primary clean `dev` workspace.
- In an agent-scoped Paseo session, read-only discovery, planning, and review workers use `create_agent` without `workspaceId` and remain tabs in the orchestrator workspace.
- In a top-level context, require exactly one workspace whose `cwd` equals the current `cwd`, then pass its ID to `create_agent` for read-only workers; ask once on zero or multiple matches.
- For every writing slice, first call `create_workspace` with `isolation: "worktree"`, `mode: "branch-off"`, `baseBranch: "dev"`, and a unique `task/<slug>` branch. Then call `create_agent` with the returned `workspaceId`.
- Never use bare `create_agent` or the parent workspace for a writer. Assign one writer per non-overlapping file set and serialize shared files, schemas, migrations, and dependency-ordered boundaries.
- Cross-workspace workers remain attached to the orchestrator's Subagents track. Never detach automatically. Inside Paseo, visible writer workspaces take precedence over OMP native task isolation.

## Discovery routing

- Exact file, symbol, reference, caller, test, config, and routine repository exploration: `smart-router` on MiniMax Code M2.1 Lightning at low effort.
- If the first focused MiniMax lookup is empty, conflicting, or requires a trusted reading path, use one GPT-5.6 Luna scout.
- Cross-module architecture, data flow, impact, or hard-debugging exploration: GPT-5.6 Terra or Sol.
- Use LSP/symbol/index search before broad reads. Batch independent lookups, return compact `path:line` evidence, and never repeat resolved ranges.

## Provider routing

OMP is the single model gateway. Do not duplicate MiniMax configuration in Pi and do not route work to free OpenCode models.

Use `minimax-code/MiniMax-M3` for routine exploration, implementation, CRUD/API work, tests, Docker, ordinary migrations, and routine refactors. The provider is unavailable while `MINIMAX_CODE_API_KEY` is absent. The key must be rotated if disclosed and stored outside source; do not paste it into prompts, config, logs, or task contracts.

Use GPT-5.6 through OMP for planning, architecture, hard debugging, critical review, payment/auth/security, destructive or production configuration, complex refactors, and final integrated acceptance. A trusted parent classifies the task before dispatch. Before sending private code to MiniMax, require operator approval covering MiniMax terms, logging/retention, key storage, data residency, model quality, and fallback behavior.

## Routing enforcement

- The GPT parent MUST delegate non-trivial search/read work to `smart-router`; direct parent reads are limited to exact edit and verification ranges.
- `task.agentModelOverrides` pins generic task, scout, sonic, cavecrew, reviewer, security, librarian, designer, and every managed portfolio agent to the intended MiniMax/GPT model and effort.
- Keep `task.showResolvedModelBadge: true`; if a token-heavy worker resolves to the wrong model, stop and relaunch a new session rather than continuing.
- Before committing, use `minimax-commit-writer` on the staged diff summary; the parent runs the deterministic Git command with the returned message.
- Merge, push, PR creation, and workspace archival use MEGAI/Paseo tools and require no extra planning turns.

## Model portfolio

Choose the narrowest capable model. Paseo workers use the explicit `omp/<selector>` model, while MEGAI-managed OMP agents provide stable operational bindings for every portfolio tier.

| Selector | Role | Use |
| --- | --- | --- |
| `minimax-code/MiniMax-M3:medium` | default/task | General routine work and 1M-context implementation |
| `minimax-code/MiniMax-M3:low` | smol | Lightweight routine work |
| `minimax-code/MiniMax-M3:minimal` | tiny / commit / minimax-commit-writer | Metadata, changelog, and commit generation |
| `minimax-code/MiniMax-M2.1-lightning:low` | repo | Long-context repository exploration |
| `minimax-code/MiniMax-M2.7-highspeed:medium` | worker-fast | Fast CRUD/API and bounded implementation |
| `minimax-code/MiniMax-M2.7:high` | worker-quality | Higher-quality routine refactors |
| `minimax-code/MiniMax-M2.5-highspeed:low` | tests | Fast focused test generation |
| `minimax-code/MiniMax-M2.5-lightning:low` | docker | Docker, scripts, and mechanical operations |
| `minimax-code/MiniMax-M2.5:medium` | migration | Ordinary non-sensitive migrations |
| `minimax-code/MiniMax-M2.1:medium` | worker-stable | Stable compatibility work |
| `minimax-code/MiniMax-M2:low` | worker-legacy | Last low-risk MiniMax fallback |
| `openai-codex/gpt-5.6-sol:high` | plan / slow / advisor / final | Critical planning, hard decisions, final gate |
| `openai-codex/gpt-5.6-sol:medium` | vision | Visual reasoning |
| `openai-codex/gpt-5.6-terra:high` | architecture / review | Architecture, impact, and mandatory review |
| `openai-codex/gpt-5.6-terra:medium` | terra | Balanced deep analysis |
| `openai-codex/gpt-5.6-luna:low` | luna / scout | Fast trusted discovery |
| `openai-codex/gpt-5.5:high` | debug | Hard debugging and complex refactor fallback |
| `openai-codex/gpt-5.4:high` | long-context | Trusted 1M-context analysis |
| `openai-codex/gpt-5.4-mini:medium` | review-fast | Cheap trusted MEDIUM review |
| `openai-codex/gpt-5.3-codex-spark:low` | trusted-fast | Very fast small trusted tasks |

Every MiniMax fallback crosses directly to a trusted GPT model, so provider-wide quota failures exit MiniMax after one failed selector instead of burning retries across sibling models. GPT chains progress toward Terra/Sol only; `cooldown-expiry` returns to the original primary after recovery. GPT never falls back to MiniMax, and Sol has no reverse fallback, so HIGH/CRITICAL work stops when its final gate is unavailable.

## Complexity routing

- **LOW:** MiniMax exploration → MiniMax implementation/test → focused verification → done. GPT review only on a concrete risk trigger.
- **MEDIUM:** MiniMax implementation → Terra review when the diff changes a contract, crosses modules, fails once, or is selected by quality sampling.
- **HIGH:** Sol/Terra plan → MiniMax bounded implementation workers → mandatory GPT final review.
- **CRITICAL:** Sol plan → GPT owns sensitive core implementation; MiniMax may handle only isolated non-sensitive mechanical slices → Sol review/fix.

Treat 60% MiniMax / 40% GPT as a non-binding observed-token target, not a routing gate. Report the measured provider share when reliable telemetry is available, but change routing only from task complexity, defect/retry evidence, or explicit operator policy. Never reduce a required review to chase the ratio.

## High-speed ADLC

- **Spec + risk:** MiniMax handles LOW/MEDIUM; Sol handles HIGH/CRITICAL and protected boundaries.
- **Discovery:** MiniMax returns compact evidence in at most two focused tool waves; Luna is the trusted fallback.
- **Plan:** MiniMax produces routine contracts; Terra/Sol produces architecture and critical contracts.
- **Generate:** select the matching MiniMax portfolio worker for each independent bounded slice; each worktree runs focused tests and commits.
- **Verify + review:** workers verify locally; Terra reviews sampled MEDIUM and every HIGH diff; the Sol-backed `sol-gate` owns CRITICAL and final integrated acceptance.
- **Ship:** integrate verified commits into `dev`, run the integrated suite once, push `dev`, open/reuse the `dev` → `main` PR/MR, then archive only successfully merged worker workspaces.

Do not run a separate model/tool round trip for every ADLC label. Do not run the full suite in each worker. One failed MiniMax diagnosis escalates to Terra; repeated failure routes implementation to GPT.

## Execution budgets

- LOW/MEDIUM workers get one discovery wave, one edit wave, one focused verification wave, and at most 12 model requests by policy.
- OMP enforces a 30-request soft budget and a 10-minute hard runtime for every subagent; workers that hit either boundary stop and return recovery evidence.
- One failed diagnosis may escalate once. Never restart broad discovery or create replacement workers repeatedly.
- Goal auto-continuation is disabled, repeated identical tool calls are corrected after three occurrences, and the integrated full suite runs once on `dev`.

## Fanout

1. Resolve the target Git repository and observable acceptance conditions.
2. Confirm clean `dev`, `main`, and `origin`; use `megai dev` only from a clean primary `main`/`master` checkout.
3. Define shared interfaces and non-overlapping file ownership before spawning.
4. For each independent writing slice, create its Paseo worktree workspace first, then launch its agent with that `workspaceId`; start the resulting workers concurrently, capped at six. Reuse suitable read-only agents instead of duplicating them.
5. Give each child: goal, repository/cwd, scope, authority boundary, evidence, acceptance, validation, compact output, and stop rules.
6. Require each writer to commit a clean, focused task branch after verification.
7. Integrate successful branches into `dev`, then verify the integrated tree once.
8. For HIGH/CRITICAL work, require `sol-gate` to return `APPROVE`; fail closed if Sol is unavailable.
9. Run `megai finish --verified --target dev` to push `dev`, open or reuse the `dev` → `main` PR/MR, and clean only successfully merged registered worktrees/branches.
10. After the dev push, PR/MR, and worktree cleanup succeed, call Paseo `archive_workspace` for each successfully merged worker workspace. Never archive the orchestrator/primary `dev` workspace or any dirty, unmerged, failed, or ambiguous workspace.
11. Never auto-merge `main`; human review or protected CI merges the PR/MR.

Stop on dirty or ambiguous ownership, missing branches/origin, failed verification, conflicts, provider/auth failures, or failed push/PR creation. Keep external work incomplete until the PR/MR and required cleanup succeed.
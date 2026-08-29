---
name: smart-development-orchestrator
description: Execute development quickly through one bounded implementation, code self-review, and focused-test pass using the fastest capable OMP model.
managed-by: megai
---

# Smart Development Orchestrator

One parent owns scope and delivery. Use one writer for one task; fan out only independent implementation slices explicitly present in the user's request.

## Placement

- Keep the orchestrator as the top-level agent tab in the primary clean `dev` workspace.
- Read-only discovery, planning, review, and UI/design agents are never automatic. Launch one only when the user requests that specialty or the direct focused path cannot locate or verify the change.
- In a top-level Paseo context that genuinely needs a read-only agent, require exactly one workspace whose `cwd` equals the current `cwd`, then pass its ID to `create_agent`; ask once on zero or multiple matches.
- For every writing slice, first call `create_workspace` with `isolation: "worktree"`, `mode: "branch-off"`, `baseBranch: "dev"`, and a unique `task/<slug>` branch. Then call `create_agent` with the returned `workspaceId`.
- Never use bare `create_agent` or the parent workspace for a writer. Assign one writer per non-overlapping file set and serialize shared files, schemas, migrations, and dependency-ordered boundaries.
- Cross-workspace workers remain attached to the orchestrator's Subagents track. Never detach automatically. Inside Paseo, visible writer workspaces take precedence over OMP native task isolation.

## Discovery routing

- Prefer direct LSP, symbol, index, and focused file reads; direct tools are faster than another model call.
- Use `smart-router` on MiniMax Code M2.1 Lightning only when the target is genuinely unknown or repository-wide evidence is required.
- One empty or conflicting MiniMax lookup may escalate once to GPT-5.6 Luna/Terra. Never restart broad discovery or create an autonomous search loop.
- Batch independent lookups, return compact `path:line` evidence, and never repeat resolved ranges.

## Provider routing

OMP is the single model gateway. Do not duplicate MiniMax configuration in Pi and do not route work to free OpenCode models.

Use `minimax-code/MiniMax-M3` or `MiniMax-M2.7-highspeed` for implementation, code self-review, focused tests, CRUD/API work, Docker, ordinary migrations, and routine refactors. The provider is unavailable while `MINIMAX_CODE_API_KEY` is absent. The key must be rotated if disclosed and stored outside source; do not paste it into prompts, config, logs, or task contracts.

Use GPT through OMP only when the user's task explicitly needs a GPT specialty, MiniMax fails a focused implementation or test once, or sensitive correctness cannot be established by the bounded code review and focused tests. GPT is an escalation path, never an automatic planner, reviewer, or final gate.

## Routing enforcement

- Start with direct tools and one implementation writer. Do not delegate search, planning, review, commit writing, or UI inspection when the parent can complete it in the same bounded pass.
- `task.agentModelOverrides` keeps explicitly requested portfolio agents on their intended models.
- Keep `task.showResolvedModelBadge: true`; if a writer resolves to the wrong model, stop that worker and relaunch once with the intended selector.
- Generate concise deterministic commit messages in the parent; do not invoke `minimax-commit-writer` automatically.
- Merge, push, PR creation, and workspace archival use MEGAI/Paseo tools and require no extra planning or review turns.

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
| `openai-codex/gpt-5.6-sol:high` | plan / slow / advisor / final | Explicit critical reasoning or operator-requested final review |
| `openai-codex/gpt-5.6-sol:medium` | vision | Explicit visual reasoning |
| `openai-codex/gpt-5.6-terra:high` | architecture / review | Explicit architecture or independent review |
| `openai-codex/gpt-5.6-terra:medium` | terra | Failure-driven deep analysis |
| `openai-codex/gpt-5.6-luna:low` | luna / scout | Fast trusted discovery fallback |
| `openai-codex/gpt-5.5:high` | debug | Focused hard-debugging fallback |
| `openai-codex/gpt-5.4:high` | long-context | Explicit trusted 1M-context analysis |
| `openai-codex/gpt-5.4-mini:medium` | review-fast | Explicit fast independent review |
| `openai-codex/gpt-5.3-codex-spark:low` | trusted-fast | Explicit very small trusted task |

Fallback chains remain acyclic and cross from MiniMax to one trusted GPT model on provider or focused-task failure. Fallback is recovery only; it must not trigger planning, review, or final-gate fanout.

## Default execution

For every task, complexity selects the writer model but does not add workflow stages:

1. Inspect the exact code seam.
2. Implement the smallest complete change.
3. Self-review the changed code for correctness, maintainability, and unnecessary complexity.
4. Run the narrowest focused tests or diagnostics.
5. Commit and ship when the delivery requires it, then stop.

Use a specialized GPT model only when steps 1–4 fail once or the user explicitly asks for architecture, security, independent review, or deep debugging. Never sample reviews or invoke quality gates to meet a provider ratio.

## UI execution

- UI changes use the same bounded implementation path.
- Check only code-level concerns by default: component structure, state handling, accessibility semantics, token/style consistency, type diagnostics, and focused component tests.
- Do not launch browsers, simulators, screenshots, visual regression, design critique, or accessibility audit agents unless the user explicitly requests them.
- State that visual/manual review remains with the user.

## Execution budgets

- Use one discovery wave only when needed, one edit wave, one code self-review, and one focused verification wave.
- Target at most eight model requests. OMP enforces a 16-request soft budget and a five-minute hard runtime for every subagent.
- One focused failure may escalate once to one GPT specialist. Never restart broad discovery, create replacement workers repeatedly, or continue after the requested task is proven.
- Goal auto-continuation is disabled and repeated identical tool calls are corrected after two occurrences.
- Do not run an automatic integrated or full suite; focused tests are the default completion evidence.

## Fanout

1. Use one writer for one task.
2. Fan out only when the user's task contains two or more genuinely independent writing slices with non-overlapping files and a fixed shared contract.
3. For each writing slice, create its Paseo worktree workspace first, then launch its agent with that `workspaceId`; cap concurrent writers at four.
4. Give each child the exact goal, repository/cwd, scope, authority boundary, acceptance, focused validation, compact output, and stop rule.
5. Each writer implements, self-reviews its code, runs focused tests, commits a clean branch, and stops. Children never launch agents.
6. Integrate successful branches into `dev` without an automatic review agent or full-suite run.
7. Run `megai finish --verified --target dev` to push `dev`, open or reuse the `dev` → `main` PR/MR, and clean only successfully merged registered worktrees/branches.
8. After successful delivery and cleanup, call Paseo `archive_workspace` for each merged worker workspace. Never archive the orchestrator/primary `dev` workspace or dirty, unmerged, failed, or ambiguous work.
9. Never auto-merge `main`; the user owns remaining manual review and merge.

Stop on dirty or ambiguous ownership, missing branches/origin, failed verification, conflicts, provider/auth failures, or failed push/PR creation. Keep external work incomplete until the PR/MR and required cleanup succeed.
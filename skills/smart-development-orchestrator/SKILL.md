---
name: smart-development-orchestrator
description: Use GPT for every code write and MiniMax only for bounded read-only discovery, with one fast implementation/self-review/test pass.
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
- Use `smart-router` on MiniMax Code M2.1 Lightning only for read-only search, read, find, symbol/reference lookup, and compact repository evidence.
- One empty or conflicting MiniMax lookup may escalate once to GPT-5.6 Luna/Terra. MiniMax never receives write, test, migration, or review authority.
- Batch independent lookups, return compact `path:line` evidence, and never repeat resolved ranges.

## Provider routing

OMP is the single model gateway. Do not duplicate MiniMax configuration in Pi and do not route work to free OpenCode models.

Use GPT through OMP for every code write: GPT-5.6 Terra medium owns core implementation and self-review; GPT-5.4 Mini owns small bounded edits and focused tests; GPT-5.5 owns migrations/hard debugging; GPT-5.4 owns compatibility and long-context work; Spark owns tiny mechanical edits.

Use MiniMax Code M2.1 Lightning only inside `smart-router` and read-only scout roles for search, read, find, glob, symbols, references, callers, and existing-pattern lookup. Never route implementation, tests, refactors, migrations, Docker changes, commit writing, or fallback writes to MiniMax.

## Routing enforcement

- Start with direct tools and one GPT implementation writer. Use MiniMax only when read-only repository discovery is genuinely needed.
- `task.agentModelOverrides` pins all write-capable agents to GPT and only `smart-router`, `scout`, and `cavecrew-investigator` to MiniMax.
- Keep `task.showResolvedModelBadge: true`; if any writer resolves to MiniMax, stop it immediately and relaunch once on `gpt-core-worker` or `gpt-fast-worker`.
- Generate concise deterministic commit messages in the parent; do not invoke a commit-writing agent.
- Merge, push, request promotion, and workspace archival use deterministic MEGAI/Paseo tools and require no extra model turns.

## Model portfolio

Choose the narrowest capable model. Paseo workers use the explicit `omp/<selector>` model, while MEGAI-managed OMP agents provide stable operational bindings for every portfolio tier.

| Selector | Role | Use |
| --- | --- | --- |
| `minimax-code/MiniMax-M2.1-lightning:low` | repo / scout / smart-router | Read-only search, read, find, symbols, references, callers, and pattern lookup |
| `openai-codex/gpt-5.6-terra:medium` | default / task / gpt-core-worker | Core implementation, self-review, and product logic |
| `openai-codex/gpt-5.6-terra:high` | worker-quality / architecture / review | High-risk implementation and explicit deep review |
| `openai-codex/gpt-5.4-mini:medium` | smol / worker-fast / tests / gpt-fast-worker | Fast small edits and focused tests |
| `openai-codex/gpt-5.3-codex-spark:low` | tiny / commit / docker / worker-legacy | Tiny mechanical trusted changes |
| `openai-codex/gpt-5.5:high` | migration / debug | Migrations and hard debugging |
| `openai-codex/gpt-5.4:high` | worker-stable / long-context | Compatibility and long-context implementation |
| `openai-codex/gpt-5.6-sol:high` | plan / slow / advisor / final | Explicit critical reasoning or operator-requested final review |
| `openai-codex/gpt-5.6-sol:medium` | vision | Explicit visual reasoning |
| `openai-codex/gpt-5.6-luna:low` | luna | One-step trusted discovery fallback |
| `openai-codex/gpt-5.4-mini:medium` | review-fast | Explicit fast independent review |
| `openai-codex/gpt-5.3-codex-spark:low` | trusted-fast | Explicit very small trusted task |

Only the read-only MiniMax discovery role may fall back once to Luna. GPT write roles never fall back to MiniMax, so provider limits stop quickly instead of consuming more low-quality write tokens.

## Default execution

For every task, complexity selects the writer model but does not add workflow stages:

1. Inspect the exact code seam.
2. Implement the smallest complete change.
3. Self-review the changed code for correctness, maintainability, and unnecessary complexity.
4. Run the narrowest focused tests or diagnostics.
5. Commit and ship when the delivery requires it, then stop.

GPT owns steps 2–4 for every task. MiniMax may supply compact discovery evidence for step 1 only and must never edit, generate tests, review code, or own a task worktree. Do not chase a fixed token ratio; enforce the authority boundary.

## UI execution

- UI changes use the same bounded implementation path.
- Check only code-level concerns by default: component structure, state handling, accessibility semantics, token/style consistency, type diagnostics, and focused component tests.
- Do not launch browsers, simulators, screenshots, visual regression, design critique, or accessibility audit agents unless the user explicitly requests them.
- State that visual/manual review remains with the user.

## Execution budgets

- Use one discovery wave only when needed, one edit wave, one code self-review, and one focused verification wave.
- Target at most eight model requests. OMP enforces a 16-request soft budget and a five-minute hard runtime for every subagent.
- One focused GPT failure may escalate once to the matching GPT specialist. Never retry a failed GPT write on MiniMax, restart broad discovery, or create replacement workers repeatedly.
- Goal auto-continuation is disabled and repeated identical tool calls are corrected after two occurrences.
- Do not run an automatic integrated or full suite; focused tests are the default completion evidence.

## Fanout

1. Use one writer for one task.
2. Fan out only when the user's task contains two or more genuinely independent writing slices with non-overlapping files and a fixed shared contract.
3. For each writing slice, create its Paseo worktree workspace first, then launch `gpt-core-worker` or `gpt-fast-worker` with that `workspaceId`; cap concurrent writers at four.
4. Give each child the exact goal, repository/cwd, scope, authority boundary, acceptance, focused validation, compact output, and stop rule.
5. Each writer implements, self-reviews its code, runs focused tests, commits a clean branch, and stops. Children never launch agents.
6. Integrate successful branches into `dev` without an automatic review agent or full-suite run.
7. Run `megai finish --verified --target dev` to push `dev`, reuse the one open `dev` → `main` request, and clean only successfully merged registered worktrees/branches.
8. After successful dev delivery and cleanup, call Paseo `archive_workspace` for each merged worker workspace. Never archive the orchestrator/primary `dev` workspace or dirty, unmerged, failed, or ambiguous work.
9. Complete the tracked task, then ask the user whether to promote `dev` to `main`. Run `megai promote --approved` only after an explicit affirmative reply; never infer approval or enable deferred auto-merge.

Stop on dirty or ambiguous ownership, missing branches/origin, failed verification, conflicts, provider/auth failures, or failed push/request/promotion. Main stays unchanged while approval is absent.
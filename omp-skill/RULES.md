<!-- megai:paseo-placement:begin -->
# OMP smart routing and Paseo placement

## Smart code discovery

- Use direct LSP, index, search, and exact reads first. Invoke `smart-router` only when the target is genuinely unknown or read-heavy repository evidence is required.
- One empty/conflicting MiniMax lookup may escalate once to Luna or Terra. Never repeat resolved evidence or start an autonomous search loop.
- New model settings and managed agents apply to new sessions/task resolutions. If a writer resolves to the wrong model, stop and relaunch once instead of continuing on the wrong tier.

## Worker model routing

- OMP is the single model gateway. Use MiniMax M3 or M2.7 Highspeed for implementation, code self-review, focused tests, Docker, ordinary migrations, and routine refactors.
- GPT specialties are explicit or failure-driven: architecture, hard debugging, sensitive correctness, or independent review only when requested or after one focused MiniMax failure. No automatic planning, sampled review, or final gate.
- Generate commit messages directly in the parent; never add a model call solely for commit text. Merge and push remain deterministic MEGAI operations.
- Ignore provider-share targets during execution. Select the fastest capable model for the user's exact task. Do not use free OpenCode models or duplicate MiniMax in Pi. A disclosed `sk-cp` key must be rotated and configured outside source.

## Bounded execution

- Run inspect → implement → code self-review → focused tests → ship when required, then stop.
- UI checks are code-only by default: component structure, state handling, accessibility semantics, token/style consistency, diagnostics, and focused component tests. Browser, simulator, screenshot, visual, design, and accessibility-audit loops require an explicit user request.
- Do not run automatic planner/reviewer/final-gate agents, TDD loops, integrated full suites, queue draining, or `/loop`. One focused failure may escalate once to one specialist.

## Paseo agent placement

- The orchestrator stays in the primary `dev` workspace.
- In an agent-scoped Paseo session, read-only discovery, planning, and review workers use `create_agent` without `workspaceId`, so they appear as tabs in the orchestrator workspace.
- In a top-level context, require exactly one workspace whose `cwd` equals the current `cwd`, then pass its ID to `create_agent` for read-only workers; ask once on zero or multiple matches.
- Every worker with write authority MUST first use `create_workspace` with `isolation: "worktree"`, `mode: "branch-off"`, `baseBranch: "dev"`, and a unique `task/<slug>` branch, then use `create_agent` with the returned `workspaceId`.
- Never create concurrent writers in the parent workspace and never use bare `create_agent` for a writer. Shared-file/schema/migration boundaries are serialized through one writer.
- Cross-workspace workers remain attached to the parent Subagents track. After verified merge, dev push, PR/MR creation, and worktree cleanup, call `archive_workspace` for that worker workspace. Never archive primary `dev`, dirty, failed, conflicted, or unmerged work.
- Outside Paseo, OMP native task isolation may provide ephemeral worktree/branch isolation; inside Paseo, visible writer workspaces take precedence.
<!-- megai:paseo-placement:end -->

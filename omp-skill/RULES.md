<!-- megai:paseo-placement:begin -->
# OMP smart routing and Paseo placement

## Smart code discovery

- MUST delegate non-trivial file location, cross-file search, caller/reference tracing, and read-heavy exploration to `smart-router`. The GPT parent may read only an already-known exact edit or verification range and must not repeat router evidence.
- `smart-router` uses MiniMax Code M2.1 Lightning for routine lookup, Luna when MiniMax evidence is empty/conflicting or needs a trusted path, and Terra for cross-module architecture/data-flow/impact reasoning.
- New model settings and managed agents apply to new sessions/task resolutions. If the resolved-model badge shows the wrong model, stop and relaunch instead of continuing token-heavy work on GPT.

## Worker model routing

- OMP is the single model gateway. MiniMax agents own routine exploration, implementation, CRUD/API, focused tests, Docker, ordinary migrations, routine refactors, and commit/changelog message generation.
- GPT agents own planning, architecture, hard debugging, critical review, payment/auth/security, production configuration, complex refactors, and final integration. HIGH/CRITICAL GPT gates are mandatory regardless of the advisory ratio.
- Before `git commit`, delegate the staged diff summary and repository convention to `minimax-commit-writer`; the parent applies the returned message. Merge and push are deterministic MEGAI operations and should not consume additional model turns.
- Target roughly 60% MiniMax and 40% GPT as an observed-token guideline. Do not use free OpenCode models and do not duplicate MiniMax in Pi. A disclosed `sk-cp` key must be rotated, then configured as `minimax-code` through OMP auth or `MINIMAX_CODE_API_KEY` outside source.

## Paseo agent placement

- The orchestrator stays in the primary `dev` workspace.
- In an agent-scoped Paseo session, read-only discovery, planning, and review workers use `create_agent` without `workspaceId`, so they appear as tabs in the orchestrator workspace.
- In a top-level context, require exactly one workspace whose `cwd` equals the current `cwd`, then pass its ID to `create_agent` for read-only workers; ask once on zero or multiple matches.
- Every worker with write authority MUST first use `create_workspace` with `isolation: "worktree"`, `mode: "branch-off"`, `baseBranch: "dev"`, and a unique `task/<slug>` branch, then use `create_agent` with the returned `workspaceId`.
- Never create concurrent writers in the parent workspace and never use bare `create_agent` for a writer. Shared-file/schema/migration boundaries are serialized through one writer.
- Cross-workspace workers remain attached to the parent Subagents track. After verified merge, dev push, PR/MR creation, and worktree cleanup, call `archive_workspace` for that worker workspace. Never archive primary `dev`, dirty, failed, conflicted, or unmerged work.
- Outside Paseo, OMP native task isolation may provide ephemeral worktree/branch isolation; inside Paseo, visible writer workspaces take precedence.
<!-- megai:paseo-placement:end -->

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

- New agent or tab means the current Paseo workspace. Create another agent session so it appears as a sibling tab.
- In an agent-scoped Paseo session, call `create_agent` without `workspaceId`; Paseo inherits the caller's workspace.
- In a top-level context, require exactly one workspace whose `cwd` equals the current `cwd`, then pass that `workspaceId` explicitly to `create_agent`.
- Never call `create_workspace` unless the user explicitly requests a new workspace, worktree, isolated branch, or PR checkout.
- For zero or multiple matches, ask once and do not call `create_agent` or `create_workspace` until placement is resolved.
<!-- megai:paseo-placement:end -->

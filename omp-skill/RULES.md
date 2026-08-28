<!-- megai:paseo-placement:begin -->
# OMP smart routing and Paseo placement

## Smart code discovery

- Route non-trivial file location, cross-file search, caller/reference tracing, and read-heavy exploration through the `smart-router` task agent. The parent keeps implementation and final verification.
- `smart-router` uses MiniMax Code M3 for routine lookup, Luna when MiniMax evidence is empty/conflicting or needs a trusted path, and Terra for cross-module architecture/data-flow/impact reasoning.
- Direct parent reads are for an already-known exact edit or verification range. Do not duplicate ranges returned by the router.

## Worker model routing

- OMP is the single model gateway. MiniMax Code M3 owns routine exploration, implementation, CRUD/API, tests, Docker, ordinary migrations, and routine refactors.
- GPT-5.6 owns planning, architecture, hard debugging, critical review, payment/auth/security, production configuration, complex refactors, and final integration. HIGH/CRITICAL GPT gates are mandatory regardless of the target ratio.
- Target roughly 60% MiniMax and 40% GPT by inference tokens. Do not use free OpenCode models and do not duplicate MiniMax in Pi. A disclosed `sk-cp` key must be rotated, then configured as `minimax-code` through OMP auth or `MINIMAX_CODE_API_KEY` outside source.

## Paseo agent placement

- New agent or tab means the current Paseo workspace. Create another agent session so it appears as a sibling tab.
- In an agent-scoped Paseo session, call `create_agent` without `workspaceId`; Paseo inherits the caller's workspace.
- In a top-level context, require exactly one workspace whose `cwd` equals the current `cwd`, then pass that `workspaceId` explicitly to `create_agent`.
- Never call `create_workspace` unless the user explicitly requests a new workspace, worktree, isolated branch, or PR checkout.
- For zero or multiple matches, ask once and do not call `create_agent` or `create_workspace` until placement is resolved.
<!-- megai:paseo-placement:end -->

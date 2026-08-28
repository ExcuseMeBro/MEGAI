<!-- megai:paseo-placement:begin -->
# OMP smart routing and Paseo placement

## Smart code discovery

- Route non-trivial file location, cross-file search, caller/reference tracing, and read-heavy exploration through the `smart-router` task agent. The parent keeps implementation and final verification.
- `smart-router` uses Luna for focused lookup and may escalate exactly once to its read-only Terra worker for cross-module, ambiguous, architectural, data-flow, or impact questions.
- Direct parent reads are for an already-known exact edit or verification range. Do not duplicate ranges returned by the router.

## Worker model routing

- GPT models run through OMP: Sol owns orchestration and final integration, Terra owns detailed planning/review, and Luna owns search/read discovery.
- A trusted parent classifies the exact payload before creating a MiniMax-enabled process and scopes `MINIMAX_API_KEY` to that worker only. Use `minimax-worker` only for a bounded public/synthetic or privacy-attested writing slice. Never send secrets, personal data, private code, auth/security, schemas, migrations, or production configuration.
- Never configure the same Chinese provider in Pi and OMP. OMP is the single model gateway; Pi remains an emergency/local lightweight fallback.

## Paseo agent placement

- New agent or tab means the current Paseo workspace. Create another agent session so it appears as a sibling tab.
- In an agent-scoped Paseo session, call `create_agent` without `workspaceId`; Paseo inherits the caller's workspace.
- In a top-level context, require exactly one workspace whose `cwd` equals the current `cwd`, then pass that `workspaceId` explicitly to `create_agent`.
- Never call `create_workspace` unless the user explicitly requests a new workspace, worktree, isolated branch, or PR checkout.
- For zero or multiple matches, ask once and do not call `create_agent` or `create_workspace` until placement is resolved.
<!-- megai:paseo-placement:end -->

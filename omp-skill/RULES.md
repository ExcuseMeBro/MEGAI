<!-- megai:paseo-placement:begin -->
# Paseo agent placement

- New agent or tab means the current Paseo workspace. Create another agent session so it appears as a sibling tab.
- In an agent-scoped Paseo session, call `create_agent` without `workspaceId`; Paseo inherits the caller's workspace.
- In a top-level context, require exactly one workspace whose `cwd` equals the current `cwd`, then pass that `workspaceId` explicitly to `create_agent`.
- Never call `create_workspace` unless the user explicitly requests a new workspace, worktree, isolated branch, or PR checkout.
- For zero or multiple matches, ask once and do not call `create_agent` or `create_workspace` until placement is resolved.
<!-- megai:paseo-placement:end -->

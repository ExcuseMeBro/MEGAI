---
name: agent-worktree-lifecycle
description: Deliver verified task work from managed worktrees to the agreed branch; main promotion requires explicit approval.
managed-by: megai
---

# Agent worktree lifecycle

The parent owns integration. Use one writer per registered worktree; read-only children may share the parent workspace. Inside Paseo create writers through `create_workspace` with worktree isolation and then `create_agent` with that workspace ID. Select Pi explicitly for every child and verify its returned harness/model/thinking; follow `megai`'s GPT-only Pi delegation contract. Children never create agents, mutate trackers or integrate branches. Independent slices may use separate worktrees only with non-overlapping ownership.

## Delivery contract

Resolve the target before edits. Default: task branch from `dev`, then verified integration to `dev`. **An explicit persistent-branch request overrides that default:** push only the named branch, retain its branch/worktree, and do not merge into `dev`/`main`, call `finish`, or archive the retained workspace.

Before delivery, inspect the diff and prove task acceptance with relevant tests; use independent review for security/data-integrity risks or consequential cross-module changes. Commit only task-owned changes. Stop on dirty/ambiguous target ownership, conflicts, failed checks, authentication failures or uncertain push results; never force-push or force-delete work.

For normal dev delivery:

```bash
megai finish --dry-run --target dev
megai finish --verified --target dev
```

This merges/pushes verified dev, reuses one open dev-to-main request and cleans only the safely merged task worktree/branch. Archive only that merged child workspace, never the primary or unmerged/dirty work. Verify delivery before the parent hands off the linked Plane item at started `In Review`; only the user marks `Done`.

Main stays unchanged until the user explicitly approves promotion of the reviewed dev head:

```bash
megai promote --approved
```

Never infer approval from an implementation request, enable deferred auto-merge, or drain another task after acceptance.

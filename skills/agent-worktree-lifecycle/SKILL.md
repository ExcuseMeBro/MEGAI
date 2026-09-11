---
name: agent-worktree-lifecycle
description: Deliver verified task work from managed worktrees to the agreed branch; main promotion requires explicit approval.
managed-by: megai
---

# Agent worktree lifecycle

The parent owns integration. Use one writer per registered managed worktree; readers may share that worktree read-only. Select Pi explicitly and verify the returned harness/model/thinking before task context; follow `megai`'s Pi-only delegation contract. Children never create agents, mutate trackers or integrate branches.

## One primary workspace at rest

Before creating a task workspace, run `megai workspace --root CURRENT_CHECKOUT`.
It resolves the Git **primary** checkout and its unique existing Paseo project ID,
even when called from a linked worktree. Same remote URL alone is not identity.
Missing/ambiguous registration is BLOCKED; do not create another project to bypass it.

1. Each new task gets a distinct branch and managed worktree workspace from `dev`.
   Use structured Paseo `create_workspace` with `isolation: "worktree"`, the resolved
   **canonical `projectId`**, and explicit branch/base/title. Omit `path`. The daemon
   chooses its managed location. Reuse only for a refinement of the same task,
   after confirming idle writer ownership; the primary remains the delivery checkout.
2. Check the returned project ID, workspace ID and Git primary/common directory.
   Never pass a sibling checkout path as a new local project. Do not clone or run
   direct `git worktree add ../PROJECT-task` for agent work.
3. Pass that explicit `workspaceId` to `create_agent`; never rely on implicit
   top-level workspace creation. Writers use non-overlapping scopes. Readers share
   a managed workspace read-only, not a second project registration.
4. Keep one primary workspace at rest. Additional workspaces represent unfinished
   isolated tasks, not permanent copies of the project. A separately approved
   persistent branch is an explicit retention exception, never a sibling project.
5. Match subagents to scope: the parent handles a bounded known change directly;
   use scoped Pi workers for independent implementation and read-only reviewers
   for independent evidence. Readers share the task workspace; simultaneous writers
   each own a distinct managed worktree. Child workspaces close with the parent task.

The receipt-owned `megai-workspace-guard` enforces these creation preconditions in
Pi tool calls, using read-only/on-demand Git and Paseo registry lookup. It leaves
models, auth, settings and input arguments unchanged. It is not an OS sandbox:
external clients, arbitrary scripts and disabled/excluded extensions are outside
its boundary. Report unavailable identity/guard rather than claim enforcement.

For existing duplicates, inventory branches, dirty/untracked data, agents and
terminals first. Obtain writer release before moving anything. Use supported Paseo
operations; never rewrite a running daemon's registry. Archive only completed,
safely delivered workspaces with retained history; never archive an active/dirty
workspace merely to hide duplication. If lossless reparenting is unavailable,
report that blocker and agree the archive/recreation or maintenance boundary.

## Delivery contract

Resolve the target before edits. Default: task branch from `dev`, then verified integration to `dev`. **An explicit persistent-branch request overrides that default:** push only the named branch, retain its branch/worktree, and do not merge into `dev`/`main`, call `finish`, or archive the retained workspace.

Before delivery, inspect the diff and prove task acceptance with relevant tests; use independent review for security/data-integrity risks or consequential cross-module changes. Commit only task-owned changes. Stop on dirty/ambiguous target ownership, conflicts, failed checks, authentication failures or uncertain push results; never force-push or force-delete work.

For normal dev delivery:

```bash
megai finish --dry-run --target dev
megai finish --verified --target dev
```

This merges/pushes verified dev, reuses one open dev-to-main request and cleans only
its safely merged task worktree/branch. Verify the remote dev head before cleanup.
Coordinate the helper's Git cleanup with supported Paseo archival; never edit the
live registry. Confirm all task writers/reviewers and terminals are released,
inspect tracked/untracked/ignored data, and preserve required evidence externally.
Archive each completed child workspace, verify its worktree is gone, then delete
only safely merged redundant task branches (including published task refs when
retirement is authorized). Never force-delete an unmerged branch or discard dirty
work; stop and reconcile it. Verify no completed child workspace remains active
and only the primary remains when no unfinished task or explicit retention
exception exists. Do not archive another parent's active task to reach that count.

Before archival, relocate final source-bound verification to the delivered primary
with freshly captured receipts/review; changing receipt cwd does not transfer old
evidence. Preserve historical raw evidence and session history. Hand off the same
Plane item at started `In Review` only after verified delivery and cleanup; only the
user marks `Done`.

Main stays unchanged until the user explicitly approves promotion of the reviewed dev head:

```bash
megai promote --approved
```

Never infer approval from an implementation request, enable deferred auto-merge, or drain another task after acceptance.

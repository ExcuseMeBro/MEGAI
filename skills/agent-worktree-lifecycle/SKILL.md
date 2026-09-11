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

The receipt-owned `megai-workspace-guard` enforces canonical project identity and
managed worktree isolation in Pi creation calls. It does not enforce branch/base/title
policy or task uniqueness; the parent verifies those separately. Lookup is read-only
and on demand; models, auth, settings and input arguments remain unchanged. This is
not an OS sandbox: external clients, arbitrary scripts and excluded extensions are
outside its boundary. Report an unavailable guard rather than claim enforcement.

For existing duplicates, inventory branches, dirty/untracked data, agents and
terminals first. Obtain writer release before moving anything. Use supported Paseo
operations; never rewrite a running daemon's registry. Archive only completed,
safely delivered workspaces with retained history; never archive an active/dirty
workspace merely to hide duplication. If lossless reparenting is unavailable,
report that blocker and agree the archive/recreation or maintenance boundary.

## Delivery contract

Resolve the target before edits. Default: task branch from `dev`, then verified integration to `dev`. **An explicit persistent-branch request overrides that default:** push only the named branch, retain its branch/worktree, and do not merge into `dev`/`main`, call `finish`, or archive the retained workspace.

Before delivery, inspect the diff and prove task acceptance with relevant tests; use independent review for security/data-integrity risks or consequential cross-module changes. Commit only task-owned changes. Stop on dirty/ambiguous target ownership, conflicts, failed checks, authentication failures or uncertain push results; never force-push or force-delete work.

For Paseo-managed dev delivery, separate integration from destructive cleanup.
The legacy `finish` helper removes the checkout itself; use the ordered primary-dev
sequence below so it cannot delete ignored artifacts or a reviewer's active cwd.

1. Release all task writers and owned terminals. Reserve the clean primary `dev`
   checkout; verify its local/remote head is the reviewed base. Inventory tracked,
   untracked and ignored files in every retiring workspace. Reconcile dirty work,
   preserve required drafts, refs and session/evidence bytes in verified private
   backups, and stop on an unknown owner or unresolved data. Read-only verification
   may continue only while its checkout remains retained.
2. Commit and verify the candidate against the current dev base in its task
   workspace, including tests and independent review. With a source-current PASS,
   use integration-only commands from the parent (replace placeholders):

   ```bash
   git -C PRIMARY merge --ff-only TASK_BRANCH
   git -C PRIMARY push origin dev
   ```

   The primary must still be clean, on `dev`, and at the reserved base before the
   fast-forward. Stop on divergence or an uncertain push; verify the exact remote
   dev head. These commands leave task worktrees and branches intact.
3. Capture fresh source-bound verification at the delivered primary and obtain
   source-current independent review before retiring its task checkout. Old receipt
   cwd values cannot be rewritten to transfer evidence. Keep historical raw logs.
4. Release every remaining reviewer. Recheck each retiring workspace's data and
   merged ancestry immediately before supported Paseo archival; never edit the live
   registry. Archive only a released, clean, safely delivered child and verify its
   worktree is gone. Delete only safely merged redundant task branches, including
   published task refs when retirement is authorized. Never force-delete unmerged
   work. An external read-only parent may verify the final live layout without
   resurrecting an archived task workspace.
5. Verify no completed child workspace remains active and only the primary remains
   when no unfinished task or explicit retention exception exists. Another parent's
   active task is not a cleanup target. Hand off the same Plane item at started
   `In Review` only after verified delivery and cleanup; only the user marks `Done`.

Main stays unchanged until the user explicitly approves promotion of the reviewed dev head:

```bash
megai promote --approved
```

Never infer approval from an implementation request, enable deferred auto-merge, or drain another task after acceptance.

---
name: agent-worktree-lifecycle
description: Deliver verified task work from managed worktrees to the agreed branch; main promotion requires explicit approval.
managed-by: megai
---

# Agent worktree lifecycle

The parent owns integration. Use one writer per registered managed worktree; readers may share that worktree read-only. Registered non-Git directory projects have the read-only exception below. Select Pi explicitly and verify the returned harness/model/thinking before task context; follow `megai`'s Pi-only delegation contract. Children never create agents, mutate trackers or integrate branches.

## Existing projects only

Work inside the user's existing Paseo project: project → task workspace → agent
tabs. "Canonical" means resolving that existing identity, not creating a project
named canonical or regrouping/renaming the user's projects. This applies to every
project, not only MEGAI. Missing or ambiguous identity is BLOCKED: ask the user to
select/reconcile the existing project, rather than registering a replacement.
Project creation or reorganization needs a separate explicit user request.

## Non-Git directory review

A workspace/umbrella folder (e.g. ADAM with separate component repositories) need
not become a Git repo just to open a reviewer. Run `megai workspace --root DIRECTORY`:
`kind: "directory"` means the exact real path has one active existing `non_git`
Paseo project. Use that returned `projectId`; no new infra repo, `git init`, clone,
project registration or user location question is needed for read-only work.
Missing/ambiguous identity, malformed registry, inaccessible paths and broken Git
metadata still block; a Git failure is not a blanket permission to use local mode.

1. Reuse the current task's verified directory `workspaceId` on refinement. For a
   new read-only task, create a workspace under that existing project using
   `create_workspace` with `isolation: "local"`, `projectId`, and a task title. If
   `path` is supplied, it must resolve to the exact registered root; omit all Git
   branch/worktree/PR fields. Multiple workspaces are normal: choose the known task
   ID, not the first workspace at that path. Reconcile uncertain creation by lookup.
2. Verify the returned project/workspace IDs, `kind: "directory"` and exact cwd.
   Open agent tabs with `create_agent`, an explicit Pi provider/model, supported
   thinking, and `labels: {"megai.access": "read-only"}`. Use the neutral READY and
   native model/thinking verification from `megai` before sending task context.
3. Scope the reader to named files/snapshots and read-only commands. The label is a
   parent authority declaration, **not a filesystem sandbox**; it does not prevent
   arbitrary shell writes or authorize a later promotion to writer. No edits, task
   mutation, delegation or live migration/deploy actions. Preserve independent
   security review and source-current evidence; never replace review with self-PASS.
4. A writer still needs the matching existing component/infra Git repository and
   a managed isolated worktree. An umbrella's child Git repo keeps its own Git/Paseo
   identity, not the directory exception. Reuse the originating Plane identity and
   documented mapping (ADAM workspace/components use `ADAM full`). If the write
   location is genuinely unresolved, continue safe read-only review/planning and
   report only that write-location decision; never invent a repo or fake acceptance.
5. Release readers and task-owned terminals before supported archival of a completed
   task workspace. Local workspace archival is bookkeeping, not permission to delete
   the directory or its files. Preserve other active workspaces and user data.

## One primary workspace at rest

For Git project changes, before creating a task workspace, run `megai workspace --root CURRENT_CHECKOUT`.
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
3. Open agent tabs with `create_agent` and that explicit `workspaceId`; never rely
   on implicit top-level workspace creation. Writers use non-overlapping scopes. Readers share
   a managed workspace read-only, not a second project registration.
4. Keep one primary workspace at rest. Additional workspaces represent unfinished
   isolated tasks, not permanent copies of the project. A separately approved
   persistent branch is an explicit retention exception, never a sibling project.
5. Match subagents to scope: the parent handles a bounded known change directly;
   use scoped Pi workers for independent implementation and read-only reviewers
   for independent evidence. Readers share the task workspace; simultaneous writers
   each own a distinct managed worktree. Child workspaces close with the parent task.

The receipt-owned `megai-workspace-guard` enforces canonical project identity and
managed worktree isolation in Pi creation calls, with the explicit registered-directory
read-only launch exception above. It does not enforce post-launch read-only behavior or branch/base/title
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

---
name: agent-worktree-lifecycle
description: Deliver verified task work from managed worktrees to the agreed branch; main promotion requires explicit approval.
managed-by: megai
---

# Agent worktree lifecycle

The parent owns integration. Use one writer per registered managed worktree; readers may share that worktree read-only. Registered non-Git directory projects use the scoped local-workspace exception below. Select Pi explicitly and verify the returned harness/model/thinking before task context; follow `megai`'s Pi-only delegation contract. Children never create agents, mutate trackers or integrate branches.

## Existing projects only

Work inside the user's existing Paseo project: project → task workspace → agent
tabs. "Canonical" means resolving that existing identity, not creating a project
named canonical or regrouping/renaming the user's projects. This applies to every
project, not only MEGAI. Missing or ambiguous identity is BLOCKED: ask the user to
select/reconcile the existing project, rather than registering a replacement.
Project creation or reorganization needs a separate explicit user request.

## Non-Git local work

A registered workspace/umbrella folder (e.g. ADAM) supports both readers and scoped
configuration writers without a Git repository. Run `megai workspace --root DIRECTORY`:
`kind: "directory"` identifies one active existing `non_git` project at the exact
real path. Use its returned `projectId`; no new infra repo, `git init`, clone or
project registration is needed. Absence of Git alone never blocks configuration
work or triggers an infra-repo question. Unknown/ambiguous identity, inaccessible
paths and broken Git metadata still require reconciliation, not blind fallback.

1. Reuse the current task's verified directory `workspaceId` on refinement. For a
   new task, create a workspace under that existing project with `isolation: "local"`,
   `projectId`, and a title. An optional `path` must resolve to the exact registered
   root; omit Git branch/worktree/PR fields. Multiple workspaces are normal: select
   the known task ID, not the first matching path. Reconcile uncertain creation by lookup.
2. Verify returned project/workspace IDs, `kind: "directory"` and cwd. Open agent tabs
   with `create_agent`, explicit Pi provider/model and supported thinking. Readers use
   `labels: {"megai.access": "read-only"}`. Configuration writers use
   `labels: {"megai.access": "write", "megai.writeScope": "infra/service-config"}`,
   naming an existing, relative, non-symlink configuration subdirectory of this project.
   Parent derives a suitable scope from the task/current layout and may create the
   needed configuration directory; it does not ask for a separate repo merely to proceed.
   Use neutral READY/native model/thinking verification before sending task context.
3. Local workspaces share files: they are **not isolated filesystem copies**. Before
   either parent or child writes, inspect agents/terminals across all workspace IDs at
   that project root and reserve one writer for the configuration scope. Record exact
   owned files, acceptance, backup/rollback location and deadline in the same Plane
   task. Back up existing files privately before replacement, retain their permissions,
   and preserve unrelated files. Stop on an overlapping/unknown writer or uncertain write.
   A `megai.writeScope` label is a scope declaration, **not a filesystem sandbox**;
   the parent must enforce ownership and scope. Never promote a reader by prompt alone.
4. Run `megai acceptance` with `--root` set to the complete owned configuration
   subdirectory, not the whole multi-repo umbrella. Directory snapshots include every
   file and subdirectory (including hidden files); no ignore rules silently omit source.
   Keep contracts, raw logs, backups and generated test outputs outside that source root.
   Include all task-relevant configuration/test inputs; do not narrow scope to hide a
   change. Preserve independent security review, real tests, red→green for bug fixes
   and a source-current PASS. Production deployment, secrets and destructive migration
   still need their normal explicit authorization; local write access grants none of these.
5. A writer still needs a managed isolated worktree when changing Git repository
   sources, including child component repos inside the umbrella. Local config work
   outside Git instead delivers verified files plus private backup/evidence: no invented
   commit, branch, push or merge step. Reuse the originating Plane identity and documented
   mapping (ADAM workspace/components use `ADAM full`); hand off In Review, never Done.
6. Release all task writers, readers and terminals before supported workspace archival.
   Local archival is bookkeeping, not permission to delete the directory or its files.
   Keep delivered configuration, backups/evidence and other active workspaces intact.

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
scoped local-workspace exception above. It does not enforce post-launch filesystem access or branch/base/title
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

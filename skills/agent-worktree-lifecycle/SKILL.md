---
name: agent-worktree-lifecycle
description: Use folder-first local task workspaces, single-writer ownership and verified delivery; worktrees are explicit opt-in.
managed-by: megai
---

# Folder-first workspace lifecycle

The parent owns delivery and reserves one writer per shared file scope. Local
workspaces are the default for Git and non-Git folders alike. A workspace is task
bookkeeping, not a reason to create a branch, worktree, repository or project.
Children never delegate, mutate Plane or integrate. Follow `megai`'s verified Pi
launch procedure and keep the user's provider/model/thinking preferences intact.

## Existing projects only

Use the folder already added to Paseo: project → task workspace → agent tabs.
Run `megai workspace --root FOLDER` to resolve its existing projectId. From a child
repository, the nearest registered containing folder supplies the identity; do not
register each child Git repository. Existing linked worktrees retain their primary
identity. Equal-root duplicates, missing identity, unreadable paths and broken Git
metadata require reconciliation, not a new project. Project creation or reorganization needs a separate explicit user request.

## Local work — default for every folder

1. Each new task uses `create_workspace` with `isolation: "local"`, the resolved
   `projectId` and a title. Omit branch/worktree/PR fields. An optional `path` must
   resolve to the registered folder exactly; omit it when projectId is sufficient.
   Reuse the same task workspace on refinement. Multiple workspaces are normal:
   use the known workspaceId, not the first matching cwd. Verify the returned
   projectId/workspaceId/cwd. Git presence does not change this local default.
2. Local workspaces share files: they are **not isolated filesystem copies**.
   Inspect agents and terminals across all workspace IDs sharing the folder.
   Reserve one writer per overlapping file scope; parallel readers are allowed.
   Record exact owned paths, acceptance, deadline and rollback location in Plane.
   Back up existing files privately before replacement, preserving permissions;
   protect unrelated changes. An unknown or overlapping writer blocks writes.
3. Open agent tabs with `create_agent`, explicit verified `workspaceId`, Pi model
   and supported thinking. Readers use `labels: {"megai.access": "read-only"}`.
   Writers use `labels: {"megai.access": "write", "megai.writeScope": "relative/dir"}`;
   use `"."` when reserving the whole project folder. Scope directories must already
   exist and contain no symlink path components. A child Git repository is a valid
   local write scope; no separate Paseo registration or task branch is required.
   Labels are **not a filesystem sandbox** or lock: the parent enforces ownership,
   backups and scope. Never promote a reader just by changing its prompt.
4. Follow documented Plane mapping (ADAM workspace/components use `ADAM full`).
   Preserve independent review, actual tests and a source-current acceptance PASS.
   Use each changed Git repository as its acceptance root; for non-Git configuration
   use the complete owned configuration directory, not a multi-repo umbrella.
   Keep contracts, receipts and backups outside those source roots. Multiple changed
   repositories require evidence for each; do not narrow source to hide changes.
5. Deliver verified local files by default, with backup/evidence and no invented
   commit, branch, merge or push requirement. If Git delivery was explicitly agreed,
   use the agreed existing branch, inspect all staged/unstaged changes and commit
   only owned paths after acceptance preparation. Never switch branches underneath
   another session. Main promotion and Production deployment, secrets or destructive
   migrations need their normal separate approval; local write access grants none.
6. Release all task writers, read-only reviewers and owned terminals before closing
   a completed workspace. Local archival is bookkeeping, not permission to delete
   the folder or files. Keep delivered files, private backups, historical receipt
   cwd values and other active workspaces intact. Hand off In Review, never Done.

## Non-Git local work

The same local workflow applies: absence of Git alone is not a blocker; no new infra repo,
`git init` or clone is needed. Directory acceptance includes every hidden/regular
file and empty directory, bounded to 10,000 entries and 64 MiB. It rejects symlinks,
special files and nested Git metadata. Use the complete owned configuration scope;
Git components instead get their own Git acceptance evidence, not another Paseo project.

## Explicit isolation and one primary workspace at rest

Create a managed worktree/task branch only when the user explicitly requests
isolation. Resolve the existing Git project and use structured Paseo creation with
`isolation: "worktree"`; preserve canonical/common-directory validation. Do not
clone or register another project. A directory umbrella does not acquire a new
repository just to satisfy an optional isolation request; reconcile that boundary.
Readers may share a managed checkout; each isolated writer owns its own scope.
The guard validates identities and local scope paths, not user approval or an OS
sandbox. It does not enforce branch/base/title or post-launch filesystem writes.

After verified delivery, keep one primary workspace at rest. Archive only completed,
released workspaces. Inventory tracked, untracked and ignored content before removing
an explicitly created worktree; preserve dirty/unmerged data, drafts and history.
Delete only safely merged task branches when retirement is authorized. Preserve
unfinished tasks and explicit retention exceptions; another parent's active work
is not a cleanup target. Use supported Paseo archival, never rewrite its registry.

For explicitly agreed Git integration, release writers and reserve the clean target
before `git -C PRIMARY merge --ff-only TASK_BRANCH` and the agreed push. Never force
push/delete, use a cleanup helper that can remove an active cwd, or infer main
promotion approval. Verify the delivered head and release reviewers before archival.

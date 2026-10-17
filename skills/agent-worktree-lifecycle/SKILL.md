---
name: agent-worktree-lifecycle
description: Coordinate a tracked task across isolated Git worktrees and scoped non-Git configuration, with verified dev delivery and separately approved main promotion.
managed-by: megai
---

# Task worktree lifecycle

Plane owns the task identity; the parent owns integration and self-review. A task may affect several repositories, but never create a new project or repository just for coordination. Every Git source writer uses a separate task-owned worktree from the repo's current dev (or an explicitly approved target); never edit/stage/commit task source in dev/main. No specific agent runner or workspace manager is required.

## Before Git edits

For each affected repo, record primary/common-directory identity, base commit, branch (e.g. `task/slug`), worktree path, owned files and acceptance in the existing Plane item. Check existing worktrees and branches for collisions and active/foreign ownership. Create a new worktree with Git's ordinary worktree command or a safe available manager; verify its actual Git identity, branch and base SHA. Reuse only a proven task-owned worktree. If identity or exclusive ownership is uncertain, block Git writes rather than fall back to dev/main. Worktrees isolate files/indexes, not shared refs, ports, processes or credentials.

## Non-Git configuration

Use an explicitly owned local configuration scope with one writer. Inspect for overlapping edits, privately back up existing files and verify the backup. Do not use `git init`, a fake checkout or an external workspace registry to satisfy isolation. Do not edit symlinks, secrets or production settings without their own authorization. The config scope itself is not a sandbox or lock.

## Delivery

Run focused tests, inspect the complete diff and obtain source-current guarded acceptance when required. Commit owned Git changes in their worktrees before final evidence capture. Multi-repo readiness requires every affected repo and cross-repo compatibility. Reserve all integration targets atomically with `megai queue` under the same Plane pair and follow its published contract; unavailable queue blocks integration, not isolated work. Recheck exact candidate/target SHAs, clean target and ownership. Merge ready task commits into local dev without another approval; preserve ignored-file collisions in verified private backups. A moved base/conflict requires reconciliation and fresh checks in the task worktree. Record partial delivery and stop affected integrations rather than force/reset/replay them. Push and main promotion require separate explicit approval.

## Safe cleanup and handoff

After verified delivery, inventory tracked/untracked/ignored data; preserve required evidence and ignored files in a private verified backup. Release any owned writers/services. With integration reservation still held, prove the recorded task commit is an ancestor of the delivered target, recheck the branch tip and worktree identity, and remove only a released, clean, task-owned worktree via normal Git worktree removal. After verifying it is gone from Git's worktree list and disk, delete only its proven-merged local task branch via `git branch -d`. Do not use force, delete a primary checkout, sweep unknown branches, or remove foreign/dirty/busy resources. A refusal retains resources and is reported separately from delivery success. External workspace bookkeeping is optional and must never substitute for Git or ownership proof. Preserve historical receipt paths.

Record the exact delivered repo/commit vector, checks, review, cleanup or retention reasons on the same Plane task and hand off In Review. Main requires explicit approval of the reviewed repo/commit vector; a changed ref or scope invalidates approval. Done requires verified main delivery. For approved main pushes consult [main-release.md](main-release.md) for destination and release rules; no release for dev/task pushes. Other references in this directory that describe a particular external workspace manager are historical and not required by this workflow.

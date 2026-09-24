---
name: pi-workflow
description: Start and deliver tracked project changes with Plane, dev/main branches, local project rules, and isolation for monorepos or grouped repositories. Use before project edits, delegation, branch integration, or task handoff.
---

# Project work

1. Run `pi-workflow context` in the current folder. Read the reported rule files.
   `.pi/project.json` is local configuration: `layout` is `mono` or `multi`,
   `planeProject` is an existing Plane project name, `repositories` lists relative
   component paths, `forge` identifies the allowed host, and `preserveBranches`
   adds per-repository persistent branches. Global persistent branches are dev/main.
2. Run `pi-workflow start --title "EXACT TASK TITLE"`. This resolves all Plane
   pages, reuses an exact match or creates Todo, then moves it to In Progress.
   Keep its project/task UUID pair throughout refinements. Missing or ambiguous
   identity or workflow states block edits. Children inherit this pair read-only.
   For `/factory` only, use `pi-workflow factory-start --project-id UUID --task-id UUID
   --title "EXACT TASK TITLE"` instead of `start`: it validates the selected existing
   factory-ready Todo item and never creates a replacement. Do not invoke both.
3. Define task acceptance in the same Plane item. Use a managed Paseo worktree
   from dev per task. For a monorepo, one worktree contains all packages. For a
   grouped project, create one worktree per affected Git repo under the same
   existing Paseo project/task identity; pass each primary repository via `--path`.
   A coordination folder without `.git` is never initialized or cloned as a repo.
   Inherit its local rules into every child. Discover existing project ID with
   `paseo project ls --json`; create workspaces using `paseo workspace create`.
   Use returned paths under `~/.paseo/worktrees`, never constructed paths. This
   applies even to tiny edits; never edit, stage or commit directly on dev/main.
4. Serialize writes and integration for each repository. Work in task branches;
   do not change a busy primary checkout. An explicitly requested persistent
   branch overrides dev delivery: work on/push that branch only and retain it.
   Preserve dev, main, every locally configured extra branch, and unmerged work.
5. Run task acceptance checks, inspect the full diff, and fix review findings.
   After acceptance and required review, reserve all integration targets using
   `megai queue`, then automatically deliver verified task commits to local dev
   without waiting for another user confirmation. Ordinary single-task delivery may use
   `git merge --ff-only --no-overwrite-ignore`; `/mdev` all-candidates delivery instead
   uses its per-repository candidate ledger and
   `git merge --no-edit --no-overwrite-ignore <exact-sha>` so divergent task branches
   are merged rather than stalled. Preserve a colliding ignored file outside the checkout
   before a bounded retry; never overwrite or delete it.
   Verify exact delivered commits and
   complete the reservation; on a moved/dirty target, stale evidence or uncertain
   result, retain task resources and reconcile instead of forcing or assuming success.
   Push only with separate explicit approval. Perform safe task-owned post-merge
   workspace/branch cleanup before handing off In Review. Keep a receipt JSON:
   `{"repositories":[{"path":"/absolute/primary/repo","commit":"FULL_SHA","remote":"origin"}]}`.
   List every affected repository and its delivered commit. Runtime-only changes
   without a Git delivery remain In Review until a user-owned completion decision.
6. Run `pi-workflow review --project-id UUID --task-id UUID --receipt FILE
   --evidence-file FILE`. Evidence includes actual checks/results, review and
   remaining risks. The command stores the receipt on the same Plane item.
7. Promote the reviewed work to main only with explicit approval. Then run
   `pi-workflow done --project-id UUID --task-id UUID`. This reads the saved receipt,
   fetches each remote main, verifies every exact commit is included, and only then
   sets Done. Failed/partial delivery stays In Review. Run this at completion;
   there is no background watcher or unattended main merge.

For explicitly requested persistent branch work (including validationsdk), retain
that branch/worktree and leave the task In Review while its changes are absent from
main. Automatically archive only released, clean, task-owned temporary workspaces
and delete only proven-merged task branches after verified delivery, using
`agent-worktree-lifecycle` Post-merge cleanup; leave active, dirty, unknown and
unmerged work intact and report why. Never use force deletion/push to reconcile
ownership or divergence. No background daemon, hook, unattended main merge or
automatic push is implied.

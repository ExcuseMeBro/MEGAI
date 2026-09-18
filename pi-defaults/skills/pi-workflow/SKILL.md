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
3. Define task acceptance in the same Plane item. Use a managed Paseo worktree
   from dev per task. For a monorepo, one worktree contains all packages. For a
   grouped project, create one worktree per affected Git repo under the same
   existing Paseo project/task identity; pass each primary repository via `--path`.
   A coordination folder without `.git` is never initialized or cloned as a repo.
   Inherit its local rules into every child. Discover existing project ID with
   `paseo project ls --json`; create workspaces using `paseo workspace create`.
   Use returned paths under `~/.paseo/worktrees`, never constructed paths.
4. Serialize writes and integration for each repository. Work in task branches;
   do not change a busy primary checkout. An explicitly requested persistent
   branch overrides dev delivery: work on/push that branch only and retain it.
   Preserve dev, main, every locally configured extra branch, and unmerged work.
5. Run task acceptance checks, inspect the full diff, and fix review findings.
   Integrate verified task commits to dev and push when authorized by the task.
   Hand off In Review after all affected repos are delivered. Keep a receipt JSON:
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

When the `jev` tool is available, each numbered step's decision is one call with
that step's questions recorded on the same Plane item: the rule set (1), the exact
title match (2), isolation (3), delivery readiness (5), findings and the review
verdict (6), and the handoff state (7). The answer is advisory; step 7's main
promotion stays a user decision whatever it returns.

For persistent branch work (including validationsdk), retain branch/worktree and
leave the task In Review while its changes are absent from main. Clean up only
released, clean, verified-merged temporary worktrees/branches after delivery.
Never use force deletion/push to reconcile ownership or divergence.

---
name: agent-worktree-lifecycle
description: Keep primary development on dev, merge verified agent branches into dev, push dev, open or reuse a dev-to-main PR/MR, then safely remove only merged task worktrees. Use at task start/ship or for agent branch cleanup.
managed-by: megai
---

# Agent worktree lifecycle

Use `dev` as the default development and integration branch; `main` changes only through reviewed pull/merge requests. Run `megai dev` when starting from a clean primary `main`/`master` checkout. Every implementation writer works on a task branch from `dev` inside a registered Paseo/OMP/Git worktree; never write concurrently in the primary checkout or use unmanaged sibling clones.

## Parallel implementation

When a request has two or more independent implementation slices:

1. The parent is the sole integration owner and defines shared interfaces before spawning.
2. Inside Paseo, create one managed worktree workspace per writer from the same `dev` baseline, then launch each agent with the returned workspace ID. Start those agents concurrently.
3. Keep read-only discovery/review agents as tabs in the parent workspace. Never launch a writer there.
4. Outside Paseo, native OMP batch items with `isolated: true` and `task.isolation.merge: branch` may provide equivalent ephemeral isolation.
5. Assign one writer per file set. If slices touch the same file, schema, migration, or ordered dependency, serialize that boundary instead of racing.
6. Each worker commits only its slice and reports focused verification evidence. The integration owner merges successful branches into `dev`, resolves no ambiguous overlap, and verifies the integrated tree once.

A single indivisible task runs in one worktree; parallelism is required only when genuine independent slices exist.

## Preconditions

Before finishing:

1. Confirm the task branch is committed and the worktree is clean.
2. Run the task-relevant tests, typecheck, lint, or build.
3. Complete independent review when risk warrants it.
4. Keep the external task incomplete until the dev push, dev-to-main PR/MR, and required cleanup succeed.
5. Confirm `origin`, `dev`, and `main` are correct. Use `MEGAI_FORGE=github` or `MEGAI_FORGE=gitlab` for self-hosted forge URLs that cannot be detected.

## Finish

Preview first when repository ownership or placement is unfamiliar:

```bash
megai finish --dry-run --target dev
```

After verification and review:

```bash
megai finish --verified --target dev
```

To verify the merged tree again before cleanup:

```bash
megai finish --verified --target dev --verify-command "<focused verification command>"
```

The command merges a verified task branch locally with `--no-ff`—or publishes commits already on `dev`—then pushes `dev` and creates or reuses an open `dev` → `main` GitHub PR or GitLab merge request. Human review or protected CI merges that PR/MR into `main`; the agent never auto-merges `main`.

After the PR/MR exists, it:

- removes only the current registered linked worktree and its merged task branch; or
- when work happened in the primary checkout, keeps the repository on `dev` and deletes only the merged task branch.

It never deletes remote refs or the primary repository.

## Paseo workspace archival

After `dev` is pushed, the `dev` → `main` PR/MR exists, and the registered task worktree/branch cleanup succeeds, the orchestrator calls `archive_workspace` for that successfully merged worker workspace. Never archive the orchestrator or primary `dev` workspace. Never archive dirty, unmerged, failed, conflicted, or ambiguously owned workspaces; keep them available for recovery.

## Stop rules

Stop without task completion when:

- either source or target worktree is dirty;
- the current branch is detached or a protected branch other than `dev`;
- `dev`, `main`, or `origin` is absent, or `dev` is checked out in an incompatible location;
- verification fails;
- a merge conflict occurs;
- forge detection, authentication, push, or PR/MR creation fails;
- the directory is an arbitrary clone rather than a registered Git worktree.

Do not force-delete dirty or unmerged work. Do not scan and delete sibling repositories by name. For Paseo, archive only successfully merged worker workspaces after the dev push, PR/MR, and worktree cleanup are confirmed; for OMP, allow its worktree registry to observe the Git worktree removal.

After success, reconcile Asana and `.todos`, then report the PR/MR URL, merge target, and removed local worktree/branch. Human review merges the PR/MR into `main`.

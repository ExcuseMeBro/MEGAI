---
name: agent-worktree-lifecycle
description: Merge verified task worktrees into dev, push dev, reuse one open dev-to-main request, then promote main only after explicit user approval.
managed-by: megai
---

# Agent worktree lifecycle

Use `dev` as the default development and integration branch. Every implementation writer uses a task branch from `dev` in a registered Paseo/OMP/Git worktree. `main` changes only through the single reviewed `dev` → `main` pull/merge request and explicit user approval; never write concurrently in the primary checkout or use unmanaged sibling clones.

## Parallel implementation

When a request has two or more independent implementation slices:

1. The parent is the sole integration owner and defines shared interfaces before spawning.
2. Inside Paseo, create one managed worktree workspace per writer from the same `dev` baseline, then launch each agent with the returned workspace ID. Start those agents concurrently.
3. Keep read-only discovery/review agents as tabs in the parent workspace. Never launch a writer there.
4. Outside Paseo, native OMP batch items with `isolated: true` and `task.isolation.merge: branch` may provide equivalent ephemeral isolation.
5. Assign one writer per file set. If slices touch the same file, schema, migration, or ordered dependency, serialize that boundary instead of racing.
6. Each worker commits only its slice and reports focused verification evidence. The integration owner merges successful branches into `dev` and resolves no ambiguous overlap. Do not run an automatic integrated full suite.

A single indivisible task runs in one worktree; parallelism is required only when genuine independent slices exist.

## Preconditions

Before finishing:

1. Confirm the task branch is committed and the worktree is clean.
2. Self-review the changed code for correctness, quality, and unnecessary complexity.
3. Run the narrowest task-relevant test, typecheck, lint, or build. Independent review and full-suite gates are opt-in.
4. Keep the external task incomplete until `dev` is pushed, one `dev` → `main` request exists, and merged task worktree cleanup succeeds. Main promotion is a separate user-approved boundary.
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

The command merges a verified task branch locally with `--no-ff`—or publishes commits already on `dev`—then pushes `dev`. It reuses the one open `dev` → `main` request and creates one only when none exists.

After the request exists, it:

- removes only the current registered linked worktree and its merged task branch; or
- when work happened in the primary checkout, keeps the repository on `dev` and deletes only the merged task branch.

It never deletes remote refs or the primary repository.

## Main promotion

After the task is finished on `dev`, ask the user whether to promote the reviewed `dev` head to `main`. Do not infer approval from the original implementation request.

Only after an explicit affirmative answer:

```bash
megai promote --approved
```

The command verifies that local `dev` equals `origin/dev`, the one open request points at that exact commit, and forge checks/protections are clean. It merges that request, synchronizes local and remote `main`, and preserves `dev`. It never creates another request or enables deferred auto-merge. Without `--approved`, it fails before promotion.

## Paseo workspace archival

After `dev` is pushed, the `dev` → `main` PR/MR exists, and the registered task worktree/branch cleanup succeeds, the orchestrator calls `archive_workspace` for that successfully merged worker workspace. Never archive the orchestrator or primary `dev` workspace. Never archive dirty, unmerged, failed, conflicted, or ambiguously owned workspaces; keep them available for recovery.

## Stop rules

Stop without task completion when:

- either source or target worktree is dirty;
- the current branch is detached or a protected branch other than `dev`;
- `dev`, `main`, or `origin` is absent, or `dev` is checked out in an incompatible location;
- verification fails;
- a merge conflict occurs;
- forge detection, authentication, push, request creation, approved promotion, or main synchronization fails;
- the directory is an arbitrary clone rather than a registered Git worktree.

Do not force-delete dirty or unmerged work. Do not scan and delete sibling repositories by name. For Paseo, archive only successfully merged worker workspaces after the dev push, one open request, and worktree cleanup are confirmed; main approval is not required for workspace cleanup.

After task delivery, reconcile Asana and `.todos`, report the one request URL and removed task worktree/branch, then ask whether to promote `dev` to `main`. Run `megai promote --approved` only after an explicit affirmative reply.

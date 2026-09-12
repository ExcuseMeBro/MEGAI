---
name: agent-worktree-lifecycle
description: Coordinate one folder/task across isolated Git-repo worktrees, verified dev delivery and separately approved main promotion.
managed-by: megai
---

# Hybrid task workspace lifecycle

One existing Paseo folder/project and one Plane task coordinate the work. Git
source writers use separate managed worktrees; non-Git configuration uses a local
owned scope. Workspaces do not imply new project/repository registration. Parents
own integration; children never delegate, mutate Plane, merge or promote.

## Existing projects only

Run `megai workspace --root FOLDER` to resolve the existing projectId. Unregistered
child repositories inherit the nearest registered containing folder. Linked Git
worktrees retain their primary identity. Missing/ambiguous identity, overlapping
registered projects, unreadable paths or broken metadata require reconciliation.
Project creation or reorganization needs a separate explicit user request.

## Plan the complete task

Each new task records its affected repositories and non-Git configuration scopes
in the same Plane item. Use documented mapping (ADAM workspace/components use
`ADAM full`), not one new Plane/Paseo project per repository. Pick one lowercase
task slug, e.g. `adam-123`, and use `task/adam-123` in every affected Git repo.
One repo in a monorepo means one worktree; three independent backend/frontend/mobile
repos mean three worktrees with the same task name under their own repository roots.
Do not scan/copy unrelated repos or create an umbrella Git repo.

Record the repo primary/common-directory identity, base dev commit, task branch,
workspaceId/path, owned files, dependencies and acceptance per repo. This is a
technical delivery manifest/evidence in Plane, not another execution tracker.
Re-use it and the same task workspaces for refinements. Multiple workspaces are normal.
Reserve distinct ports, containers and test databases where runtime work needs them;
worktrees isolate files/indexes, not shared Git refs, services, secrets or an OS process.

## Git source isolation

1. Resolve every affected primary repo and its current `dev` base. Fetch an agreed
   remote when remote delivery is in scope; reconcile stale/diverged refs safely,
   without switching or resetting another session's checkout. Missing dev is BLOCKED,
   not permission to branch from main. An explicit delivery/base exception such as
   MEGAI's retained `pi` takes precedence and must be recorded.
2. Create each workspace through native Paseo, with the **same umbrella projectId**:

   ```json
   {"isolation":"worktree","projectId":"EXISTING_UMBRELLA_ID",
    "path":"/absolute/umbrella/backend","baseBranch":"dev",
    "branchName":"task/adam-123","worktreeSlug":"adam-123"}
   ```

   Repeat for frontend/mobile only if affected. `path` is that repo's primary
   checkout, not a subdirectory, clone or another worktree. Paseo manages placement;
   no child project registration or direct unmanaged `git worktree add` is needed.
   Verify returned projectId/workspaceId, real Git primary/common directory, branch,
   base HEAD and owned worktree path before writing. Same-name collisions or uncertain
   creation are reconciled by lookup; never delete or adopt an unknown owner's work.
3. Open agent tabs with `create_agent`, each repo's verified workspaceId, explicit
   Pi model and supported thinking; perform neutral/native launch verification.
   One writer per worktree; read-only reviewers may share it. Parallel task writers
   get different task branches/worktrees even within one repo. Cross-repo tasks can
   implement independently, while integration reserves shared target resources.

## Non-Git local work

Use `create_workspace` with `isolation: "local"`, the existing folder projectId and
optional exact folder path, without branch/worktree fields. Coordination/readers
may also use this local workspace when the folder itself is Git. Writers use
`labels: {"megai.access": "write", "megai.writeScope": "infra/service-config"}`;
readers use `labels: {"megai.access": "read-only"}`. Local Git writers are rejected.

Local workspaces are **not isolated filesystem copies**. Inspect agents/terminals
across matching folders and reserve one writer per overlapping scope. Back up existing files privately,
preserving permissions and unrelated data. Scope must be an existing non-symlink
configuration directory containing no Git metadata/symlinks (bounded to 10,000
entries); `"."` is valid only for such a complete Git-free folder, not a multi-repo
umbrella. Labels are **not a filesystem sandbox** or lock. Absence of Git alone
needs no new infra repo or `git init`. Keep complete owned configuration acceptance
and private backups outside source; no invented commit/branch/push for these files.
Production deployment, secrets and destructive migrations retain separate approval.

## All-repo readiness and dev delivery

1. Preserve independent review and actual acceptance for **all affected repos and
   configuration scopes before the first dev mutation**. Commit only owned changes
   when Git delivery is agreed, then capture source-current evidence per worktree.
   Include cross-repo/API compatibility tests and runtime resource ownership when
   relevant; one green repository does not make the multi-repo task ready.
2. Release all task writers before integration. Reserve **all target repo resources
   atomically** through `megai queue`. Read the separately delivered contract at
   `$MEGAI_HOME/pi-skill/integration-queue.md` (`MEGAI_HOME` defaults to `~/.megai`;
   repository source: `pi-skill/integration-queue.md`). Use `plan` with the same Plane
   identity and repeated `--repo PRIMARY_PATH CANDIDATE_REF`, then `enqueue` the private
   request. `claim` with a unique executor checks the target base vector; keep its token
   private and maintain its lease with `heartbeat`. Keep queue position while waiting;
   `refresh` with new evidence retains FIFO after revalidation; stale owners need
   explicit `reconcile` with owner-stopped evidence, not timeout-based lock stealing.
   The shared queue journal is coordination, not a Plane replacement or main/push
   approval. If queue support is unavailable, integration is BLOCKED; isolated
   implementation may continue.
3. Under the reservation, preflight every source/destination commit, clean target
   checkout and remote policy before mutating any repo. Record the exact source/dev
   commit vector. Integrate each ready task into its own existing dev checkout:
   `git -C DEV_CHECKOUT merge --ff-only task/adam-123`. Do not switch a shared checkout.
   A moved dev requires integrating that new base into the owned task worktree and
   fresh tests/review; conflicts stay isolated, never force/reset another task.
4. Push only if explicitly included in delivery scope, using normal non-force pushes
   and exact remote-head verification. Recheck source/target vectors between steps.
   Multi-repo delivery is **not atomic**: journal each completed repo; on conflict,
   test/push failure or uncertain result stop the remaining integrations, preserve
   every worktree/ref/evidence and reconcile actual refs before resuming. Never
   blindly replay a merge/push, automatically roll back published commits, or report
   whole-task success for partial delivery. Use `hold` for uncertain/partial outcomes;
   reconcile evidence before retry/resume. Only `finish --outcome completed` after
   actual delivery checks the candidate vector; it never substitutes for independent
   current acceptance. Queue release/recovery follows its contract.
5. Verify the delivered dev vector and task-wide behavior before handoff In Review,
   never Done. Capture actual evidence; historical receipt cwd values stay unchanged.

## Main promotion and cleanup

Main promotion is a **separate explicit user approval** of the exact reviewed repo
list and dev/main commit vector. Reacquire target reservations, recheck all approved
refs and tests, then promote those dev commits to their own main branches. A moved
ref, extra repo or changed scope invalidates approval: show the new vector and ask
again. Neither task creation, dev delivery, queue acquisition nor a previous approval
silently authorizes main, push or production deployment. Partial promotion follows
the same journal/stop/reconcile rules; no automatic rollback across repositories.

After verified delivery and reviewer release, inventory tracked/untracked/ignored
files and retain required private artifacts. Archive only released, clean, safely
delivered workspaces through Paseo; delete only safely merged task branches. Local
archival is bookkeeping, not permission to delete shared folders/files. Preserve
unfinished/dirty work and explicit retention exceptions; keep one primary workspace
at rest. The guard validates paths/provenance, not task-wide readiness, queue locking,
branch/base/title policy, user approval or post-launch filesystem writes.

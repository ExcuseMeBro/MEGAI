---
name: agent-worktree-lifecycle
description: Coordinate one folder/task across isolated Git-repo worktrees, verified dev delivery and separately approved main promotion.
managed-by: megai
---

# Hybrid task workspace lifecycle

One existing Paseo folder/project and one Plane task coordinate the work. Git
source writers use separate managed worktrees; non-Git configuration uses a local
owned scope. Workspaces do not imply new project/repository registration. Parents
own integration; children never delegate, mutate Plane, merge or promote. Every Git
change, however small, uses a task-owned managed worktree; direct source edits,
staging or commits in the dev/main checkout are forbidden.

## Pi verification mode

For Pi, `megai` selects routine or guarded verification before edits. Below,
independent review and formal acceptance apply to guarded work or stricter project
rules; routine work uses actual focused tests and parent self-review. Multi-repo
delivery and concurrency/shared-state changes are guarded. Workspace isolation,
backups, target reservations and approval boundaries apply in both modes. Load this
workflow for workspace/delivery operations, not on every implementation step.

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
   If isolated ownership cannot be proved, stop Git edits; never fall back to the
   primary dev checkout.
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

1. Preserve mode-appropriate review and actual acceptance for **all affected repos and
   configuration scopes before the first dev mutation**: routine Pi uses focused tests
   and parent self-review; guarded Pi (including multi-repo delivery) requires the
   independent formal gate. Other harnesses retain their required independent review.
   Commit only owned changes in task worktrees, then capture source-current evidence
   per worktree. Once ready, proceed to local dev delivery without an extra user
   confirmation; a task request already authorizes this step, not push or main.
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
   checkout and remote policy before mutating any repo. This parent-owned automatic
   dev merge is the only permitted task-related change in the primary dev checkout;
   never edit, stage or commit task source there. Record the exact source/dev
   commit vector. Integrate each ready task into its own existing dev checkout:
   `git -C DEV_CHECKOUT merge --ff-only --no-overwrite-ignore task/adam-123`.
   An ignored-file collision is a recoverable refusal, not permission to overwrite:
   preserve the named file in a verified private backup outside the checkout before
   retrying, and report its new location. Never delete it or switch a shared checkout.
   A moved dev requires integrating that new base into the owned task worktree and
   fresh tests/review; conflicts stay isolated, never force/reset another task.
4. Push only if explicitly included in delivery scope, using normal non-force pushes
   and exact remote-head verification. For Pi, only approved `main` pushes publish
   GitHub release notes, plus Forgejo only for ADAM (see Release notes for main
   pushes (Pi)). Other branch pushes do not create releases. Recheck source/target vectors between steps.
   Multi-repo delivery is **not atomic**: journal each completed repo; on conflict,
   test/push failure or uncertain result stop the remaining integrations, preserve
   every worktree/ref/evidence and reconcile actual refs before resuming. Never
   blindly replay a merge/push, automatically roll back published commits, or report
   whole-task success for partial delivery. Use `hold` for uncertain/partial outcomes;
   reconcile evidence before retry/resume. `reconcile --outcome resume` requires
   stopped-owner evidence and a new executor; every head must be the recorded base
   or candidate, all resources stay reserved, the token rotates, and only returned
   remaining repositories may proceed. Never replay already-delivered repositories.
   Only `finish --outcome completed` after
   actual delivery checks the candidate vector; it never substitutes for mode-appropriate
   current acceptance (independent formal evidence for guarded Pi; focused tests and
   self-review for routine Pi). Queue release/recovery follows its contract.
5. Verify the delivered dev vector and task-wide behavior, then automatically run
   **Post-merge cleanup** below without another user prompt, before handoff In Review,
   never Done. Do not clean up when delivery is partial or uncertain. Capture actual
   evidence; historical receipt cwd values stay unchanged.

## Release notes for main pushes (Pi)

Pi delivery policy: release notes are **main-only**. Only an approved push to
`refs/heads/main` triggers the release workflow below. Pushes to `pi`, `dev` and
`task/...`, any other branch, or tags alone do not create releases, release notes
or snapshot tags, and need no release-specific preflight. For mixed-ref pushes,
only the `main` ref gets a release. Normal push approval and remote-head verification
still apply to every pushed ref. Preserve existing releases and historical journals;
do not backfill non-main releases.

Push approval names the exact destinations, refs and the release/tag publication
authority; this rule grants no main/push approval. Required release destinations are
GitHub for every project, plus Forgejo only for ADAM and its component repositories.
Resolve ADAM membership from the verified existing umbrella project identity and
documented repository mapping (`ADAM full` in Plane); component repositories and
linked worktrees inherit that identity. Never infer ADAM membership from a branch
name, checkout basename or remote alias. Ambiguous identity is BLOCKED before
selecting destinations.

Non-ADAM projects (including SPMAPP and MEGAI) use GitHub only under this rule;
missing Forgejo does not block them. Do not preflight, create or register Forgejo
resources for non-ADAM projects. This scope rule grants no new push destination.

**Notes-only releases are sufficient.** Publish only the release body; do not upload
release assets. Do not build, package or upload binaries, archives, checksums or
evidence bundles solely to populate release
assets; missing attachments are not a blocker. Required tests and commit/tag/release
verification below still apply. Forge-generated source archives may appear
without manual uploads; leave them and any existing release assets unchanged.

Before a qualifying main push, preflight only the required destinations for authenticated access
and the existing target repo identity/remote, then draft the notes. A missing, unmapped or
unauthorized required forge is BLOCKED; never treat it as success, invent a
project/remote or expose private code to a new host. A queue reservation is not push
approval; the existing main/push approval boundary is unchanged.

1. Publish a **Release** for the same pinned commit on every required destination -
   release bodies, not merely commit or PR text. Record each destination's old/new
   full SHA and ref and summarize the actual verified pushed range. On a new ref, push
   from an explicitly selected baseline or a clearly identified initial-history scope;
   never assume `HEAD^`. A no-op (`old == new`) skips a new release but still
   reconciles any previously pending note.
2. Main pushes publish a notes-only **prerelease** snapshot, never latest. Tags
   follow the agreed release convention; never guess or increment a semantic version.
   The branch snapshot tag is
   `push/<ref-digest>/<full-new-commit-SHA>`, where `ref-digest` is the full 64
   lowercase hex SHA-256 of the exact fully qualified ref name's UTF-8 bytes (e.g.
   `refs/heads/main` -> `f921bd05e68b03740c450e565e0e6173e546193170b2dd404ddb6f153e9b5bf3`),
   with no newline, truncation or normalization. Look up an existing release by tag
   before creating; a conflicting tag identity is BLOCKED.
3. Group the whole approved push under one persisted push journal ID, created before
   any mutation and reused on every retry. Inside it keep one deterministic per-ref
   publication identity for `refs/heads/main`: the exact fully qualified ref plus
   its intended peeled commit, using the main snapshot tag above. Non-main refs in
   the same push have no release publication entry.
   Reuse that same per-ref identity on all required destinations and every retry; never mint a fresh
   ID for missing-side recovery.
4. Verify the remote ref first, then publish and read back the exact target commit,
   release bodies, status, the tag's peeled commit and URLs. A tag's peeled commit
   must equal the intended immutable commit; only a branch/ref target may move. An
   uncertain release create is reconciled by tag lookup before any retry.
5. Write short, simple release notes in plain language. Use a few brief bullets
   with meaningful emoji labels: ✨ changes, 🐛 fixes, ✅ actual tests, ⚠️ breaking
   changes/migration or risks, and 🔗 safe source links when useful. Include only
   relevant items; omit empty sections, boilerplate and long technical narratives.
   Emojis accompany clear text, never replace it. Preserve material warnings and
   required migration steps even when brevity needs an exception. Keep full SHA
   vectors and operational logs in the push journal rather than bloating the notes.
   Never copy secrets, PII or private tracker content into release notes.
6. An uncertain or partial push/publication stops and reconciles read-only: preserve
   the journal and queue, keep any published success on one forge, report push success
   separately from release failure, never roll back a successful push, and resume only
   the missing required destination without re-pushing successful refs, duplicating releases or
   overwriting human-written text.

This is agent instruction, not enforcement: MEGAI installs no git hook, and manual
pushes outside this workflow are not intercepted.

## Main promotion and cleanup

Main promotion is a **separate explicit user approval** of the exact reviewed repo
list and dev/main commit vector. Reacquire target reservations, recheck all approved
refs and tests, then promote those dev commits to their own main branches. A moved
ref, extra repo or changed scope invalidates approval: show the new vector and ask
again. Neither task creation, dev delivery, queue acquisition nor a previous approval
silently authorizes main, push or production deployment. Partial promotion follows
the same journal/stop/reconcile rules; no automatic rollback across repositories.

## Post-merge cleanup

Cleanup is part of delivery, not optional polish or a new approval round trip.
Automatically run it after verified task-to-dev integration, and again for remaining
task resources after separately approved main promotion. Do not keep a delivered
task workspace merely to wait for main: its commit and evidence must already be
preserved in dev and private artifacts.
An explicitly named persistent target such as MEGAI `pi` uses the same procedure
after verified delivery to that target; retain `pi` itself and any explicitly
retained workspace. This procedure grants no merge, main, push or remote-deletion
approval. It is agent workflow, not a Git hook or background cleanup service.

1. **Scope and preserve.** Use the same Plane task's recorded repo/workspace/ref
   vector, not a global merged-branch sweep. Protect primary workspaces, `dev`,
   `main`, `master`, named persistent branches and explicit retention exceptions.
   Confirm all-repo delivery and required push/release results first; partial,
   failed or uncertain delivery retains every task resource for reconciliation.
   Inventory tracked, untracked and ignored files, and preserve required drafts,
   logs, session/evidence bytes and recovery refs in verified private backups
   outside retiring paths. A clean `git status` alone does not cover ignored data.
2. **Release owners.** Finish mode-appropriate verification before retirement;
   task writers/reviewers must finish with saved final results and no follow-up work.
   From a retained parent checkout, pinned cleanup archives only that parent's idle
   direct children after checking their parent ID, cwd and pending permissions;
   never archive the invoking parent, another parent's child or an active agent.
   Release owned terminals and workspace services. Check
   current Paseo agents/terminals and Git worktree ownership. An idle agent is not
   proof of release; active, unknown or another task's owners require retention.
   Never archive the current parent workspace from inside its own retiring cwd:
   hand cleanup to a parent in the retained primary workspace. Keep historical
   receipt paths unchanged; retain the checkout if a pending check still needs it.
3. **Prove safe retirement.** Immediately before each mutation, recheck exact
   projectId/workspaceId, path/common-directory identity, branch tip, clean data
   inventory and released ownership. Require the recorded task tip to be an
   ancestor of every target required by this delivery stage, using
   `git merge-base --is-ancestor TASK_SHA TARGET_SHA`; recheck the target refs too.
   For dev-only delivery, verified dev is sufficient; approved main promotion
   requires the recorded promoted commit in main as well. Squash/rebase delivery
   without ancestry proof is retained for explicit reconciliation, not force
   deletion. Keep the applicable integration reservation through retirement;
   if already released, reacquire it and revalidate before deleting refs.
4. **Archive, then delete.** From a retained checkout, after all task owners
   are released and the reservation is held, run
   `pi-workflow cleanup --cwd PRIMARY --workspace EXACT_ID --branch task/SLUG --tip FULL_TASK_SHA`
   for each delivered task worktree. It automatically archives only verified idle
   direct children of the invoking parent, then rereads owner and terminal state.
   Unarchived foreign/unknown children and missing release evidence still block.
   Its local-`dev` ancestry check is sufficient
   for local dev-only delivery; remote `dev` is not a prerequisite unless the
   task separately approved a push. The command refuses busy agents, terminals,
   ignored/untracked data, moved refs and uncertain ownership, archives the exact
   Paseo workspace, reads back its absence, then deletes only the proven merged
   local branch. Record its JSON result or exact refusal. If workspace archival
   succeeded but branch deletion failed, keep the branch for read-only
   reconciliation; never invent a missing workspace to retry cleanup. An
   explicitly approved main promotion additionally requires main ancestry proof
   before retirement. Use supported Paseo `archive_workspace` only for the
   released, clean, safely delivered task workspace. Describe its current schema
   first; preserve required session/evidence bytes before archival. Verify it is
   inactive and its managed worktree is absent from both Git and the filesystem
   before deleting its task branch. Local-workspace archival is bookkeeping,
   not permission to delete shared folders/files. Never edit Paseo's registry
   or use `rm -rf`, force worktree removal or `git branch -D` as a fallback.
   Delete only the recorded safely merged local task branch with `git branch -d -- NAME`
   from a retained checkout; if Git refuses, retain and report it. Published task
   refs need explicit remote-deletion approval, fresh exact remote-tip/ancestry
   checks and race-protected deletion of that ref only; absent approval, keep them.
5. **Read back and hand off.** Recheck Paseo workspaces, Git worktrees and local
   (and authorized remote) refs. Record removed resources and retained resources
   with concrete reasons in the same Plane item. Leave one primary workspace at rest
   when this task has no unfinished work or retention exception; other tasks stay
   untouched. If archival/deletion fails or its result is uncertain, stop cleanup,
   preserve remaining resources and reconcile read-only before retrying. Report
   verified delivery separately from blocked cleanup; never claim cleanup complete
   with unexplained leftovers. Hand off In Review, never Done, with that outcome.

The guard validates paths/provenance, not task-wide readiness, queue locking,
branch/base/title policy, user approval or post-launch filesystem writes.

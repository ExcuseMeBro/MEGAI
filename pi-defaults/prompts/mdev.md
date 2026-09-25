---
description: Reconcile, review, merge and push task work to dev without repeated approval
---

Invoking `/mdev` is explicit authorization to reconcile, review, merge and push task work
into `dev` for the resolved project, plus safe **local** task branch/worktree cleanup.
Do not ask again for dev merge/push approval. Complete recoverable prerequisites rather
than merely reporting "blocked; preserved unchanged". This does **not** authorize main
promotion, force-push, remote task-branch deletion, extra Plane changes, or other projects/repos.

"All branches" means every eligible local `task/*` branch and registered task worktree
inside every repository in the resolved project. It does not include `main`, `dev`, a
configured preserve branch, a foreign/unknown repository, or a remote task ref (remote
task-ref deletion still needs separate approval). A monorepo has one repository ledger;
a multi-repo project has one independent ledger per configured repository.

**Never stop for a recoverable prerequisite**
Resolve each of these, continue, and report them as steps you completed:
- Local `dev` ahead of the remote, or anything listed in `pendingDelivery`: that is the work
  queue, not a blocker.
- Ignored or ignored-untracked files in a checkout (`ignored-untracked`, `ignored:*` status
  reasons): they never block the delivery decision, and they only keep that one workspace out
  of cleanup. They are still destructible: an ordinary fast-forward overwrites an ignored file
  whose path the task commit now tracks, so always merge with `--no-overwrite-ignore`. When
  that refuses, move the colliding ignored file aside to a preserved path, re-run, and report
  where it went; never delete it.
- Missing Plane identity for recorded task work: reuse the branch's existing identity, or
  create it once with `pi-workflow start --title "<task title>"` so the delivery has a home.
- Missing or stale evidence for the recorded SHA: obtain focused checks and parent
  self-review of that exact SHA, including corrections made after an earlier review.
  Treat verified task-owned tracked/untracked edits as unfinished task work: finish
  and commit only those changes in the owned worktree, then refresh acceptance on the new SHA.
  Never discard or silently omit them from a completion claim.
- Moved refs or a rejected non-force push: fetch, revalidate the new scoped snapshot and retry,
  at most three revalidation passes; report only if it keeps moving.
- Merge conflicts: resolve bounded conflicts through the approved worker, preserving both
  tasks' behavior.
Hold the affected row when ownership/scope is ambiguous, authentication or required evidence
is unavailable, focused checks fail, bounded recovery is exhausted, or the action is outside
this invocation's authority. Record the reason and continue independent rows. Never turn a
failed check into approval merely to finish the queue.

**Scope**
1. Load the `pi-workflow` skill. Run `pi-workflow context` at the invocation cwd. Grouped
   projects: cover every `repositories` entry and `preserveBranches`. Resolve the current
   project only - never scan all projects, home directories, or unrelated repos.
2. Preserve `main`, `dev`, and every configured persistent/protected branch (global + per-repo
   `preserveBranches`). Keep unknown or foreign work untouched.

**Inventory before any write**
3. Run `pi-workflow status` for the resolved repositories and use its `pendingDelivery`,
   `blocked` and `cleanupEligible` lists as the inventory; use `paseo workspace ls --json`,
   `paseo project ls --json` and bounded Git ref inspection only to fill gaps. Record per
   candidate: exact current SHA and existing review evidence, owning task/branch, worktree
   path, clean vs dirty, busy/active/locked state, and any unfinished Git operation. Treat
   `blocked` entries as diagnostics to resolve, never as a reason to stop.
4. Bind every candidate's readiness, test, and parent self-review evidence to its exact
   recorded SHA and merge diff. Stale/missing evidence is work to complete, not an
   automatic skip: obtain focused checks and current self-review, including corrections
   made after an earlier review. Never treat old review as final-SHA approval.
   Reuse valid evidence; use the approved implementation routing for needed fixes
   and checks. Missing runner support is not permission to change execution protocols.
5. Reconcile ownership against the existing Plane task identity, creating that identity when
   the recorded work has none. Plane access otherwise stays read-only here except the existing
   task's own delivery evidence and its **In Review** transition after step 9: never create a
   duplicate identity, never move other items, never set Done.
6. Never write into a foreign owner's checkout. For a dirty worktree, a busy/active/locked
   workspace, or an unfinished Git operation, integrate from another clean, exclusively owned
   checkout of the same recorded commits instead of stopping, and report which path was used.
   Never switch another owner's checkout, kill running work, force-reset or stash. Known
   task-owned unpublished or diverged commits are reconciliation work, not automatic blockers;
   inspect both histories and integrate only the recorded, scoped commits after checks/review.
   Unconfirmed workspace release blocks cleanup only, not delivery of an otherwise safe
   reviewed commit.

**Candidate ledger (before merge)**
6a. Build one candidate ledger for every configured repository before the first merge. Enumerate
every eligible task branch: all local `task/*` refs and all registered task worktrees, including candidates absent from
`pendingDelivery`; deduplicate the same repository/branch/HEAD, but never silently drop a
candidate because its workspace is dirty, busy, missing, or has no Plane receipt. Each row
must contain repository path, branch, exact HEAD, worktree/workspace path and id, ownership,
dirty/operation state, review/evidence state, remote-`dev` ancestry, merge result and cleanup
result. Sort rows deterministically by repository path, branch, then HEAD.
Also record local `dev` ahead of remote `dev` as a delivery-only row with its exact SHA:
it is protected from cleanup, not omitted from publication. Seed integration from fetched
remote `dev`, then reconcile this row before task rows; an already-reachable SHA is skipped.
Pinned commits from a dirty/busy task may be delivered, but its uncommitted work remains an
explicit unfinished row. Never label that entire task complete or archive its workspace.
6b. Treat the ledger as a queue, not a single all-or-nothing gate. A moved ref, missing
workspace, stale receipt, conflict, test failure, or cleanup failure is recorded against that
row and the run continues with the next candidate. The run must continue with the next repository even when
one repository has a held row. Only foreign ownership,
ambiguous scope, or a protected ref stops the affected write; never wait indefinitely for an
agent, workspace, lock, conflict resolver, or remote ref.

**Integrate serially without stalling**
7. Work in a safe, exclusively owned integration checkout for each repository; if the primary
`dev` checkout is dirty, busy, or shared, use a clean managed integration worktree and do not
switch or reset the primary. Refresh only approved remotes. For each ledger row, re-read the
exact HEAD and merge that SHA, never a moving branch name. Skip a SHA already reachable from
the current fetched remote `dev`.
7a. Record the last accepted integration SHA before each candidate. Attempt that candidate
in a disposable, task-owned clean integration worktree/branch based on that accepted SHA;
promote its result to the accepted ledger only after checks pass. Merge with
`git merge --no-edit --no-overwrite-ignore <candidate-sha>`: fast-forward when
possible, and create a normal merge commit when the task branch diverged. Never use `--ff-only`
for this all-candidates delivery loop; it is the reason independent task branches stall.
7b. On a conflict, run one bounded approved resolver attempt in the isolated integration
checkout. If it resolves, run focused acceptance and continue. If it cannot resolve, abort only
that candidate's merge, record `held: conflict` with the paths/reason, and immediately continue
with the next ledger row; do not sleep, poll, or wait for an unbounded child.
7c. If focused checks fail after a candidate, preserve the candidate worktree/branch, discard
only the isolated candidate integration state, record `held: verification`, and continue with
the next repository. A failure in one repository must not prevent safe candidates in other
repositories from reaching `dev`; report a partial vector instead of claiming all succeeded.
7d. Recheck candidate refs and remote `dev` before every publication. If a candidate moved or
non-force push is rejected by remote advancement, fetch and revalidate that row up to three
times, then record `held: moving-ref` and continue. Run combined acceptance and fresh
parent self-review for each repository's final SHA; unchanged baseline failures are
reported separately.
7e. Before any shared target mutation or push, load `megai`'s `integration-queue.md` and reserve
the exact validated target vector with `megai queue plan`, `enqueue`, and `claim`. For origin
remote-dev publication use `--remote-dev`; never use the dirty primary's current branch as an
implicit target. For another approved remote, use a queue mode that explicitly supports that
destination; missing support holds that publication rather than locking the wrong ref.
Dependent repositories for one task require all-repo acceptance and one atomic reservation;
independent tasks may proceed separately. Keep the lease live through publication and cleanup.
A wait, stale vector, or uncertain mutation follows the queue's refresh/hold/reconcile contract,
not an unreserved retry. After a remote advance, preserve both histories and revalidate the
combined result; never just retry the same rejected push. Journal each completed repository;
partial or uncertain publication retains the whole affected reservation until reconciled.
Publish each validated repository result by exact SHA
(`<validated-sha>:refs/heads/dev`) with an ordinary non-force push. Local `dev` may be
fast-forwarded with `git merge --no-edit --no-overwrite-ignore <validated-sha>` only in a
clean, exclusively owned checkout at the recorded head; otherwise leave the primary untouched
and report the isolated remote delivery. Never rewrite a target or switch another owner's branch.

**Cleanup only after proof**
8. Fetch and prove each exact validated commit is reachable from the remote `dev` first.
   Preserve the existing task's delivery receipt and evidence privately for cleanup and later
   Plane handoff. Do not set In Review until the task's cleanup attempts are accounted for.
9. Clean each delivered repository independently while its queue reservation is held.
   From a retained primary checkout invoke `pi-workflow cleanup --cwd PRIMARY --workspace
   EXACT_ID --branch task/SLUG --tip FULL_TASK_SHA`; its verified idle direct children are
   archived before the workspace and branch. For `/mdev` remote-dev delivery with a dirty
   primary, do not mutate that primary checkout to make this local-dev-only command pass:
   retain the row until local dev can be safely reconciled. A status `cleanupEligible: false`
   due only to remote-dev/local-dev disagreement is advisory, not a reason to skip a pinned
   cleanup after verified local delivery.
   Preserve task-owned ignored/generated data in a private 0700 backup outside the checkout
   with path, mode, content-hash inventory and read-back before moving it; never erase or
   relocate unverified, foreign or ambiguous content. Rerun the pinned cleanup after a safe
   backup. For dirty tracked/untracked task source, finish it as task work with new acceptance
   before delivery; a non-task or uncertain change is retained. A missing archived workspace
   with a leftover branch is reconciled only against the existing recorded workspace/archive
   receipt, exact SHA and current dev ancestry under reservation; otherwise retain it, never
   invent provenance. No force removal, reset, stash or global merged-branch sweep.
   Cleanup failure for one row must not stall independent rows; cleanup each delivered repository independently.
   Record its exact reason and continue. Keep the invoking parent workspace, foreign/unknown/busy/dirty work, protected
   branches and all remote task branches. Finally store each task's complete delivery and
   cleanup result in Plane (`pi-workflow review`) and move only that task to **In Review**;
   never Done here — Done requires verified `main` via `pi-workflow done`.
   Complete/release the queue reservation only after verified delivery and accounted cleanup.
10. Report a complete per-repository ledger: merged, held, skipped, cleaned and retained rows;
    exact validated commits; workspace/branch resources removed; and every reason. Do not
    re-review unchanged evidence, and do not call the run complete while any eligible row is
    unaccounted for.

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
- Missing or stale evidence for the recorded SHA: obtain the focused checks and a fresh
  independent GPT review of that exact SHA, including any corrections made after an earlier
  review.
- Moved refs or a rejected non-force push: fetch, revalidate the new scoped snapshot and retry,
  at most three revalidation passes; report only if it keeps moving.
- Merge conflicts: resolve bounded conflicts through the approved worker, preserving both
  tasks' behavior.
Stop only for: a write that would touch work owned by someone else, an ambiguous
product/ownership decision, or an action this invocation does not authorize (main promotion,
force, remote branch deletion, other projects/repos).

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
4. Bind every candidate's readiness, test, and review evidence to its exact recorded SHA and
   merge diff. Stale/missing evidence is work to complete, not an automatic skip: obtain
   focused checks and fresh independent GPT review of the current recorded SHA, including
   corrections made after an earlier review. Never treat the old review as final-SHA approval.
   Reuse valid evidence; use the approved DeepSeek execution / GPT review routing for needed
   fixes and checks. Missing runner support is not permission to change execution protocols.
5. Reconcile ownership against the existing Plane task identity, creating that identity when
   the recorded work has none. Plane access otherwise stays read-only here except the existing
   task's own delivery evidence and its **In Review** transition in step 8: never create a
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
7a. Merge with `git merge --no-edit --no-overwrite-ignore <candidate-sha>`: fast-forward when
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
times, then record `held: moving-ref` and continue. Run combined acceptance and fresh review
for each repository's final SHA; unchanged baseline failures are reported separately.
7e. Publish each validated repository result by exact SHA
(`<validated-sha>:refs/heads/dev`) with an ordinary non-force push. Local `dev` may be
fast-forwarded with `git merge --no-edit --no-overwrite-ignore <validated-sha>` only in a
clean, exclusively owned checkout at the recorded head; otherwise leave the primary untouched
and report the isolated remote delivery. Never rewrite a target or switch another owner's branch.

**Cleanup only after proof**
8. Fetch and prove each exact validated commit is reachable from the remote `dev` first. Then
   store the per-task multi-repository delivery receipt/evidence under the existing Plane
   identity (`pi-workflow review`) and move only that task to **In Review**; never Done here -
   Done requires verified `main` via `pi-workflow done`.
9. Clean each delivered repository independently after its exact validated SHA is reachable
   from remote `dev`. Archive released, clean, task-owned Paseo workspaces with the documented
   manager (`paseo workspace archive`), never `rm -rf`; then use ordinary non-force
   `git worktree remove` / `git branch -d` only for the unchanged local task branch proven
   merged into remote `dev`. Cleanup failure for one row must not stall cleanup of other rows;
   cleanup each delivered repository independently.
   Keep the current workspace, foreign/unknown/busy/dirty work, protected branches and all
   remote task branches. A workspace retained because it holds ignored or unreleased data is
   reported as retained, not as a reason to stop delivery.
10. Report a complete per-repository ledger: merged, held, skipped, cleaned and retained rows;
    exact validated commits; workspace/branch resources removed; and every reason. Do not
    re-review unchanged evidence, and do not call the run complete while any eligible row is
    unaccounted for.

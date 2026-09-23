---
description: Reconcile, review, merge and push task work to dev without repeated approval
---

Invoking `/mdev` is explicit authorization to reconcile, review, merge and push task work
into `dev` for the resolved project, plus safe **local** task branch/worktree cleanup.
Do not ask again for dev merge/push approval. Complete recoverable prerequisites rather
than merely reporting "blocked; preserved unchanged". This does **not** authorize main
promotion, force-push, remote task-branch deletion, extra Plane changes, or other projects/repos.

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

**Integrate serially**
7. Work in a safe, exclusively owned checkout; isolate integration if a checkout is shared.
   Refresh only approved remotes. Compare local and remote `dev`; local ahead is not a blocker.
   Account for every unpublished commit, reuse its existing Plane identity and verify/review
   it before publication. If histories diverged, reconcile known scoped work without rewriting
   history; stop only for unknown ownership or out-of-scope changes needing an owner decision.
   Recheck candidate refs, then merge recorded reviewed SHAs one at a time, never live branch
   names. Skip a commit already reachable from the fetched remote `dev`; no duplicate merge.
   Resolve bounded integration conflicts through the approved worker, preserving both tasks'
   behavior; ask only for ambiguous product/ownership decisions, not ordinary merge permission.
   Run acceptance checks on the combined result and obtain independent GPT review of its exact
   final SHA. Fix introduced regressions and rerun affected checks/review. Demonstrably unchanged
   baseline failures must be reported separately, never described as a green full suite.
   Recheck refs before publication. If a candidate moved or a non-force push is rejected due to
   remote advancement, fetch and revalidate the new scoped snapshot and retry, at most three
   passes; report only if refs keep moving or safe reconciliation needs owner input, preserving
   the integration.
   Fast-forward local `dev` with `git merge --ff-only --no-overwrite-ignore` only if its
   checkout is clean, exclusively owned and still at the recorded head; never rewrite it or
   switch someone else's branch. Publish the exact validated
   commit by SHA (`<validated-sha>:refs/heads/dev`) with an ordinary non-force push. If local `dev`
   cannot safely be updated, retain the isolated integration and report that separately from
   verified remote delivery. Genuine unresolved regressions, unsafe state or infrastructure
   failures stop only the affected repository; preserve work and report the concrete blocker.

**Cleanup only after proof**
8. Fetch and prove each exact validated commit is reachable from the remote `dev` first. Then
   store the per-task multi-repository delivery receipt/evidence under the existing Plane
   identity (`pi-workflow review`) and move only that task to **In Review**; never Done here -
   Done requires verified `main` via `pi-workflow done`.
9. Clean only workspaces that are released, clean, task-owned, at a fresh unchanged head with
   recorded ownership, and whose reviewed SHAs are all on pushed `dev`. Use the documented
   Paseo manager for Paseo workspaces (`paseo workspace archive`), never `rm -rf`. Use ordinary
   non-force `git worktree remove` / `git branch -d` only when appropriate. Keep the current
   workspace, foreign/unknown work, and all remote branches. A workspace retained because it
   holds ignored or unreleased data is reported as retained, not as a blocked run.
10. Report per repository: merged / skipped / retained, the exact validated commits, and why.
    Do not re-review unchanged evidence.

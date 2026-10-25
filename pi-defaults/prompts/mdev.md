---
description: Reconcile, review, merge and push verified task work to dev
---

Invoking `/mdev` explicitly authorizes reviewed task delivery to `dev` and an ordinary non-force push to `origin/dev` for the resolved project. It does not authorize main promotion, a force push, remote task-branch deletion, or changes to another project.

**Drive the sweep; do not re-derive a ledger by hand.** Load `pi-workflow`, run `pi-workflow context` and read the reported rules and `.pi/project.json`, then work in three steps:

1. `pi-workflow mdev scan` is the read-only ledger: every configured repository, its fetched and local `dev`, and one row per task branch with exact SHA, checkout path, clean/dirty/ignored state, writer activity and the Plane task number. Cross-check it against `git worktree list --porcelain` before trusting an "idle" row; a checkout you cannot attribute is owned by someone else.
2. `pi-workflow mdev run --check "<focused command>"` performs the delivery pass: it adopts an inactive dirty checkout after a private backup, merges each exact task SHA on `dev` with `git merge --no-ff --no-overwrite-ignore`, restores `dev` when the post-merge check fails, pushes non-force only that verified tip to `refs/heads/dev`, confirms the advertised and freshly fetched heads agree, writes the receipt and evidence to the Plane task, moves it to In Review, and then retires every branch and worktree it proved merged.
3. Read the report instead of re-deriving it: `merged`, `adopted`, `plane`, `pending_plane`, `retained`, `resources`, `pushed`. Run the sweep again while rows still make progress, and stop only when the remaining rows carry a concrete retained reason.

**Own the blockers.** You are the operator: a retained row is work for you, not a reason to stop, and one blocked row never cancels the others.

- Merge conflict: resolve it in that task's own checkout when the conflicting files belong to that task, re-run the focused checks on the resolved SHA, then run the sweep again. Never resolve by dropping the other side of the history.
- Missing acceptance: run the checks yourself. Tracked or untracked task source needs its own task acceptance, and an old receipt for a different SHA is not evidence; guarded tasks require a source-current formal PASS before integration.
- Plane timeout, 5xx, dropped connection or malformed stream: the sweep retries transient transport failures and journals a hand-off it could not prove. Run `pi-workflow mdev resume` once connectivity returns; never replay a whole boundary blindly and never invent a state you did not read back.
- Rows the report retains: Retain active, dirty, unknown or unmerged resources with the reported reason.
  The shared `dev` checkout is the operator's own directory: fresh writes or an open session there never blocked the
  sweep, only a held lock or an in-progress Git operation does. uncertain ownership, a Git lock, an in-progress operation or an active writer on that exact checkout is not permission to force anything. An open session or a cwd inside a repository is not by itself a blocker; uncommitted work there is.
- A separate writer needs coordination: reserve the exact repository vector with `megai queue plan`, `enqueue` and `claim` under the existing Plane pair. The sweep's own lock (`megai-mdev.lock`) is exclusive only within one repository, and neither mechanism grants approval beyond this invocation.

Report a ledger of merged, held and retained rows with their exact SHAs, the checks you ran and every Plane task identifier you moved to In Review. `/prdev` owns the `dev` -> `main` pull request; `/rwbrowser` stays user-invoked unless the task's acceptance already requires browser evidence.

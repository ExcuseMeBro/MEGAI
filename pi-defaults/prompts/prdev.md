---
description: Open or reuse the dev-to-main pull request for the current project (no merge)
---

Invoking `/prdev` explicitly authorizes a necessary non-force push of verified `dev` and
creating or reusing a `dev` -> `main` pull request. Do not ask again for those actions. It never authorizes
merging or pushing `main`, never authorizes cleanup or branch deletion, and never touches
another project.

**Never stop for a recoverable prerequisite**
Complete each of these and continue; report each per repository:
- No forge in `.pi/project.json`: derive the host from the `origin` remote URL (`github.com` ->
  `gh`, `gitlab.com` -> `glab`) and use the installed authenticated CLI for that host.
- Several remotes or a fork: honor explicit project forge/destination policy first, then the
  verified branch push remote, then `origin`. Resolve head and base repository identities;
  a fork must never silently redirect a push or PR to another project.
- Missing evidence for the captured `dev` SHA: produce it (focused checks plus parent
  self-review of that exact SHA) and store it on the existing Plane task identity with
  `pi-workflow review` before the pull-request write. Absent evidence is work, not a blocker.
- Moved refs: re-fetch and revalidate, at most three passes, then publish the now-stable SHA.
- `dev` identical to `main`: report "no pull request needed" as a completed result.
Unusable authentication, an unsupported host, ambiguous destination, missing required evidence,
failed checks, missing branches or exhausted ref retries hold that repository with a concrete
reason, without abandoning independent repositories. Continue prerequisites only while safe;
never publish unverified work because the prompt says to recover.
Never invent success: evidence must cover the exact published SHA.

**Resolve**
1. Load `pi-workflow` and run `pi-workflow context` at the invocation cwd. Cover every
   configured repository. Take the forge and remote from that context and local config
   (`.pi/project.json`), falling back to the derivation above when the config is silent.
2. Use the installed, authenticated forge CLI matching the host (`gh` for GitHub, `glab` for
   GitLab). Inspect its help once when the exact syntax is unknown, then reuse that result.

**Verify before any write**
3. Fetch and inspect fresh remote refs, then capture the exact proposed `dev` SHA and the exact
   remote `main` base SHA for each repository. Preserve any dirty or busy checkout: no
   automatic commit, stash, reset, or rebase. Use another clean checkout of the same SHA when
   the current one is unavailable, instead of stopping.
   Use the fetched remote `dev` when local `dev` is absent or behind it. Use local `dev` when
   it is ahead and its exact SHA passes verification. Diverged histories need `/mdev` or
   separately authorized reconciliation; this command never silently rewrites either side.
   If remote `main` is missing, report that fact; do not create it.
   Compare the captured heads before creating Plane work or collecting new evidence:
   `git rev-list --count <main-sha>..<dev-sha>` equal to zero is a completed no-op.
4. Require delivery, test, and parent self-review evidence that covers that `dev` SHA and the `dev`-versus-
   `main` diff, attached to the existing Plane task identity, captured before any push or PR
   write. Create the identity and that evidence when they are missing; never invent success.
5. Compare the captured `dev` SHA with that `main` base. No commits in that diff means no PR;
   report that as a completed result rather than creating an empty one.

**Publish**
6. Recheck both refs immediately before publication. If either moved, revalidate the evidence
   against the new heads and retry, at most three passes, rather than publishing a PR that no
   longer matches its proof.
7. If `dev` genuinely must be pushed, reserve the exact target with `megai queue` under the
   existing Plane identity (`--remote-dev` for origin), using its documented lease and recovery
   rules. Another remote requires a queue mode supporting that explicit destination; otherwise
   hold the push. Push only `<validated-sha>:refs/heads/dev` with an ordinary
   non-force push and then verify remote `dev` is exactly that SHA. A ref that keeps moving
   after the revalidation passes stops and reports; never force, reset, or rewrite.
   Finish the reservation after remote verification; uncertain results use hold/reconcile.
8. Look up an **OPEN** PR by exact base repository + `main`, head repository + `dev`.
   Reuse its URL after verifying its current head SHA and base SHA against captured evidence.
   A stale head/base is a revalidation case, never a reason to create a duplicate PR. If more
   than one exact match exists, report the ambiguity. Create only after a successful complete
   lookup proves no open match. After an uncertain create, look up that same identity before
   retrying. Closed/merged PRs do not count as open matches.
   Use the explicit correct remote/project and branch direction, a concise diff-based summary,
   and actual test results. Pass multiline bodies through a structured API or `--body-file`.
   Read back the returned PR's URL, state, repositories, branch direction and head/base SHAs.
   Ref drift triggers the same three-pass revalidation budget, not an unqualified success.
9. Return the PR URL per repository, or the concrete reason and its remediation per repository.
   Keep private repository text and credentials out of the PR body; no broad public search.

**Boundaries**
10. A pull request is not main delivery: retain the existing Plane task identities in
    **In Review** and do not mark them Done, do not merge, and do not delete branches.

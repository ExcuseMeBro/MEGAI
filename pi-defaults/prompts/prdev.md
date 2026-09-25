---
description: Open or reuse the dev-to-main pull request for the current project (no merge)
---

Invoking `/prdev` authorizes exactly two things: pushing verified `dev` only if that push is
needed and already authorized, and creating a `dev` -> `main` pull request. It never authorizes
merging or pushing `main`, never authorizes cleanup or branch deletion, and never touches
another project.

**Never stop for a recoverable prerequisite**
Complete each of these and continue; report each per repository:
- No forge in `.pi/project.json`: derive the host from the `origin` remote URL (`github.com` ->
  `gh`, `gitlab.com` -> `glab`) and use the installed authenticated CLI for that host.
- Several remotes or a fork: prefer `origin`, then the remote the tracked branch pushes to, then
  the project's own configuration. This is resolution work, not a reason to stop.
- Missing evidence for the captured `dev` SHA: produce it (focused checks plus parent
  self-review of that exact SHA) and store it on the existing Plane task identity with
  `pi-workflow review` before the pull-request write. Absent evidence is work, not a blocker.
- Moved refs: re-fetch and revalidate, at most three passes, then publish the now-stable SHA.
- `dev` identical to `main`: report "no pull request needed" as a completed result.
Only a genuinely unusable authentication state, or a host with no usable CLI, is reported as a
concrete blocker for that one repository, without abandoning the other repositories.
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
4. Require delivery, test, and parent self-review evidence that covers that `dev` SHA and the `dev`-versus-
   `main` diff, attached to the existing Plane task identity, captured before any push or PR
   write. Create the identity and that evidence when they are missing; never invent success.
5. Compare the captured `dev` SHA with that `main` base. No commits in that diff means no PR;
   report that as a completed result rather than creating an empty one.

**Publish**
6. Recheck both refs immediately before publication. If either moved, revalidate the evidence
   against the new heads and retry, at most three passes, rather than publishing a PR that no
   longer matches its proof.
7. If `dev` genuinely must be pushed, push only the validated commit with an ordinary
   non-force push and then verify remote `dev` is exactly that SHA. A ref that keeps moving
   after the revalidation passes stops and reports; never force, reset, or rewrite.
8. Reuse an existing **OPEN** PR only when it matches exactly: same repository, base `main`,
   head `dev` at the same captured SHA. Otherwise create one with the explicit correct
   remote/project and branch direction, a concise diff-based summary, and the actual test
   evidence and results.
9. Return the PR URL per repository, or the concrete reason and its remediation per repository.
   Keep private repository text and credentials out of the PR body; no broad public search.

**Boundaries**
10. A pull request is not main delivery: retain the existing Plane task identities in
    **In Review** and do not mark them Done, do not merge, and do not delete branches.

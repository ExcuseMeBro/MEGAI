---
description: Open or reuse the dev-to-main pull request for the current project (no merge)
---

Invoking `/prdev` authorizes exactly two things: pushing verified `dev` only if that push is
needed and already authorized, and creating a `dev` -> `main` pull request. It never authorizes
merging or pushing `main`, never authorizes cleanup or branch deletion, and never touches
another project.

**Resolve**
1. Load `pi-workflow` and run `pi-workflow context` at the invocation cwd. Cover every
   configured repository. Take the approved forge and remote from that context and local
   config (`.pi/project.json`); ambiguous remotes (multiple candidates, fork upstream) or
   missing credentials are a blocker - stop and report instead of guessing.
2. Use the installed, authenticated forge CLI matching the host (`gh` for GitHub, `glab` for
   GitLab). Inspect its help once when the exact syntax is unknown, then reuse that result.

**Verify before any write**
3. Fetch and inspect fresh remote refs, then capture the exact proposed `dev` SHA and the exact
   remote `main` base SHA for each repository. Preserve any dirty or busy checkout: no
   automatic commit, stash, reset, or rebase.
4. Require delivery, test, and review evidence that covers that `dev` SHA and the `dev`-versus-
   `main` diff, attached to the existing Plane task identity, captured before any push or PR
   write. Missing or SHA-mismatched evidence is a blocker; never invent success.
5. Compare the captured `dev` SHA with that `main` base. No commits in that diff means no PR;
   report that rather than creating an empty one.

**Publish**
6. Recheck both refs immediately before publication. If either moved, stop and revalidate the
   evidence against the new heads rather than publishing a PR that no longer matches its proof.
7. If `dev` genuinely must be pushed, push only the validated commit with an ordinary
   non-force push and then verify remote `dev` is exactly that SHA. Divergence or a moved ref
   stops and reports; never force, reset, or rewrite.
8. Reuse an existing **OPEN** PR only when it matches exactly: same repository, base `main`,
   head `dev` at the same captured SHA. Otherwise create one with the explicit correct
   remote/project and branch direction, a concise diff-based summary, and the actual test
   evidence and results.
9. Return the PR URL per repository, or the blocker and reason per repository. Keep private
   repository text and credentials out of the PR body; no broad public search.

**Boundaries**
10. A pull request is not main delivery: retain the existing Plane task identities in
    **In Review** and do not mark them Done, do not merge, and do not delete branches.

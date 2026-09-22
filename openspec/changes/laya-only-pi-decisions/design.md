## Context

See `proposal.md` for motivation and `specs/local-laya-decisions/spec.md` for observable requirements. Current `dev` already contains the core local Laya runtime and patch-equivalent installer hardening. Three pending Laya policy refinements and four independent workflow-status commits remain on separate branches. A separate legacy-only branch must remain untouched. The active local Pi profile still loads retired extensions even though its defaults already expect Laya.

The change affects installer and workflow policy, so it uses guarded acceptance, one isolated task worktree, an independent read-only review and queue-controlled `dev` integration. Private profile backups and historical session transcripts are user data and are not purge targets.

## Goals / Non-Goals

**Goals:**
- Produce one reviewed task commit lineage containing every applicable pending change, with Laya refinements integrated before unrelated workflow-status work.
- Leave the final tracked tree and active local profile Laya-only, with no retired implementation or descriptive artifacts.
- Preserve the legacy-only branches, Git history, private backups and session transcripts without exposing them as active resources.
- Verify Laya behavior, workflow-status behavior, source cleanliness and installed-profile cleanliness before `dev` delivery.

**Non-Goals:**
- Rewriting Git history or deleting legacy-only branches.
- Deleting private backups or session transcripts.
- Adding a compatibility alias, hosted fallback or second runtime.
- Promoting to `main` in this task stage.

## Decisions

### Integrate by dependency order rather than merging every branch head

Apply the three unique Laya refinement commits first. Do not replay the installer-fix branch because `git cherry` shows its two commits are patch-equivalent to `dev`. Apply the four workflow-status commits only after the Laya layer is settled. The legacy-only branch is excluded.

This preserves useful commit provenance without importing obsolete work or creating duplicate patches. A single squash was rejected because it would hide which reviewed branch changes were retained.

### Make the final tree strictly Laya-only

Delete legacy-only files and directories, then remove legacy names and migration behavior from mixed installer, policy and verification files. Rename this OpenSpec change to a Laya-only path. Final verification performs an exhaustive case-insensitive tracked-tree scan for the retired tool name and related package identifiers; zero matches are required.

Keeping historical benchmark documents in the final tree was rejected by explicit user direction. Git history and the untouched legacy branch provide the archive without keeping dead artifacts in `dev`.

### Separate source cleanup from local profile cleanup

The repository installer becomes Laya-only and does not retain one-time migration guards. For the current machine, first copy active resources that will change into a private timestamped backup, then remove only active retired extensions/prompts/configuration and run the verified Laya profile installer. Do not alter session logs or existing backup directories.

This avoids permanent migration code for a one-time local cleanup and prevents accidental data loss.

### Keep Laya runtime safety checks

Retain pinned runtime ownership, interpreter/version/lock validation, two-checkpoint verification, one shared session process, bounded local requests and fail-open advisory behavior. The pending Laya refinements that preserve custom operator policy and order activation after profile resources remain required.

### Deliver to `dev` only after guarded acceptance

Focused tests cover runtime/policy installation, active source scope and workflow status. Final evidence also proves commit order, exhaustive absence in tracked source, Laya presence and retired-tool absence in the active local profile. A fresh read-only reviewer evaluates the exact committed candidate and evidence. Queue-controlled fast-forward integration targets `dev`; `main` needs a later explicit approval of the exact vector.

## Risks / Trade-offs

- **Removing historical tracked artifacts reduces in-tree context** → preserve them in Git history and the untouched legacy branch.
- **Branch commits may conflict after Laya refinements** → resolve only in the isolated task worktree and rerun affected tests; never modify source branches.
- **One-time local cleanup can remove operator files accidentally** → limit it to identified active resources, back them up privately first, and preserve sessions/backups.
- **An exhaustive name scan can flag unrelated prose** → every match is reviewed; the final requirement is intentionally zero tracked matches.
- **`dev` may move during review** → rebase or merge the new `dev` base into the task worktree, recapture evidence and review before queue delivery.

## Migration Plan

1. Update and validate this Laya-only OpenSpec contract.
2. Apply the unique Laya refinement commits and verify their focused tests.
3. Apply the workflow-status commits and verify their focused tests.
4. Remove all tracked retired-stack artifacts and references; update mixed installers/tests for Laya-only behavior.
5. Run focused suites, Ruff on changed Python, strict OpenSpec validation and exhaustive tracked-tree scans.
6. Commit the candidate, capture guarded acceptance evidence and obtain source-current independent review.
7. Under an integration-queue reservation, fast-forward the accepted candidate to `dev` and verify the exact commit.
8. Back up affected active local Pi resources, apply the delivered Laya-only profile and verify loaded tools/resources plus exhaustive active-profile absence.
9. Hand the Plane item to In Review. Stop before `main` promotion.

Rollback before `dev` delivery is discarding the task worktree. After `dev` delivery, use a new reviewed revert commit; never rewrite shared history. Local profile rollback uses the private backup only if the Laya-only install fails and requires explicit reconciliation before any later promotion.

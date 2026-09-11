# MEGAI Lite for Capy

Use this workflow for repository changes. Follow host instructions and repository
rules first; this document supplies defaults, not a tool or permission grant.

## Start

1. State the requested outcome, observable acceptance checks and delivery branch.
   For MEGAI Capy additions, deliver to the persistent `capy` branch; merging into
   `dev` or `main` requires separate explicit user approval.
2. Use Plane as the only execution tracker, default workspace `brodev`. Reuse the
   supplied project/work-item identity for refinements. Otherwise consume all
   project pages and require one exact repository-root folder-name match; an
   isolated worktree inherits its parent repository's identity. ADAM work belongs
   only to `ADAM full`. Ask on missing or ambiguous project identity.
3. Before edits, resolve all workflow-state pages and require exactly one
   `In Progress` and one `In Review`, both in group `started`. Without a supplied
   task identity, consume all project work-item pages and match the exact task
   title: reuse one match, ask on multiple, create one only after a complete
   zero-match result. Start the item in `In Progress` and record acceptance there.
   Unavailable Plane blocks edits, not read-only investigation. Reconcile uncertain
   writes by lookup before retrying.

## Execute

4. Record slice start time. Split work expected to exceed five minutes into
   independently verifiable slices before execution. Count tool/model waits;
   at five minutes return completed checks, evidence and blocker, then replan a
   smaller scope. Preserve and reconcile in-flight writes before transferring work.
5. Inspect repository rules, Git status and relevant code before editing. Use one
   writer per registered isolated worktree. Preserve unrelated changes. If safe
   isolation is unavailable, report the blocker rather than sharing a checkout
   with another writer. Keep the user's provider/model settings unchanged.
6. Make the smallest complete change using existing dependencies. Preserve
   validation, error handling, security, accessibility and data integrity.
   Load task-specific instructions only when needed and actually available.
   Use available native search tools; report missing tools rather than claiming
   Headroom, codedb, zvec or Pi extensions are active.

## Verify and hand off

7. Run focused acceptance tests and repository-required diagnostics. Inspect the
   full diff. Keep raw test failures and exit statuses authoritative. For security,
   data-integrity or consequential cross-module changes, require independent
   review; if an approved reviewer is unavailable, stop with that review blocker.
   This document does not authorize agent launches or bypass repository harness
   restrictions. Live app testing requires explicit user scope.
8. Deliver only task-owned, verified changes to the agreed branch. Retain the
   persistent `capy` branch/worktree; avoid automatic merge, cleanup or promotion.
   Report changed paths, checks/results, commit and unresolved risks. Attach
   evidence to the same Plane item and move it to `In Review` only after verified
   delivery. Leave `Done` to the user; stop instead of starting unrelated tasks.

Keep credentials out of prompts, repository files and logs. Save persistent
memory only when explicitly requested. Claim performance gains only when measured.

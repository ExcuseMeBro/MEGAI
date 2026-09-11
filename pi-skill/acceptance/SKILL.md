---
name: megai-acceptance
description: Freeze acceptance before Pi implementation; after changes require source-current test/runtime evidence and fresh independent Pi verification before handoff. Use for implementation, acceptance review, and blocked or stale verification.
managed-by: megai
---

# Pi acceptance gate

Parent-owned workflow; leaves inherit the frozen criteria and never mutate Plane,
delegate or integrate. Follow repository rules and user resource exclusions.
Read [reference.md](reference.md) when preparing a contract, capturing commands,
assembling evidence, or invoking the checker. This is an evidence gate, not a
security sandbox or a replacement execution tracker.

## Before implementation

1. Start/reuse the linked Plane item. Define observable outcomes, error cases and
   regression boundaries with the user. Map every required outcome to a named
   criterion and a bounded test or runtime command. Load relevant engineering or
   UI/a11y guidance; avoid unrelated full-suite work.
2. The parent prepares a task-specific contract outside the source checkout,
   records its exact SHA256 and acceptance in the same Plane item, and gives the
   implementer only that approved contract. A changed requirement requires parent
   reconciliation and a newly approved hash; implementers cannot silently waive it.
3. Product behavior changes require a relevant real runtime check: an existing
   browser/E2E flow, API with isolated test data, CLI invocation or equivalent.
   A documentation/static-only task may declare runtime unnecessary with an
   explicit rationale. Missing prerequisites are BLOCKED, not an excuse to waive
   a required check. Test count/coverage or an LLM score alone is not acceptance.
4. Live tests need explicit user-approved local/staging scope, targets and test
   identities. Record authorization in the contract before execution. A request
   to install this workflow is not blanket permission for future live tests.
   Never run production mutations, real payments/messages or destructive cleanup.

## After implementation

5. Freeze the candidate source snapshot, including uncommitted/nonignored files.
   Keep evidence outside the checkout. Run original bounded test commands through
   `megai acceptance run`; preserve raw logs, actual exits and before/after source
   hashes. Do not soften failed tests or replace runtime behavior with mocks.
   For browser flows, run the repository's existing E2E command (for example an
   already-installed Playwright suite); Paseo browser observations/screenshots may
   supplement receipts. No browser capability is installed or invented here.
6. Verify the running build is from that same snapshot and record environment,
   target, actions, expected result and observed result. Check the actual outcome
   (for example save then reload), not just that a button was clicked. Include
   relevant error/loading/empty, permission, mobile and keyboard scenarios when
   required by the task. A screenshot without an observed outcome is insufficient.
7. Obtain a fresh independent Pi verifier through the approved delegation path.
   First send neutral READY, verify Pi harness/exact model/effective high thinking,
   then send frozen contract/hash, candidate snapshot/diff and raw evidence, not
   the implementer's reasoning transcript. Prefer Sol/high per MEGAI review policy.
   The verifier has read-only source authority, may perform authorized bounded
   checks in isolation, and reports each criterion plus reproducible findings.
   Preserve actual status metadata and the review as a hashed artifact. If the
   approved route or reviewer is unavailable, report BLOCKED; no self-review label.

## Decide and stop

8. Assemble evidence and run `megai acceptance check` with the hash retrieved from
   Plane, not a newly computed replacement. All criteria must have observations,
   matching command receipts and a source-current independent review. PASS allows
   verified delivery to the agreed branch and Plane In Review, never Done.
   FAIL requires fixes; BLOCKED requires the named missing evidence or prerequisite.
   Report the criterion → command/action → outcome → artifact mapping to the user.
9. Changes after verification invalidate affected evidence; the checker is
   deliberately conservative and invalidates the whole source snapshot. Re-run
   checks/review after fixes, rather than copying a previous PASS. Work in slices
   targeting at most five minutes; checkpoint at the deadline and replan. Preserve
   in-flight non-interruptible writes. Avoid unbounded repair/review loops.

Keep credentials and private data out of commands and public artifacts. Raw logs
stay private; review/redact exports and bind any sanitized copies to their own
hashes. Missing or excluded resources remain visible blockers. Native Pi settings,
provider/model catalog and user opt-outs remain unchanged.

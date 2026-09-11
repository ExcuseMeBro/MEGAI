---
name: megai-acceptance
description: Freeze task acceptance, reproduce bugs, collect source-current evidence and obtain independent Pi review before handoff. Use for implementation, bug fixes, review findings and blocked or stale verification.
managed-by: megai
---

# Pi acceptance gate

Parent owns the contract and Plane identity; leaves inherit both, never delegate,
mutate Plane or integrate. Load this workflow once per task; reuse it at handoff.
Read [reference.md](reference.md) when preparing contracts, recording a regression,
collecting evidence or assembling review. This gate is not a sandbox or tracker.

## 1. Freeze the task

Start/reuse the linked Plane item. Name observable outcomes, error cases and
regression boundaries; bind each to a bounded command that asserts the outcome.
Use schema 2: classify `bugfix`, `change` or `docs`. Product behavior requires a
real CLI/API/browser check; static-only work needs an explicit runtime rationale.
Live tests require user-approved local/staging targets and isolated identities.
Missing prerequisites mean BLOCKED; production mutations, real payments/messages
and destructive cleanup remain outside scope.

For **bugfix**, first reproduce the reported failure and capture the regression
command with `run --test-file`. Inspect its actual assertion failure, not a missing
dependency, timeout or unrelated error. Bind that red receipt, exact expected exit
and failure signature into a regression criterion. The same test files and command
must pass after the fix. Freeze the parent-approved contract bytes outside source;
record SHA256 and criteria in the same Plane item before implementation. Changes
to criteria/tests require parent reconciliation and fresh red evidence, not a waiver.

## 2. Fix and collect

Use the narrowest root-cause fix and task-relevant checks. One writer, no mandatory
scout or duplicate reviewer. Commit the candidate before final capture when a later
commit would invalidate its snapshot. Keep artifacts outside the source checkout.

Run `megai acceptance collect` with the frozen contract and hash retrieved from
Plane. It captures commands once, in order, into a new private directory; a failure
or source change stops later commands. The generated evidence is a **BLOCKED draft**,
not acceptance. Inspect raw logs and fill each observation with the actual outcome.
For runtime checks, bind the running build/environment to the candidate and verify
the result (e.g. save then reload), including required error/permission/a11y cases.
Existing E2E commands and authorized browser observations may supply evidence;
screenshots, coverage, exit zero or LLM scores alone do not prove behavior.

## 3. Review, decide, stop

Use one fresh independent Pi verifier through the approved route: neutral READY,
verify Pi/exact model/effective high thinking, then send the frozen contract/hash,
candidate diff/snapshot and raw evidence, not the implementer's reasoning transcript.
Prefer Sol/high. Give read-only authority and a bounded deadline. Reviewer checks
every criterion, root cause, red/green validity, regressions and runtime provenance;
reports severity, `path:line`, impact and reproduction for actionable findings.
Hash the actual review/status artifact. Unavailable verifier means BLOCKED.

Resolve blocking findings; rerun affected diagnostics and obtain source-current
review. Any source/index/commit change invalidates the entire prior snapshot: final
capture and review must match the delivered candidate. Reuse the healthy reviewer
for bounded corrections, with no unbounded repair loop or repeated discovery.

Run `megai acceptance check` with the Plane-approved hash. Only PASS permits agreed
branch delivery and Plane **In Review**, never Done or unapproved main promotion.
Report criterion → command/action → observed result → artifact. FAIL needs a fix;
BLOCKED needs the named evidence/prerequisite. Stop at acceptance. Keep five-minute
slice checkpoints, user resource exclusions and native provider settings intact.
Credentials/private data stay out of argv and public artifacts; raw logs remain
private, and sanitized exports need their own hashes.

## Purpose

Define Pi task verification and acceptance without an automatic independent-review requirement while keeping source-current evidence and historical acceptance receipts intact.

## ADDED Requirements

### Requirement: No mandatory separate reviewer for new Pi tasks
Pi workflows SHALL use actual focused checks and parent self-review, including guarded, delegated and security-sensitive tasks, without requiring a separate reviewer agent. Explicitly requested independent review MAY be performed but SHALL NOT be an implicit prerequisite.

#### Scenario: Guarded task without a reviewer
- **WHEN** a guarded task has source-current checks and parent self-review but no reviewer agent
- **THEN** it may proceed through the acceptance and delivery boundaries without a missing-review blocker

#### Scenario: User asks for an independent review
- **WHEN** the user explicitly requests an independent review
- **THEN** the workflow may run one without making it a default requirement for other tasks

### Requirement: Review-free new acceptance evidence
New acceptance contracts SHALL be able to pass from frozen criteria, source-current command receipts and actual observations without a review object or reviewer identity. A missing, failing or stale required check SHALL still fail or block acceptance. Extra unsupported evidence fields SHALL be blocked instead of silently ignored.

#### Scenario: All checks have current evidence
- **WHEN** a new review-free contract has complete passing criteria and source-current evidence without a review field
- **THEN** the gate returns PASS

#### Scenario: Missing or stale check
- **WHEN** any required check is missing, fails, or has an obsolete source snapshot
- **THEN** the gate does not return PASS

### Requirement: Historical evidence remains verifiable
Acceptance contracts frozen under the earlier reviewer-required schemas SHALL retain their original review validation, without silently changing their approved contract hashes or treating missing reviews as passing evidence.

#### Scenario: Prior frozen contract
- **WHEN** an earlier schema contract and its review evidence are checked
- **THEN** the existing validation applies unchanged

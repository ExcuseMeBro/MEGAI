## Purpose

Provide Pi with private local typed decisions through one Laya runtime while keeping the tracked source, active installed profile and delivery history unambiguous and verifiable.

## ADDED Requirements

### Requirement: Laya-only typed decisions
Pi SHALL expose `laya` for bounded `choice`, `score`, and `noul` requests and SHALL use the local Laya bridge for decision-backed sift, routing, guidance and compaction behavior.

#### Scenario: Mixed decision request succeeds
- **WHEN** a caller submits valid choice, score and noul questions
- **THEN** `laya` returns typed answers and probabilities through the local bridge

#### Scenario: Local runtime fails
- **WHEN** the bridge is missing, invalid, cancelled or exceeds its deadline
- **THEN** the tool returns a bounded failure and advisory hooks preserve their native fallback behavior

### Requirement: One session-scoped local runtime
Pi SHALL lazily start one owned Laya process per extension session, retain only the English and multilingual checkpoints, serialize requests safely and stop the child during shutdown or reload.

#### Scenario: Languages alternate
- **WHEN** English and explicitly multilingual requests alternate in one Pi session
- **THEN** one process reuses the two routed checkpoints without loading a third model

#### Scenario: Session ends
- **WHEN** Pi shuts down or reloads the extension
- **THEN** pending work is rejected safely and no independent daemon remains

### Requirement: Clean tracked source
The accepted `dev` tree SHALL contain only Laya decision implementation and documentation. It SHALL contain no file, directory, code, test, benchmark, result, migration guard, installer hook, compatibility alias, package identifier or descriptive reference belonging to the retired decision stack.

#### Scenario: Tracked tree is scanned
- **WHEN** an exhaustive case-insensitive scan checks tracked paths and contents for the retired tool name and package identifiers
- **THEN** the scan returns zero matches

#### Scenario: Historical work is needed
- **WHEN** an operator needs the retired implementation or its measurements
- **THEN** it remains available from untouched separate branches or Git history rather than the `dev` tree

### Requirement: Ordered branch consolidation
The task lineage SHALL integrate unique Laya refinement commits before independent workflow-status commits, SHALL not duplicate patch-equivalent installer fixes, and SHALL not merge legacy-only branch commits.

#### Scenario: Candidate history is inspected
- **WHEN** commit ancestry and patch equivalence are checked before delivery
- **THEN** all applicable unique changes are present in the required order and excluded work is absent

### Requirement: Safe Laya profile installation
The installer SHALL validate the owned pinned Laya runtime before activation, preserve unowned resources and operator model preferences, apply profile resources before Laya activation, and preserve custom delegation policy while updating only active Laya naming.

#### Scenario: Runtime is valid
- **WHEN** the pinned interpreter, package, lock and routed checkpoints match
- **THEN** one Laya extension becomes active after profile resources are installed

#### Scenario: Runtime or ownership is invalid
- **WHEN** runtime identity, ownership or checkpoint verification fails
- **THEN** installation stops before activating an unusable profile or mutating unowned resources

### Requirement: Active local profile is Laya-only
After delivery, the active local Pi harness SHALL load Laya-backed tools and SHALL contain no active retired extension, prompt, configuration or package reference. Existing private backups and session transcripts SHALL remain unchanged.

#### Scenario: Local profile is verified
- **WHEN** the delivered profile is installed and Pi resources are reloaded
- **THEN** required Laya-backed tools load, the retired tool does not load, and an exhaustive active-resource scan has zero matches

#### Scenario: Historical local data exists
- **WHEN** backup directories or session transcripts contain historical records
- **THEN** cleanup leaves those private records untouched because they are not active harness resources

### Requirement: Guarded dev delivery
The candidate SHALL pass focused behavior checks, changed-Python lint, strict specification validation, exhaustive source/profile scans and source-current independent review before queue-controlled integration to `dev`.

#### Scenario: All evidence passes
- **WHEN** every frozen criterion passes on the exact committed candidate and the queue confirms the expected `dev` base
- **THEN** the candidate may be fast-forwarded to `dev` and handed off In Review

#### Scenario: Main promotion is considered
- **WHEN** `dev` is verified and promotion is desired
- **THEN** no `main` mutation occurs until the user separately approves the exact reviewed commit vector

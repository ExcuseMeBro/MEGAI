## Purpose

Preserve accessible Asana project and task data during a non-destructive, verifiable migration to Plane while both services remain available.

## ADDED Requirements

### Requirement: Complete source accounting
The migration SHALL inventory active and archived projects, including empty projects, completed tasks and recursive subtasks. It MUST account for source descriptions, memberships/sections, comments/history, attachments, dependencies, custom fields, attribution and dates with explicit coverage or gap evidence.

#### Scenario: Archived and nested records
- **WHEN** source enumeration contains an archived project and nested completed subtasks
- **THEN** those records remain in the export and migration inventory without changing source status

#### Scenario: Incomplete response
- **WHEN** pagination, a nested response or a data category cannot be fully retrieved
- **THEN** the migration records the failure and does not report a complete export or full migration

### Requirement: Secure private preservation
The migration SHALL keep source exports, credentials and raw attachment bytes outside Git in private storage. It MUST preserve source privacy and MUST NOT forward tracker credentials to attachment origins, fetch private-network attachment targets, publish source files or invite destination members implicitly.

#### Scenario: Attachment host or permission mismatch
- **WHEN** an attachment URL resolves to a private network or destination permissions would broaden source access
- **THEN** the unsafe operation is blocked and reported without losing the source reference

### Requirement: Stable resumable identity
The migration SHALL preserve source identities, use one destination writer, record durable mappings, reconcile ambiguous write outcomes before retries and leave unrelated destination data untouched.

#### Scenario: Response lost after creation
- **WHEN** a creation request may have succeeded but no response was recorded
- **THEN** retry first reconciles deterministic source identity and never blindly creates a duplicate

#### Scenario: Multiple project memberships
- **WHEN** one Asana task belongs to multiple projects
- **THEN** the migration preserves those memberships explicitly and reports how the destination represents them

### Requirement: Observable data fidelity and parallel safety
The migration SHALL verify source-to-destination records and relationships, preserve original attachment bytes with checksum evidence, and distinguish native imports from archive-only preservation. It MUST detect source drift and destination edits before catch-up, retain Asana as MEGAI's status authority and refrain from source deletion or final cutover.

#### Scenario: Unsupported metadata
- **WHEN** Plane cannot natively restore original authorship, history, timestamps or a property
- **THEN** the original metadata is preserved with provenance and reported as a fidelity gap rather than silently dropped or fabricated

#### Scenario: Destination changed during parallel use
- **WHEN** a mapped destination record has changed since the last verified write
- **THEN** catch-up reports a conflict rather than overwriting the hand edit

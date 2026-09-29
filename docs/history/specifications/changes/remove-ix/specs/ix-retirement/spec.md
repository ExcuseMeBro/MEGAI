## Purpose

Retire Ix without disrupting the existing free local search stack or losing unrelated agent configuration and stored data.

## ADDED Requirements

### Requirement: Ix is not an active MEGAI tool
MEGAI SHALL NOT install, update, invoke, advertise or require Ix during ordinary operation. Existing codedb, zvec-grep and native read/edit behavior SHALL be preserved, with rg as exact-search fallback.

#### Scenario: Fresh and existing installations
- **WHEN** a user installs, updates, checks or launches MEGAI
- **THEN** no Ix installer, backend health check or map command is invoked and the existing search stack remains available.

### Requirement: Explicit safe legacy retirement
Legacy retirement SHALL require explicit apply, preview its changes otherwise, back up changed files, preserve unrelated registrations and refuse malformed or ambiguous inputs before writing. Repeated application SHALL be a no-op. It SHALL NOT delete database volumes or recursively scan other projects.

#### Scenario: Mixed hooks and agent configuration
- **WHEN** retirement is applied to configuration containing known Ix and unrelated entries
- **THEN** only exact known Ix entries and recognized MEGAI leftovers are removed and originals are recoverable.

#### Scenario: Invalid or unrecognized configuration
- **WHEN** an input is malformed or a candidate is not recognizable as Ix-owned
- **THEN** malformed input prevents writes and unrecognized content is preserved with a diagnostic.

#### Scenario: Runtime cleanup
- **WHEN** the current host's Ix runtime is retired
- **THEN** only identity-verified Ix containers are stopped/removed, runtime files are archived, and database volumes and other tools remain intact.

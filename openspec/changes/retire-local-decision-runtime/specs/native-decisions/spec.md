## ADDED Requirements

### Requirement: No shipped local decision runtime
The tracked tree SHALL contain no source, installer, gate, documentation, test, fixture or change record for the retired local decision runtime, and no tracked path or file content SHALL contain its name. Pi workflow decisions SHALL rely on native judgment.

#### Scenario: Tracked tree is free of the retired runtime
- **WHEN** the frozen acceptance check scans every tracked path and every tracked file content for the retired name
- **THEN** it reports no match and passes

#### Scenario: Installer no longer gated on a local runtime
- **WHEN** `lib/pi_model_policy.py` runs with or without `pi-defaults/install.py`
- **THEN** no runtime verification, checkpoint download or loader subprocess runs, the policy transaction applies by itself, and a failure still stops the install

### Requirement: Native decisions, file selection and compaction in policy text
Reachable policy documents SHALL describe every workflow decision step as native judgment, SHALL select files with scoped native search and reads, and SHALL NOT require a retired tool or substitute compactor.

#### Scenario: Policy documents stay native
- **WHEN** the adaptive-policy test reads `pi-skill/ADAPTIVE.md`, `pi-skill/delegation.md`, `pi-skill/acceptance/SKILL.md`, the workflow skills and `pi-defaults/AGENTS.md`
- **THEN** each describes native judgment, none contains the retired name, and the model-policy test finds native compaction documented with no substitute compactor

#### Scenario: Actual Pi loader has no missing mandatory tools
- **WHEN** a disposable Pi profile loads the required extension resources offline
- **THEN** the loader reports no missing mandatory tools or extension errors, and no retired file-selection companion is registered

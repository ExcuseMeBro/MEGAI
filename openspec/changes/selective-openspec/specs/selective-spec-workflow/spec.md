## ADDED Requirements

### Requirement: Selective planning
The Pi integration SHALL use OpenSpec for multi-module behavior, public API/data migration, consequential security changes, or explicit spec requests, while leaving small known-seam fixes on the normal acceptance-and-test path.

#### Scenario: Small fix
- **WHEN** a task is a bounded known-seam fix without an explicit spec request
- **THEN** the agent does not initialize OpenSpec or generate planning artifacts
- **AND** existing acceptance and regression-test requirements remain in force

#### Scenario: Durable complex-change handoff
- **WHEN** a complex change is authorized
- **THEN** the parent prepares scoped requirements, preserved behavior, observable failure scenarios and verification criteria
- **AND** children receive only relevant artifacts and explicit file/validation authority

### Requirement: Single task identity and checklist
The integration SHALL preserve Asana as status authority, one linked summary in `.todos`, and `tasks.md` as the sole detailed implementation checklist.

#### Scenario: Resume or delegation
- **WHEN** a session resumes or a child is assigned a slice
- **THEN** it reuses the proposal's Asana GID and linked change path
- **AND** children do not create tracker tasks or mutate `.todos`

### Requirement: Evidence before handoff
The integration SHALL distinguish structural OpenSpec validation from demonstrated implementation correctness and record requirement-to-evidence mapping.

#### Scenario: Artifacts exist but tests fail
- **WHEN** OpenSpec reports planning complete but an acceptance test fails
- **THEN** the parent reports the failed gate and does not declare implementation verified
- **AND** neither `/opsx:verify` nor archive warnings authorize bypassing the failure

#### Scenario: Verified implementation awaits review
- **WHEN** focused verification and required dev delivery pass
- **THEN** Asana remains In Review with completed=false and the OpenSpec change stays active
- **AND** archive requires explicit user approval, while Done and main promotion retain their separate authority boundaries

### Requirement: Optional privacy-preserving installation
The installer SHALL install the tested OpenSpec version and one managed Pi skill without initializing repositories, modifying model settings or overwriting user skills.

#### Scenario: Initial and repeated installation
- **WHEN** the installer runs with a compatible runtime and no conflicting skill
- **THEN** it uses @fission-ai/openspec 1.12.0 with npm lifecycle scripts disabled when installation is needed
- **AND** it disables OpenSpec telemetry, preserves unrelated configuration, and keeps exactly one managed Pi skill link on repeat runs

#### Scenario: Existing incompatible CLI or skill
- **WHEN** another OpenSpec version or a user-owned skill occupies the target
- **THEN** installation fails clearly without replacing that CLI or skill

#### Scenario: Removal
- **WHEN** the optional integration is removed
- **THEN** only its owned Pi skill links and MEGAI state entry are removed
- **AND** the CLI, user skills, privacy setting and repository specs remain available

#### Scenario: Custom Pi locations and changed ownership
- **WHEN** installation registered multiple Pi locations and removal runs without their original environment overrides
- **THEN** removal checks every registered location and removes only links still pointing to the managed skill
- **AND** links replaced by their owner are preserved

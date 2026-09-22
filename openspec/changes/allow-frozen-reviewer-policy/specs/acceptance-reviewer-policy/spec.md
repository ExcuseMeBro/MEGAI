## ADDED Requirements

### Requirement: Frozen reviewer policy in schema-2 contracts
Schema-2 acceptance contracts SHALL accept an optional top-level `reviewer` object with exactly `harness`, `model` and `thinking`; its presence SHALL freeze the exact independent reviewer policy for that task. A malformed or partial `reviewer` object SHALL be BLOCKED. Schema-1 contracts SHALL NOT accept the field.

#### Scenario: Valid frozen policy
- **WHEN** a schema-2 contract includes `reviewer` with a harness, a `provider/model` value and a thinking level
- **THEN** the contract parses successfully and the frozen policy is available to collection and checking

#### Scenario: Malformed frozen policy
- **WHEN** the `reviewer` object omits a required field, has extra fields, or holds an empty harness or syntactically invalid model
- **THEN** `collect` and `check` both return BLOCKED without running or accepting evidence

#### Scenario: Schema-1 contract with reviewer
- **WHEN** a schema-1 contract contains a `reviewer` field
- **THEN** the contract is BLOCKED as unsupported

### Requirement: Exact evidence validation against the frozen policy
`check` SHALL require review evidence to match a frozen policy exactly on harness, provider/model and thinking, and SHALL keep requiring `harness: pi` and `thinking: high` when no policy is frozen. A non-frozen review with a thinking level other than `high` SHALL be BLOCKED.

#### Scenario: Explicitly frozen medium review passes
- **WHEN** a schema-2 contract freezes `openai-codex/gpt-5.6-luna` at `medium` and the review evidence records that harness, model and thinking
- **THEN** `check` accepts the review as independent and returns the criteria verdict

#### Scenario: Frozen-policy mismatch
- **WHEN** review evidence records a different harness, provider/model or thinking level than the frozen policy
- **THEN** `check` returns BLOCKED and does not treat the review as independent

#### Scenario: Legacy contract keeps Pi/high
- **WHEN** a schema-2 contract has no `reviewer` field and review evidence records `harness: pi` at `high`
- **THEN** `check` accepts the review as before
- **AND** the same contract with a `medium` review is BLOCKED

### Requirement: Collection emits the frozen reviewer policy
`collect` SHALL populate the generated review template's `harness`, `model` and `thinking` from the frozen policy when present, and SHALL keep the existing Pi/high template when it is absent.

#### Scenario: Frozen policy template
- **WHEN** a schema-2 contract with a frozen policy is collected
- **THEN** the draft evidence review records that harness, model and thinking while `verdict`, `session_id` and observations remain explicitly incomplete

#### Scenario: Default template
- **WHEN** a contract without a frozen policy is collected
- **THEN** the draft review keeps `harness: pi` and `thinking: high` as today

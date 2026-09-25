## Purpose

Defines the explicitly selected native Pi/Paseo worker profile and bounded balance fallback after retiring the non-interactive Agy integration without weakening ownership or credential safety.

## ADDED Requirements

### Requirement: Native worker profile
The operator SHALL be able to select a GPT Sol high coordinator, one native DeepSeek Flash high implementation worker and a separate GPT Astra high reviewer. An active parent SHALL retain its selected model and thinking. The profile MUST NOT require or register an Agy worker tool.

#### Scenario: Fresh configured session
- **WHEN** the native profile is selected for a new session
- **THEN** startup uses GPT Sol high, role guidance selects DeepSeek Flash high for substantial bounded implementation and GPT Astra high for independent review, and Agy is not installed as an active Pi extension.

#### Scenario: Existing session and unrelated settings
- **WHEN** owned policy is refreshed or the native profile is applied
- **THEN** unrelated settings, credentials and the already-running parent's model remain unchanged, with a private backup and ownership checks before runtime changes.

### Requirement: One-way provider-specific balance recovery
A confirmed DeepSeek provider-specific insufficient balance SHALL attempt at most one GPT Luna continuation at high thinking, preserving the failed task context, diff and test evidence. Auth/permission failures, uncertain writes and shared outages MUST NOT trigger model hopping; failure on the fallback MUST NOT cycle back.

#### Scenario: Insufficient DeepSeek balance
- **WHEN** a DeepSeek run ends on a confirmed 402 insufficient-balance provider error, the writer is quiescent and Luna is available
- **THEN** its unfinished task resumes once on GPT Luna high with the original evidence, without a second concurrent writer.

#### Scenario: Non-provider or second failure
- **WHEN** the failure is permission/auth-related, the prior write is uncertain, or the Luna continuation fails
- **THEN** the system retains the work and evidence without a further automatic model transition.

### Requirement: Retired Agy integration
The managed Pi policy SHALL no longer install Agy tools, Agy-only presets or mandatory Agy execution instructions. Retirement MUST NOT uninstall the standalone operator-owned CLI, delete credentials or alter another repository.

#### Scenario: Owned runtime upgrade
- **WHEN** the reviewed native profile replaces the owned Antigravity profile
- **THEN** it removes only receipt-owned Agy extension/policy resources and installs the native role/fallback configuration; custom or unowned bytes are retained for explicit reconciliation.

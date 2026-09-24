## Purpose

Defines reliable, event-driven handoff of Paseo-hosted Pi child agents and an opt-in local Antigravity/GPT profile without silently changing unrelated providers or safety limits.

## ADDED Requirements

### Requirement: Child completion is event driven
The Pi parent SHALL request completion notifications when creating a Paseo Pi child and on every background dispatch, retain child/run identity, yield when dependent, and resume only on a matching completion, error, or permission-needed event. It MUST NOT poll, sleep, or use an arbitrary child-wait timeout as a completion signal.

#### Scenario: Matching completion
- **WHEN** a supervised Pi child finishes its current dispatched run and Paseo delivers a matching notification
- **THEN** the parent examines its saved result once and continues the original task without resending the prompt.

#### Scenario: Unmatched or permission-needed event
- **WHEN** a duplicate, stale, other-child, error, or permission-needed notification arrives
- **THEN** the parent MUST NOT accept it as successful completion or automatically approve a permission; it reconciles the matching run and preserves the task state.

#### Scenario: Notification transport unavailable
- **WHEN** the parent cannot confirm that completion notifications can reach it
- **THEN** it SHALL use a supported native event-backed wait without an artificial timeout if safe, or report the blocked handoff, never schedule a polling loop or claim the notification worked.

### Requirement: Safety timeouts stay distinct
The harness SHALL retain provider request/stall safeguards and tool-specific timeout semantics independently of child-result waiting. Antigravity CLI delegation SHALL remain bounded and SHALL NOT be represented as a Paseo Pi agent notification source.

#### Scenario: Provider stall
- **WHEN** a provider is unresponsive while a child run is pending
- **THEN** the existing stalled-provider reconciliation applies; the absence of a child-wait deadline does not approve indefinite provider requests, blind retries, or replacing a busy writer.

### Requirement: Opt-in Antigravity Pi profile is reproducible
The installer SHALL offer an explicit Antigravity-first local Pi preset whose native Pi coordinator and roles use GPT, whose DeepSeek runtime fallback is disabled, and whose bounded Agy worker uses the existing worktree and sandbox safeguards. Selecting it MUST preserve unrelated settings and the existing opt-in economy preset; it MUST NOT register Antigravity as a native Pi model.

#### Scenario: Opt-in installation
- **WHEN** the operator explicitly chooses the Antigravity preset
- **THEN** fresh Pi sessions start with a GPT model, use GPT-native role metadata, do not implicitly fall back to DeepSeek, and eligible Git implementation is routed to sandboxed Agy with independent GPT review.

#### Scenario: Existing configuration
- **WHEN** the installer refreshes Pi policy without the new preset
- **THEN** it leaves the operator's native provider/model, thinking, credentials, existing fallback file, and explicit economy choice unchanged.

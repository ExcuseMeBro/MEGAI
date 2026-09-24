## Purpose

Provide Pi's optional typed decision, file relevance and short-context compaction helpers from an on-device model without hosted Jev traffic or weakening native safety controls.

## ADDED Requirements

### Requirement: On-device typed decisions
The local Pi harness SHALL answer supported `choice`, `score` and `noul` requests using the installed `laya-multilingual` checkpoint without sending state, file content, credentials or metadata to a remote model endpoint. It SHALL validate question counts, criteria, finite probability values and complete answer identities before returning success. It SHALL report a bounded failure instead of silently truncating input that does not fit the checkpoint.

#### Scenario: Valid local decision
- **WHEN** a Pi caller supplies a valid state and supported questions that fit the local checkpoint
- **THEN** it receives typed answers, model identity and usage derived from local inference, with no hosted Jev request

#### Scenario: Unsupported or long input
- **WHEN** a request is malformed, too long or the local runtime is unavailable
- **THEN** it returns a bounded error without a fabricated answer or an external fallback request

### Requirement: Advisory tool calls and local file relevance
Laya suggestions SHALL NOT replace Pi's native permission checks, block tool calls using thresholds tuned for Jev, or cause automatic tool retries. File relevance SHALL screen only allowed readable local files, return bounded per-file probabilities, and never transmit file content to a remote endpoint.

#### Scenario: Disagreement with the previous gate
- **WHEN** Laya objects to a tool call or suggests an alternative route
- **THEN** Pi's native tool/permission flow remains authoritative and the suggestion does not block the call

#### Scenario: Candidate contains sensitive path
- **WHEN** a requested file is credential-shaped, unreadable or over the screening limits
- **THEN** the screening tool refuses or reports that candidate without reading or forwarding its text

### Requirement: Loss-avoiding local compaction
Short, complete, supported compaction decision inputs MAY be evaluated locally, but the extension SHALL never submit overlength or truncated state and SHALL never delete an irreplaceable tool result based only on an uncalibrated model judgment. If a safe, meaningful reduction cannot be demonstrated or inference fails, the extension SHALL defer to Pi's native summarizer, preserving the original session history.

#### Scenario: Long or failed compaction input
- **WHEN** a compaction input exceeds the local model's context or a local decision fails
- **THEN** the extension returns control to Pi's native summarizer without committing a lossy local summary

#### Scenario: No safe reduction
- **WHEN** local decisions do not establish a safely reducible span
- **THEN** Pi's native summarization runs rather than appending a non-shrinking transcript

### Requirement: No active Jev browser
The installed local Pi profile SHALL NOT expose a Jev-browser skill or bundled executable as an active capability after migration.

#### Scenario: Browser capability discovery
- **WHEN** the refreshed local profile lists its installed skills and tools
- **THEN** no Jev-browser entry is offered and the documentation describes browser automation as unavailable until an independently approved local replacement exists

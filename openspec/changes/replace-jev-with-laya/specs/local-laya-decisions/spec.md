## Purpose

Provide Pi with private, local typed semantic decisions while preserving the workflow-facing choice, score and noul contract and safe failure behavior.

## ADDED Requirements

### Requirement: Local typed decision tool
Pi SHALL expose a `laya` tool that accepts one state, an optional bounded language hint, and one to eight independent `choice`, `score`, or `noul` questions and returns typed answers, probability distributions, routing/model identity, usage and a short ledger record id.

#### Scenario: Mixed decision request succeeds
- **WHEN** a caller submits valid choice, score and noul questions in one request
- **THEN** `laya` returns each answer under the caller's question id with the corresponding typed value and probabilities

#### Scenario: Explicit multilingual routing
- **WHEN** a caller submits Uzbek state with `lang: "uz"`
- **THEN** the bridge routes it to the multilingual checkpoint and reports that routing without loading the specialized typed-decisions checkpoint

#### Scenario: Invalid question is rejected locally
- **WHEN** a request has an invalid id, type, language hint, instructions, criteria shape or question count
- **THEN** Pi returns `ok:false` without starting inference for that request

### Requirement: No hosted decision dependency
Active Pi decision paths SHALL use a local Laya model and SHALL NOT require, read or transmit a TypeSafe API key or call a TypeSafe endpoint.

#### Scenario: Decision runs without credentials
- **WHEN** the Laya runtime and checkpoint are installed but no TypeSafe credential exists
- **THEN** typed decisions work and no credential prompt appears

#### Scenario: Text remains local
- **WHEN** Pi evaluates workflow state or screens a readable file
- **THEN** that content is passed only to the local Laya process and is not sent to a hosted decision service

### Requirement: Session-scoped runtime lifecycle
Pi SHALL start one Laya model process lazily, use a two-slot router that retains only the English and multilingual checkpoints after first use, reuse it across decisions in the same session, serialize access safely, and stop it during session shutdown or reload.

#### Scenario: Alternating languages reuse routed models
- **WHEN** English and explicitly Uzbek-hinted decisions alternate in one Pi session
- **THEN** they use one successfully started Laya process, each checkpoint loads at most once, and the router never loads typed-decisions

#### Scenario: Session ends
- **WHEN** Pi emits session shutdown
- **THEN** the extension closes the process input, terminates any remaining child and leaves no independent daemon

### Requirement: Bounded fail-open behavior
Decision-tool failures SHALL return a bounded `ok:false` result; advisory gate, routing, repair, sift and compaction failures SHALL preserve the underlying Pi action or native fallback instead of inventing a verdict.

#### Scenario: Runtime is missing
- **WHEN** the installed Python runtime or model checkpoint cannot be loaded
- **THEN** the tool reports one actionable local error and advisory hooks fail open without a retry loop

#### Scenario: Caller cancels
- **WHEN** the caller aborts an in-flight local decision
- **THEN** the pending request is cancelled or rejected within the configured deadline without replaying it

### Requirement: Laya-specific gate safety
Tool-call blocking SHALL be disabled by default until Laya-specific calibration evidence establishes a threshold; an explicit operator setting MAY enable blocking while preserving repeat-unchanged deadlock escape.

#### Scenario: Default gate receives a strong objection
- **WHEN** local Laya returns an objection above the configured threshold and blocking has not been explicitly enabled
- **THEN** Pi reports the advice and allows the tool call

#### Scenario: Explicit blocking is enabled
- **WHEN** the operator enables Laya gate blocking and a judgment meets the configured threshold
- **THEN** Pi blocks the first call and permits an identical repeated call

### Requirement: Private bounded ledger
Pi SHALL record decision metadata and answers in a bounded local Laya ledger without storing the supplied state, screened file contents, credentials or question text.

#### Scenario: Decision is logged
- **WHEN** a local decision succeeds or fails and logging is enabled
- **THEN** one ledger row records the local model, source, answer metadata and timing while excluding the input text

### Requirement: Safe installation and migration
The installer SHALL provision a pinned upstream `laya` runtime (package version and hash, pinned interpreter) in a MEGAI-owned directory, selectively cache and verify English `convaiinnovations/laya` plus its bundled multilingual checkpoint before activating the extension, retire owned Jev extension assets, and preserve unowned resources.

#### Scenario: Supported clean install
- **WHEN** installation runs on a supported platform with the pinned interpreter available and writable owned destinations
- **THEN** the pinned runtime and both routed checkpoints are verified before `megai-laya` and `megai-laya-compaction` become active

#### Scenario: Unsupported platform
- **WHEN** installation runs where the pinned interpreter or `laya` runtime cannot be provisioned
- **THEN** installation stops with a clear error before replacing the active decision extension

#### Scenario: Existing unowned runtime
- **WHEN** the target Laya runtime exists without the MEGAI ownership marker
- **THEN** the installer preserves it and stops without mutation

### Requirement: Laya-backed companion behavior
The existing file screen, workflow gate/router, failed-tool next-move guidance and fast compaction behaviors SHALL use the same local Laya runtime and SHALL retain their existing input bounds, privacy checks and native fallbacks unless this specification states otherwise.

#### Scenario: Sift screens mixed candidates
- **WHEN** `sift` receives readable and refused candidate paths
- **THEN** readable text is scored locally, refused paths make no inference request, and only probabilities or refusal reasons enter the conversation

#### Scenario: Compaction cannot decide safely
- **WHEN** a Laya batch fails, returns unusable answers, or drops nothing
- **THEN** Pi keeps the affected entries or uses native compaction instead of losing transcript content

### Requirement: Clean public migration
Active installed resources, active policy text, environment variables, tool names, ledgers and tests SHALL use Laya naming and SHALL expose no `jev` compatibility tool.

#### Scenario: Pi resources load after migration
- **WHEN** the updated profile is installed and resources are reloaded
- **THEN** `laya` and `sift` are registered, `jev` is absent, and owned `megai-jev*` extension directories are retired

#### Scenario: Historical evidence remains readable
- **WHEN** repository history or published Jev benchmark artifacts are inspected
- **THEN** those immutable historical records may retain their original names but do not drive the active Laya runtime

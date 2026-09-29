## Purpose

Provides one Plane-first coordination contract and a reversible local connector cutover for MEGAI's coding-agent clients.

## ADDED Requirements

### Requirement: Plane identity and boundary lifecycle
MEGAI task-flow SHALL consume every page of the Plane project list and require exactly one exact Git-root project; zero or multiple projects SHALL block. It SHALL consume every page of that project's work-item list and require zero/one/multiple outcomes to be handled explicitly (ask before creating on zero; stop on multiple). It SHALL retain the `(project UUID, work item UUID)` identity pair. Imported work SHALL be matched by both `external_id` and `external_source=asana-migration-v1`, or by exhaustive pagination when server-side filtering is unavailable. The original `<!-- asana:GID -->` marker SHALL remain unchanged until the Plane pair is confirmed. `In Progress` and `In Review` SHALL remain in Plane's started group; boundary policy SHALL not require or write a completion boolean, and only the user may transition work to `Done`.

#### Scenario: Exact project and work-item resolution
- **WHEN** a tracked task starts without a linked identity pair
- **THEN** the client consumes all project and work-item pages, accepts exactly one match, and reuses the resolved UUID pair; zero or multiple matches require user reconciliation

#### Scenario: Imported identity is unresolved
- **WHEN** an imported candidate has a matching external ID but its source is missing, different, or not yet found
- **THEN** the client continues pagination or stops for reconciliation and does not create a duplicate work item

#### Scenario: Verified handoff
- **WHEN** implementation verification is complete
- **THEN** the client places the work item in started `In Review`, leaves completion state to Plane/user policy, and does not mark it Done

### Requirement: Credential-safe reversible client cutover
The connector setup SHALL support additive Plane setup for Pi and Codex and an explicit replacement mode. Codex SHALL require a separately installed, pinned `mcp-remote@0.1.43` artifact with a verified local receipt; runtime SHALL never dynamically install it. Plane tokens SHALL remain in owner-readable private files, SHALL never appear in client configuration, command-line arguments, or MEGAI logs, and SHALL be loaded only at request/bridge launch. Setup SHALL stage all selected clients before committing, preserve unrelated settings, refuse malformed or symlinked configuration, create target-bound private backups before replacement/removal, use HTTPS without TLS-disabling options, and be byte-idempotent. Rollback SHALL restore a private pre-change connector backup without deleting remote data or claiming to restore task-flow policy backups.

#### Scenario: Explicit Pi and Codex replacement
- **WHEN** the user runs Plane setup for both clients with explicit replacement enabled
- **THEN** the managed Plane entries are installed, local legacy tracker entries are removed, unrelated configuration is preserved, and private backups are available

#### Scenario: Verified bridge preflight
- **WHEN** Codex setup is requested without a valid local bridge receipt
- **THEN** setup fails before any client configuration is changed; package installation is available only through the explicit credential-free bridge install command

#### Scenario: Additive setup
- **WHEN** the user runs Plane setup without replacement enabled
- **THEN** managed Plane entries are added or refreshed while existing unrelated connector entries remain unchanged

#### Scenario: Unsafe input
- **WHEN** a token file or target client configuration is missing, world-readable, malformed, or symlinked
- **THEN** setup fails closed before writing configuration and emits no credential material

#### Scenario: Repeat and rollback
- **WHEN** setup is repeated with the same workspace and token file, or the user invokes restore after a cutover
- **THEN** repeat setup is a no-op and restore returns the affected client configuration to its latest private pre-change backup

### Requirement: Managed task-flow policy replacement
The policy installer SHALL replace only the owned Pi task-flow section and the exact Codex workflow marker block, preserving unrelated user instructions. Shipped task-flow, OpenSpec, OMP, README, and lifecycle guidance SHALL describe Plane as the sole active tracker after cutover and SHALL not reintroduce an Asana fallback or routine dual synchronization.

#### Scenario: Pi policy section
- **WHEN** Pi has `## MEGAI task flow` followed by `## Paseo-visible delegation`
- **THEN** the installer replaces only the task-flow section and leaves the delegation heading and its user-owned content byte-for-byte unchanged

#### Scenario: Codex policy block
- **WHEN** Codex has the exact legacy workflow marker block and unrelated instructions around it
- **THEN** the installer replaces that block with the managed Plane policy and preserves the surrounding instructions

#### Scenario: Ambiguous policy input
- **WHEN** a managed policy marker is duplicated, unpaired, or a target is symlinked
- **THEN** the installer refuses the change without altering the target

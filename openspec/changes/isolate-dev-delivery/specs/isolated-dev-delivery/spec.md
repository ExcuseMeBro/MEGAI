## Purpose

Defines the agent task lifecycle that keeps Git implementation isolated while delivering verified changes to local dev and retiring only proven-safe task resources.

## ADDED Requirements

### Requirement: Isolated task writes
The agent SHALL make every task Git-source edit in a separately owned task workspace and worktree based on the agreed dev branch, not directly in a dev/main checkout. Non-Git settings SHALL use an explicitly owned local configuration scope with a private backup.

#### Scenario: Small Git change
- **WHEN** a one-line source change is requested in a repository whose dev checkout is clean
- **THEN** the agent creates or reuses a verified task-owned managed worktree and edits there, leaving dev unchanged until integration.

#### Scenario: Isolation unavailable
- **WHEN** the task worktree cannot be uniquely created or owned
- **THEN** the agent blocks Git edits rather than falling back to direct dev writes.

### Requirement: Automatic verified local dev delivery
The parent SHALL, after current acceptance and required review, acquire the shared integration reservation and deliver task commits to local dev without waiting for another user confirmation. It SHALL verify the exact delivered commit before completing the reservation and Plane handoff; it MUST NOT automatically push, publish, promote main or mark Plane Done.

#### Scenario: Verified task
- **WHEN** task acceptance and review pass, the dev checkout is clean, and the reservation is granted for the unchanged target
- **THEN** the parent fast-forwards the task commit into local dev, verifies ancestry and records the delivered commit and reservation outcome.

#### Scenario: Delivery cannot be proved
- **WHEN** the target moves, acceptance becomes stale, reservation is unavailable or merge result is uncertain
- **THEN** the parent retains the task resources and records the blocker without forcing a merge, assuming success or asking for unnecessary approval.

### Requirement: Safe automatic retirement
The parent SHALL attempt post-delivery retirement of only the current task's released, idle, clean workspaces and provably merged temporary branches without asking again. It SHALL preserve active, dirty, unknown, unmerged, persistent or otherwise unproven resources and report their reasons.

#### Scenario: Proven merged task
- **WHEN** the task commit is verified on local dev and the workspace is released and clean
- **THEN** the parent archives the task-owned workspace and safely deletes its merged temporary local branch, verifying the result before Plane In Review.

#### Scenario: Workspace still owned
- **WHEN** an agent or terminal still owns the workspace, or ignored files lack safe preservation
- **THEN** the parent leaves the resources intact and reports the specific blocker.

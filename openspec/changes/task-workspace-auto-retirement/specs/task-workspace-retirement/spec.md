## ADDED Requirements

### Requirement: Retire released direct children before the workspace
After the exact task tip is verified in local dev and all data checks pass, pinned cleanup SHALL recognize idle direct children of the invoking parent in the exact task workspace, inspect each child for identity, matching cwd, no pending permissions and archived or safely archivable status, and archive those children without `--force` before archiving the workspace. The invoking parent SHALL run from a retained checkout; it SHALL never archive itself. Cleanup SHALL re-read owner and terminal state after child archival and immediately before workspace archival. A failed or uncertain child archival SHALL retain the workspace and branch for reconciliation.

#### Scenario: Delivered clean task with idle direct child
- **WHEN** the child belongs to the invoking parent, is idle without pending permissions and the task tip is in local dev
- **THEN** the child is archived, the released workspace is archived and the local task branch is deleted without another user prompt.

#### Scenario: Active or foreign owner
- **WHEN** a matching agent is running, has a pending permission or is owned by another parent
- **THEN** no agent or workspace is archived and no branch is deleted.

#### Scenario: Uncertain child result
- **WHEN** archival fails, its result cannot be read back or another owner appears
- **THEN** remaining work is preserved and the exact blocker is reported.

### Requirement: Reconcile task-owned data, never discard unknown work
Agents SHALL complete tracked/untracked task source as part of the task before acceptance. After delivery, task-owned ignored or generated files SHALL be identified and preserved in a verified private backup before workspace archival; data whose ownership or purpose cannot be proven SHALL remain in place and be reported. No automatic reset/stash/force deletion of foreign or ambiguous work is authorized.

#### Scenario: Dirty source during task execution
- **WHEN** a task-owned source change is not committed and source-current tests/review are stale
- **THEN** the owning agent commits only its verified task changes and refreshes evidence before delivery; it does not archive the workspace prematurely.

#### Scenario: Unknown or foreign data
- **WHEN** ownership or contents cannot be verified
- **THEN** the resource is retained and other independent deliverable rows continue.

### Requirement: `/mdev` repairs recoverable rows after delivery
`/mdev` SHALL use its per-repository ledger and queue reservation to deliver independently ready candidates, automatically release proven task-owned idle agents and invoke the pinned cleanup command before the task's In Review handoff. It SHALL treat remote-dev ancestry in status as advisory for local-only cleanup and SHALL use isolated integration for a dirty or busy primary checkout only where `/mdev` explicitly authorizes remote dev push; it SHALL not silently push during an ordinary local task.

#### Scenario: Multiple rows and one blocked workspace
- **WHEN** one delivered row has an unreleased or ambiguous owner and a second row is clean and independently ready
- **THEN** `/mdev` records the first as retained and continues delivery and cleanup of the second.

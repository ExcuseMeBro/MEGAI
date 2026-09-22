## ADDED Requirements

### Requirement: Read-only project-scoped status command
The CLI SHALL provide `status [--cwd PATH] [--workspace WORKSPACE_ID]`. It SHALL exit 0 and print a JSON inventory whenever an inventory can be produced, reporting every known-but-unsafe candidate as an explicit per-item `blocked` entry. It SHALL exit non-zero with a `BLOCKED:` reason on stderr and print no stdout only when the observation is fatally unavailable: an unresolvable project/cwd, an unreadable or malformed Paseo payload, or an explicit `--workspace` id that is absent or belongs to another project.

#### Scenario: Successful inventory
- **WHEN** `status` runs inside a configured project repository whose approved remote is reachable and Paseo responds with documented shapes
- **THEN** it prints JSON containing `root`, `layout`, `planeProject`, `repositories`, `workspaces`, `pendingDelivery`, `cleanupEligible` and `blocked`
- **AND** exits 0

#### Scenario: Known-but-unsafe observation
- **WHEN** a repository or workspace is dirty, busy, unknown-owned, raced, or its remote/`dev` cannot be read
- **THEN** the command still exits 0 with that candidate carrying an explicit `blocked` reason
- **AND** the candidate is never `cleanupEligible`

#### Scenario: Fatal unreadable observation
- **WHEN** the project cannot be resolved, a Paseo read fails or is malformed, or an explicitly requested `--workspace` is absent or foreign
- **THEN** the command exits non-zero with `BLOCKED:` on stderr and prints no stdout

#### Scenario: Observation is not approval
- **WHEN** `status` runs
- **THEN** it performs no merge, push, archive, delete, checkout, Plane mutation or source/config/ref edit
- **AND** only the approved fetch may write Git objects and `FETCH_HEAD`
- **AND** `pendingDelivery` and `cleanupEligible` are advisory observations that never bypass the integration queue
- **AND** an `archiveEligible` report is not archive authorization; actual cleanup still requires the separate parent owner/terminal/service-release gate

#### Scenario: Existing commands preserved
- **WHEN** `context`, `start`, `review`, `done` or `verify-main` is invoked
- **THEN** its existing behavior and output are unchanged

### Requirement: Fetch-fresh repository inventory
`status` SHALL inventory exactly the resolved project's configured `repositories`, `persistentBranches` and `preserveBranches`, refreshing only approved remotes, and SHALL report per repository the current branch, exact HEAD, detached state, dirty/untracked state, unfinished-operation state and remote-`dev` ancestry.

#### Scenario: Approved fetch does not rewrite local refs
- **WHEN** a configured persistent branch is inventoried
- **THEN** it is fetched with an explicit empty refmap and its fresh tip is read from `FETCH_HEAD`
- **AND** every named local ref, including a stale remote-tracking ref, is byte-identical afterwards

#### Scenario: Remote advanced while local tracking is stale
- **WHEN** the approved remote `dev` advances after the last local fetch
- **THEN** the reported `remoteDev` is the fresh remote tip
- **AND** the local remote-tracking ref is unchanged

#### Scenario: Approved fetch only
- **WHEN** a repository's remote violates the configured forge policy, or its remote or `dev` is missing or fails
- **THEN** that repository is blocked with a `remoteDev`/`remoteDevError` reason and no network call is made for a policy violation
- **AND** other repositories and the command still complete (exit 0)

#### Scenario: Exact project scope
- **WHEN** the project is a monorepo or a grouped multi-repository project
- **THEN** every configured repository and every persistent/preserve branch is reported
- **AND** no repository or project outside the resolved configuration is inspected

#### Scenario: Missing local branch versus failed command
- **WHEN** a configured branch is absent locally
- **THEN** it is reported with `local: null` and is not a blocked condition
- **AND** a failed Git command is a blocked condition

#### Scenario: Dirty and unfinished operation
- **WHEN** a repository has uncommitted tracked or untracked changes, or an in-progress merge, cherry-pick, revert, rebase or bisect
- **THEN** the repository is reported dirty and its normalized operation name is reported
- **AND** it is not eligible for cleanup

#### Scenario: Ignored data and locked worktree
- **WHEN** a worktree contains ignored untracked files, or a registered worktree is locked
- **THEN** normal `git status` is clean for the ignored data, yet the worktree is not `archiveEligible`
- **AND** the blocker names the ignored data or the lock, because archiving could destroy ignored data or violate the lock

### Requirement: Branch, worktree and pending-delivery inventory
`status` SHALL enumerate local task branches and registered worktrees with their exact HEADs, and SHALL report as `pendingDelivery` every such HEAD that is not reachable from the fetched remote `dev`.

#### Scenario: Clean unpublished task tip
- **WHEN** a clean task branch or worktree has a commit not reachable from the fetched remote `dev`
- **THEN** it appears in `pendingDelivery` with its exact HEAD
- **AND** it is not `cleanupEligible`

#### Scenario: Extra preserve branch
- **WHEN** a repository configures an additional `preserveBranches` entry
- **THEN** that branch is inventoried alongside `dev` and `main`

#### Scenario: Detached HEAD
- **WHEN** a repository is at a detached HEAD
- **THEN** `current` is null and `detached` is true
- **AND** a detached worktree is never `archiveEligible`

### Requirement: Fail-closed ownership and scoped workspace observation
`status` SHALL observe only workspaces of the resolved project (or exactly the requested `--workspace` id) through the documented Paseo read commands, SHALL resolve ownership by canonical project id and Git common-dir membership rather than display name, and SHALL treat busy, unreleased or unknown ownership as unsafe.

#### Scenario: Known ownership by identity
- **WHEN** a workspace maps to exactly one project id whose canonical path equals the resolved project root and whose cwd belongs to a configured repository
- **THEN** its ownership is `known`
- **AND** a matching local primary or a foreign repository or a foreign project id is never `cleanupEligible`

#### Scenario: Ambiguous identity
- **WHEN** duplicate project names or paths make the project id ambiguous
- **THEN** the affected workspace is `ownership: unknown` and blocked
- **AND** it is never `cleanupEligible`

#### Scenario: Foreign requested workspace
- **WHEN** `--workspace ID` names a workspace belonging to another project or another repository
- **THEN** the command exits non-zero with a `BLOCKED:` reason and prints no stdout

#### Scenario: `--workspace` does not narrow repository scope
- **WHEN** `--workspace ID` is supplied for a valid workspace
- **THEN** the full project repository and persistent-branch inventory is still produced

#### Scenario: Paseo schema drift
- **WHEN** a Paseo read fails or returns a shape that does not match the documented fields
- **THEN** a fatal payload failure blocks the command, while an individual malformed observation is blocked rather than guessed

### Requirement: Affirmative release proof for cleanup
`status` SHALL consider a scoped workspace released only with affirmative evidence, and SHALL report `archiveEligible` only for a clean, idle, known-owned, released worktree whose exact HEAD is reachable from the fetched remote `dev`; it SHALL never archive.

#### Scenario: Released task-owned worktree
- **WHEN** a matching scoped agent is archived with a known idle status, empty pending permissions and a matching inspect identity, and no non-archived or protected agent shares the workspace
- **THEN** the worktree is listed in `cleanupEligible` with its exact HEAD, provided it is clean, idle and at a remote-`dev`-reachable HEAD

#### Scenario: Incomplete terminal evidence
- **WHEN** a matching agent is archived but has no known idle status, or its inspect identity does not match the workspace
- **THEN** the workspace is not released and not `archiveEligible`
- **AND** `status` does not assume an undocumented queue or terminal/service release field; incomplete evidence is blocked

#### Scenario: No agent is unknown, not safe
- **WHEN** a workspace has no matching scoped agent
- **THEN** it is `released: false`, blocked, and never `cleanupEligible`

#### Scenario: Idle alone is not completion proof
- **WHEN** a matching agent is not archived, or reports pending permissions, or its state is running, initializing, error or unknown
- **THEN** the workspace is `busy`, blocked, and never `cleanupEligible`

#### Scenario: Current runner is protected
- **WHEN** a matching scoped agent id equals the current runner id
- **THEN** the workspace reports `protected: true`, is blocked, and is never `cleanupEligible`

### Requirement: Ref-race guard
`status` SHALL compare every observed named ref and worktree HEAD before and after the observation pass and SHALL report any moved candidate blocked rather than emitting a stale snapshot.

#### Scenario: Concurrent ref movement
- **WHEN** an observed persistent, task or worktree ref changes during the pass
- **THEN** that candidate is reported blocked with a movement reason
- **AND** it is never `cleanupEligible` and never presented as verified state

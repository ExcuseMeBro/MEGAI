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

#### Scenario: No canonical project match
- **WHEN** no Paseo project's canonical path equals the resolved project root
- **THEN** the command exits non-zero with `BLOCKED:` on stderr and prints no stdout
- **AND** it never reports an empty, safe-looking inventory

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

#### Scenario: Failed observation is never clean or absent
- **WHEN** any Git safety read (`status`, ignored scan, git-dir/common-dir, worktree list, ref snapshot, HEAD, symbolic-ref, local-ref or merge-base) fails
- **THEN** that candidate carries a blocked reason and the value is unknown, never reported as clean or absent
- **AND** a failed safety check can never yield `archiveEligible`

#### Scenario: Failing persistent branch blocks its repository
- **WHEN** one persistent-branch fetch fails while another succeeds
- **THEN** the repository is blocked with the failing branch reason without aborting the command
- **AND** a workspace of that repository is never `archiveEligible`

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

#### Scenario: Complete field validation
- **WHEN** an agent-list, project or workspace row is missing a documented field or has a wrong field type
- **THEN** the command fails closed with `BLOCKED:` and no stdout, never a traceback
- **AND** an `agent inspect` payload that is not an object, or whose `Id`/`Status`/`Cwd`/`Archived` type drifts, is a per-candidate blocker rather than a guess

#### Scenario: Missing pending-permissions is unknown
- **WHEN** a matching archived agent's `PendingPermissions` field is absent
- **THEN** its permissions are unknown, not empty, so the workspace is not released and not `archiveEligible`

#### Scenario: One bad matching agent invalidates release
- **WHEN** any matching scoped agent fails inspect, is malformed, is not archived, has pending permissions or unknown status, or is the protected runner
- **THEN** the workspace is not released even when another matching agent is archived and idle

#### Scenario: Missing runner identity is unknown
- **WHEN** the current runner id is not available
- **THEN** the inventory is still produced, but every workspace is blocked and never `archiveEligible`

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

#### Scenario: Categorical cleanup exclusions
- **WHEN** a workspace cwd is the primary checkout (even when mislabeled `worktree`), or its branch is `dev`, `main` or a configured preserve branch, or it is detached or not a `task/` branch
- **THEN** it is blocked and never `archiveEligible`, regardless of the Paseo isolation label or any agent release evidence

### Requirement: Ref-race guard
`status` SHALL compare every observed named ref and worktree HEAD before and after the observation pass and SHALL report any moved candidate blocked rather than emitting a stale snapshot.

#### Scenario: Concurrent ref, worktree or lock movement
- **WHEN** any observed named ref, worktree registration, worktree HEAD, worktree branch or worktree lock state changes during the pass, including a branch or worktree added or removed
- **THEN** the union of the before/after snapshots detects it, and the repository and candidate are marked `stale` and blocked
- **AND** no moved, added, removed or relocked candidate is ever `cleanupEligible` or presented as verified state

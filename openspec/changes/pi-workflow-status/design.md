## Context

`pi-defaults/workflow.py` already owns the project model (`context()`), the
raising Git helper (`git()`), primary-checkout resolution (`primary()`), the
Plane receipt helpers and the `main()` argparse tree; `status` reuses those
seams and adds no second project model or dependency. The caller
(`pi-defaults/prompts/mdev.md`) needs, before any write: exact SHAs, ownership,
clean/operation state, remote-`dev` ancestry and scoped Paseo evidence.

Observed, documented read surface (verified live, not assumed):

- `paseo project ls --json` -> `[{projectId, name, kind, path}]`.
- `paseo workspace ls --json` ->
  `[{workspaceId, project, name, isolation, cwd}]` (no HEAD/branch/clean).
- `paseo agent ls [--all] --json` ->
  `[{id, shortId, name, provider, thinking, status, cwd, created}]`;
  `--all` includes archived agents, so it is required to find released ones.
- `paseo agent inspect --json <id>` ->
  `{Id, Name, Provider, Model, Thinking, Status, Archived, ArchivedAt, Mode,
  Cwd, CreatedAt, UpdatedAt, LastUsage, Capabilities, AvailableModes,
  PendingPermissions, Worktree, ParentAgentId}`.
- `paseo status --json` is daemon-level (serverId/localDaemon/providers), not
  per-agent; it is not used for ownership.
- `git fetch --no-tags --refmap= <remote> refs/heads/<branch>` was validated to
  leave every named ref (including stale `refs/remotes/origin/dev`) untouched
  while moving `FETCH_HEAD` to the fresh remote tip.

Any payload that does not match these documented shapes fails closed.

## Goals / Non-Goals

Goals: a read-only, fail-closed inventory that distinguishes known-safe from
unknown-unsafe; exact evidence for delivery and cleanup decisions.
Non-goals: reconciliation, merge, push, archive, delete, Plane mutation,
workspace creation, installation, model/settings/daemon changes, cross-project
scanning.

## Decisions

**Command and exit contract.** `status [--cwd PATH] [--workspace ID]`.
Exit 0 with JSON whenever an inventory can be produced; every known-but-unsafe
candidate is an explicit per-item `blocked` entry. Exit non-zero with
`BLOCKED: <reason>` on stderr and **no stdout** only for a fatal observation:
unresolvable project/cwd, an unreadable or malformed Paseo payload, or an
explicit `--workspace` that is absent **or belongs to another project**.
`--workspace` narrows only the workspace observation; the project's full
repository/persistent-branch inventory is still produced, so it cannot bypass
scope or foreign isolation. A resolved root with **zero** canonical `project ls`
path matches is fatal (never an empty, safe-looking inventory); multiple matches
keep the frozen non-fatal `ownership: unknown` blocked inventory.

**Project scope.** `context(cwd)` supplies `root`, `layout`, `repositories`,
`persistentBranches` and `preserveBranches`. No other project, home directory
or unrelated repository is enumerated.

**Ownership is verifiable identity, not a display string.** From
`project ls`, canonicalize each `path` with the real path; the resolved project
id is the unique entry whose canonical path equals the canonical
`context["root"]`. Duplicate names or an ambiguous path yield `ownership:
unknown`. A workspace's `project` name maps to a unique project id; ownership is
`known` only when that id equals the resolved id **and** the canonical
`primary(expanded(cwd))` is one of the project's `repositories`. Otherwise it is
`unknown` (ambiguous) or `foreign` (different id/repo), and can never become
eligible. A `local` isolation workspace is the primary checkout and is never
eligible.

**Fetch, forge policy and race handling.** Default remote `origin`. When
`context["forge"]` is set, the remote URL must match the same policy
`receipt_repositories()` enforces; a violation blocks that repository before any
network call. Each configured persistent branch is fetched with
`--no-tags --refmap=` and its tip read from `FETCH_HEAD`, so named
remote-tracking refs are not opportunistically rewritten. A missing/failing
remote, or a missing/failing `dev`, blocks that repository (`remoteDev: null`,
`remoteDevError`) and never aborts the other repositories or the command. A
missing local branch is normal (`local: null`), never a command failure.

**Dirty, untracked, unfinished, detached, locked.** Per repository: `git
status --porcelain=v1` (untracked included); ignored untracked data from `git
ls-files --others --ignored --exclude-standard` (normal status is clean for it,
but archiving could destroy it, so a non-empty ignored list blocks cleanup);
in-progress operation from `MERGE_HEAD`, `CHERRY_PICK_HEAD`, `REVERT_HEAD`,
`rebase-merge/`, `rebase-apply/` or `BISECT_LOG` in both `git rev-parse --git-dir`
and the common dir; `detached` from `git symbolic-ref -q HEAD`; and the explicit
`locked` state from `git worktree list --porcelain`, which blocks cleanup by
policy regardless of cleanliness.

**Every Git read is checked.** Low-level helpers return a value plus an error
instead of raising, so a failed safety read blocks its candidate without
aborting the other repositories. `status`, ignored scan, git-dir/common-dir,
worktree list, ref snapshot, HEAD, symbolic-ref, local-ref and merge-base each
map a command error to an explicit blocker; the value is reported as unknown,
never coerced to clean or absent. The expected `rc 1` of `symbolic-ref` (detached)
and `merge-base --is-ancestor` (not an ancestor), and the expected missing local
branch of `rev-parse --verify --quiet`, are distinguished from `rc > 1` errors.
No Git blocker can ever yield `archiveEligible`.

**Branch/worktree inventory and pendingDelivery.** Beyond persistent branches,
enumerate local branches (`for-each-ref refs/heads/`) and registered worktrees
(`git worktree list --porcelain`) with their exact HEADs. Any local branch or
worktree HEAD not reachable from the fetched remote `dev` is a
`pendingDelivery` entry (a clean unpublished task tip is pending delivery, not
cleanup-eligible). The two-tier lookup distinguishes an absent local branch
(normal, `local: null`) from a failed command (blocked).

**Scoped agents and release proof.** `agent ls --all --json` once; for each
scoped workspace, `agent inspect --json <id>` only for agents whose expanded
`cwd` equals the workspace cwd (bounded). List rows are validated against every
documented field and type; an inspect payload that is not an object or whose
core fields (`Id`, `Status`, `Cwd`, `Archived`) drift is a per-candidate blocker
rather than a traceback. `released` is true only when **every** matching scoped
agent is affirmatively released: `Archived: true`, a **known idle status**
(documented observed value `idle`), an inspect `Id`/`Cwd` matching the workspace,
an explicit `PendingPermissions` list that is empty, and no busy/protected
condition. A missing `PendingPermissions` field is **unknown**, not empty. One
failed, malformed, non-archived, permission-pending, non-idle or protected
matching agent makes `released` false even when another matching agent is
archived and idle. A workspace is `busy` when any matching agent is not archived
or reports pending permissions, or a matching agent id equals the current runner
id (`PASEO_AGENT_ID`, `protected: true`). A missing runner id is `runner-unknown`:
the inventory is still produced, but no workspace is eligible. No documented
field proves queued work or terminal/service release, so no such field is
invented.

**Archive eligibility (observation only).** `archiveEligible` is true only for
`isolation == "worktree"` whose cwd is a registered, unlocked worktree of a
project repository, that cwd is not a primary checkout path, the branch is a
`task/` branch that is not `dev`, `main` or a configured preserve branch, and
with ownership known, not busy/protected, released, clean (no tracked/untracked/
ignored data), no unfinished operation, no Git or snapshot error, and HEAD
reachable from the fetched remote `dev`, with no ref movement. It additionally
requires **zero blockers** on both the repository and the workspace, so any
failed safety check disqualifies it. It is a report; `status` never archives, and
blocked/raced/locked/ignored candidates are never eligible.

**Ref-race guard.** A before/after snapshot of every observed named ref
(`refs/heads/*` per repository) plus every registered worktree's path, HEAD,
branch and `locked` state is compared at the end of the pass, over the **union**
of both key sets so additions and removals are detected; a moved, added, removed
or relocked candidate marks its repository `stale`, is reported blocked and is
never eligible.

**No writes.** Only `git fetch` (approved remotes) and read-only
`git`/`paseo` commands. No merge, push, archive, delete, checkout, Plane call or
file write. Fetch may change objects/`FETCH_HEAD` by design; that is not a
"no files touched" claim.

## Output shape

```
{
  "root", "layout", "planeProject",
  "repositories": [{
    "path", "current", "head", "detached", "dirty", "untracked": [],
    "ignored": [],
    "operation": null | "merge"|"cherry-pick"|"revert"|"rebase"|"bisect",
    "remoteDev", "remoteDevError",
    "branches": {name: {"local", "remote", "inRemoteDev", "diverged"}},
    "worktrees": [{"path", "branch", "head", "locked", "inRemoteDev"}],
    "blocked": ["<reason>"]
  }],
  "workspaces": [{
    "workspaceId", "project", "projectId", "name", "isolation", "cwd",
    "ownership": "known"|"unknown"|"foreign", "busy", "protected", "released",
    "head", "branch", "dirty", "ignored": [], "operation", "inRemoteDev",
    "archiveEligible", "blocked": ["<reason>"]
  }],
  "pendingDelivery": [{"kind": "branch"|"worktree", "path", "branch", "head",
                       "reason": "not-in-remote-dev"}],
  "cleanupEligible": [{"workspaceId", "cwd", "head"}],
  "blocked": [{"scope": "repo"|"workspace", "id", "reason"}]
}
```

## Risks / Trade-offs

- Requirement 5 (zero **or** `>1` canonical path match fatal) conflicts with the
  frozen test `test_status_blocks_ambiguous_project_identity`, which requires the
  `>1` case to exit 0 with a blocked `ownership: unknown` inventory. The frozen
  contract is byte-identical and takes precedence, so `>1` stays non-fatal and
  fail-closed; `0` is fatal as required. The parent owns reconciling this
  criterion.
- The Paseo CLI JSON is a contract, not a versioned API; any drift degrades to a
  blocked observation, never to a wrong `cleanupEligible`.
- Fetch-per-persistent-branch is network work, bounded to the resolved project's
  approved remotes; `--refmap=` keeps local named refs stable for the read-only
  promise.
- Requiring affirmative archival evidence means most live workspaces stay
  ineligible until their runner is released, which is the intended fail-closed
  posture.

## Privacy / Compatibility / Rollback

No data leaves the machine; Plane is untouched. The change is additive and the
five existing subcommands are unchanged. Rollback reverts the `status` subparser
and function and deletes `tests/pi_workflow_status.py`; no state is involved.

## Verification

Red first (product unedited): `python3 -m unittest tests.pi_workflow_status -v`
fails on the current CLI because `status` is rejected. Green later: the
unchanged `context` baseline plus the status scenarios with disposable Git
fixtures and a fake `paseo`; `openspec validate` is structural only and is never
implementation proof. No claim of a frozen contract is made until the parent
records the approved hash.

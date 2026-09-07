---
name: megai-task-flow
description: Coordinate Plane and .todos before project changes and at verified handoff. The parent owns boundaries; agents finish In Review, never Done.
---

# MEGAI Task Flow

The parent coordinates Plane and `.todos/` for every requested project file/code change. Pure questions and read-only investigations need no task. Delegated children inherit the parent's linked work item and never perform tracker/board mutations.

## Hard gates

- Treat Plane as the sole coordination source of truth at task boundaries.
- Treat `.todos` as the local ADLC execution source between boundaries.
- Stop before implementation when the required Plane boundary is unavailable or unauthenticated.
- Do not guess when workspace or project matching is ambiguous.
- Start work only after one Plane mutation leaves the work item in a started `In Progress` state.
- Finish agent work at Plane `In Review`; only the user may move it to `Done`.
- Every tracked MEGAI task must pass the mandatory delivery gate before Plane handoff. Main promotion remains a separate explicit user approval.

## Mandatory delivery gate

After verification and self-review, complete this gate for every tracked MEGAI task:

1. Inventory only the workers, registered worktrees, local task branches, and Paseo workspaces owned by the current task. For each worker record its Paseo workspace ID, worktree, branch, and reported committed tip; prove the branch tip exactly matches that tip and the worktree is clean. Preserve `dev`, `main`, the primary and orchestrator workspaces, and unrelated work.
2. Serially return to each current-task worker's registered worktree and run `megai finish --verified --target dev` once for every safely mergeable worker. `finish` handles one current worktree per invocation; repeat it serially until all safely mergeable current-task branches have been merged into `dev` and pushed. The first successful invocation creates or reuses the single `dev` → `main` PR/MR; later invocations reuse that same request. If any invocation exits nonzero, assume `dev` may have advanced, reconcile local/remote `dev`, the request, source worker, and inventory before retrying, and never archive that failure. Never use a global branch or sibling-worktree sweep.
3. Confirm the pushed `dev` contains every recorded committed tip with an exact-tip-and-clean proof (the recorded tip is an ancestor of `origin/dev`, and each source was clean and unchanged at finish). Do not treat `finish`'s first PR lookup result as cardinality proof: perform a complete open-request lookup and confirm exactly one open `dev` → `main` PR/MR. Duplicate, missing, incomplete, or uncertain lookup blocks handoff. Then confirm every safely merged current-task worktree and local task branch was cleaned by `finish`, and archive each successfully merged task workspace only after cleanup succeeds.
4. Pass the final current-task inventory gate: all task workers are accounted for—every safely merged worker is gone and archived, no safely merged current-task worker worktree or local task branch remains, and every corresponding Paseo archive succeeded. Any dirty, unmerged, failed, or ambiguous worker remains preserved and makes the gate fail. An orphan task-local branch may be cleaned only with explicit current-task ownership, merged-tip ancestry proof, and non-force `git branch -d` deletion; otherwise preserve it. Missing push, PR, cleanup, or Paseo archive blocks In Review. Report preserved exceptions; never handoff with them. Never sweep branches or worktrees.

Only after all four checks pass may the parent move the Plane work item to started `In Review`; leave it incomplete. Main promotion is never part of this gate.

## Project setup

1. Resolve the Git root and repository basename.
2. Locate or create `<root>/.todos/` with `todo.md`, `inprogress.md`, and `done.md`.
3. At a new task or resumed session, read `todo.md` and `inprogress.md` once. Read `done.md` only when resolving an existing task or completing work.
4. Reuse a known Plane project UUID and work item UUID from current context before searching.
5. List Plane projects through the API/MCP and consume every page. Require exactly one exact Git-root project name: zero or multiple means stop and ask. Never create a project implicitly. For managed worktrees reuse the parent's resolved repository/project identity, not the temporary worktree folder name.
6. Before any task mutation, list the project's workflow states with pagination. Require one exact `In Progress` and one exact `In Review` name, each with `group=started`; retain their UUIDs. Missing, duplicate, wrong-group, failed or incomplete responses block work: ask the user to resolve them rather than inventing IDs or silently creating/changing states.
7. For ordinary unlinked work, strip checkbox/priority/ADLC metadata and HTML markers from the local title. Consume every page of the project-scoped work-item list and compare that clean title to each exact `name`. One match: reuse its UUID. Multiple matches: stop and ask. Zero matches after a successful complete lookup: ask approval to create; after approval create one item with that exact title and the resolved `In Progress` state UUID, then record the returned `(project UUID, work item UUID)` pair in `.todos` before editing. Failed or incomplete lookup is never zero matches. If creation has an uncertain result, reconcile by lookup before retrying.
8. Existing `<!-- asana:GID -->` markers take precedence over title-based creation: match both `external_id=GID` and `external_source=asana-migration-v1` in the project-scoped Plane list; if filtering is unavailable, paginate and match locally. Require exactly one match before adding the Plane pair; zero or multiple matches block for reconciliation, never create a replacement. Preserve the original marker verbatim as history.

Boundary-only Plane sync: one start boundary and one verified handoff boundary. Reuse the active linked work item for follow-up refinements; load this skill and read the board once at task start/resume, not for each edit. A task already active in this session needs no repeated start mutation. Avoid routine reads, comments, and section changes between boundaries.

## Task identity

Store the Plane identity pair and any historical source marker at the end of the `.todos` line. Preserve the original imported marker verbatim until the pair is confirmed:

```markdown
- [ ] 🟠 📝 Fix login redirect <!-- plane:project-uuid/workitem-uuid --> <!-- asana:121234567890 -->
```

Keep both the Plane pair and `<!-- asana:GID -->` historical marker when moving the line or changing its ADLC stage. Do not rename the marker to `legacy-asana`, and never invent a second item while an identity lookup is unresolved.

## Status mapping

| State | `.todos` file | Plane state group | Agent action |
| --- | --- | --- | --- |
| Active from spec through ship | `inprogress.md` | started: `In Progress` | start boundary only |
| Verified; awaiting user review | `inprogress.md` (unchecked, 🔍 In Review) | started: `In Review` | handoff boundary |
| User marks Done; reconcile | `done.md` | completed state | user only |

`In Progress` and `In Review` remain in Plane's started group. Do not invent or synchronize a completion boolean for those states. Do not mirror individual ADLC stages to Plane. Stage emojis and transitions belong only in `.todos/inprogress.md`.

At each boundary, mutate Plane first and then move the `.todos` line. Stop and reconcile if either boundary write fails.

## Work cycle

1. Use the bounded execution contract: inspect the exact seam, implement the smallest complete change, self-review, run focused tests, then run the mandatory delivery gate.
2. Start boundary: follow the project, state and identity gates above. Reuse a linked pair directly; update an existing item with the resolved `In Progress` UUID once. For an approved new item, creation in that state is the start boundary, not a second update. Inspect the returned state and stop on failure or mismatch. Resolve an uncertain mutation before retrying.
3. Add the identity pair and historical marker to the `.todos` line and move it to `inprogress.md` at 📝 spec.
4. Cover bookkeeping stages in the same bounded implementation pass. UI verification is code-only unless explicitly requested.
5. Routine stage changes and milestone comments are forbidden. Do not dual-sync another tracker.
6. Run the mandatory delivery gate above, repeating verified `finish` serially for every current-task worker and passing its final inventory gate.
7. Handoff boundary: after verification and mandatory delivery succeed, move the Plane work item to started `In Review`; keep its linked line unchecked in `inprogress.md`, labelled 🔍 In Review. Only after observing the user's Done transition may reconciliation move the line to `done.md`.
8. Ask whether to promote `dev` to `main`; run promotion only after an explicit affirmative answer.
9. Stop after the current requested task; never auto-drain the queue or launch `/loop`.

## Reconciliation

Reconcile only when starting/resuming work and boundary state may differ, or when a boundary mutation fails:

1. Use the linked project/work-item UUID pair directly; never search while it is present.
2. Fetch only when local and remote boundary state may disagree.
3. Preserve local priority, ADLC stage, and the historical source marker.
4. Prefer Plane for title, state, assignment, and due-date conflicts.
5. Never create a second work item while a linked identity pair exists.

Pure questions and read-only investigations do not require a mirrored task. Never move unrelated work items or mark them complete.

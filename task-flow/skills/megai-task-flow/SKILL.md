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
- Repository delivery follows its worktree policy when required. Main promotion requires separate explicit user approval.

## Project setup

1. Resolve the Git root and repository basename.
2. Locate or create `<root>/.todos/` with `todo.md`, `inprogress.md`, and `done.md`.
3. At a new task or resumed session, read `todo.md` and `inprogress.md` once. Read `done.md` only when resolving an existing task or completing work.
4. Reuse a known Plane project UUID and work item UUID from current context before searching.
5. List Plane projects through the API/MCP and consume every page. The result must be exactly one exact Git-root project: zero means ask the user; multiple means stop and ask. Never create a project implicitly; never create a project implicitly while identity is unresolved.
6. For exactly one project, consume every page of its project-scoped work-item list. Resolve zero, one, or multiple matches explicitly: zero means ask before creating, one is usable, and multiple means stop and ask. An imported item is identified by the pair `(project UUID, work item UUID)`.
7. Resolve imported legacy work by matching both `external_id` and the actual `external_source=asana-migration-v1`; if the API cannot filter those fields, paginate and match locally. Never create a duplicate while identity is unresolved.

Boundary-only Plane sync: one start boundary and one verified handoff boundary. Reuse the active linked work item for follow-up refinements; load this skill and read the board once at task start/resume, not for each edit. A task already active in this session needs no repeated start mutation. Avoid routine reads, comments, and section changes between boundaries.

## Task identity

Store the Plane identity pair and any historical source marker at the end of the `.todos` line. Preserve the original imported marker verbatim until the pair is confirmed:

```markdown
- [ ] 🟠 📝 Fix login redirect <!-- asana:121234567890 plane:project-uuid/workitem-uuid -->
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

1. Use the bounded execution contract: inspect the exact seam, implement the smallest complete change, self-review, run focused tests, then stop or ship when required.
2. Start boundary: use the active `(project UUID, work item UUID)` directly. For an unlinked task, resolve the exact project and paginated work-item identity before mutating; zero or multiple matches are blocking outcomes. Put it in started `In Progress` in one mutation once the unique item is resolved; stop if the mutation fails.
3. Add the identity pair and historical marker to the `.todos` line and move it to `inprogress.md` at 📝 spec.
4. Cover bookkeeping stages in the same bounded implementation pass. UI verification is code-only unless explicitly requested.
5. Routine stage changes and milestone comments are forbidden. Do not dual-sync another tracker.
6. When required, run `megai finish --verified --target dev` and preserve the one promotion request policy.
7. Handoff boundary: after verification and required delivery succeed, move the Plane work item to started `In Review`; keep its linked line unchecked in `inprogress.md`, labelled 🔍 In Review. Only after observing the user's Done transition may reconciliation move the line to `done.md`.
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

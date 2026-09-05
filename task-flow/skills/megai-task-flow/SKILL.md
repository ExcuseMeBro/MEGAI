---
name: megai-task-flow
description: Coordinate Asana and .todos before project changes and at verified handoff. The parent owns boundaries; agents finish In Review, never Done.
---

# MEGAI Task Flow

The parent coordinates Asana and `.todos/` for every requested project file/code change. Pure questions and read-only investigations need no task. Delegated children inherit the parent's linked task and never perform tracker/board mutations.

## Hard gates

- Treat Asana as the coordination source of truth at task boundaries.
- Treat `.todos` as the local ADLC execution source between boundaries.
- Stop before implementation when required Asana access is unavailable or unauthenticated.
- Do not guess when workspace or project matching is ambiguous.
- Start work only after one Asana mutation leaves the task in `In Progress` with `completed=false`.
- Finish agent work at `In Review` with `completed=false`; only the user may move it to `Done`.
- Repository delivery follows its worktree policy: when required, verify, push dev, reuse one dev-to-main request, and clean the merged task worktree before handoff. Local configuration-only work does not invent a repository delivery step. Main promotion requires separate explicit user approval.

## Project setup

1. Resolve the Git root and repository basename.
2. Locate or create `<root>/.todos/` with `todo.md`, `inprogress.md`, and `done.md`.
3. At a new task or resumed session, read `todo.md` and `inprogress.md` once. Read `done.md` only when resolving an existing task or completing work.
4. Reuse a known project GID from current context before searching.
5. When the project is unknown, call `asana_search_objects` once for the exact repository basename. Never use premium `search_tasks`.
6. Require a unique exact project-name match; ask the user which project owns the task when absent or ambiguous. Never create a project implicitly.
7. Read sections only when their GIDs are unknown; reuse known `In Progress` and `In Review` section GIDs for later tasks. Ask if a required section is absent.

Boundary-only Asana sync: one start boundary and one verified handoff boundary. Reuse the active linked task for follow-up refinements; load this skill and read the board once at task start/resume, not for each edit. A task already active in this session needs no repeated start mutation. A follow-up after handoff returns the same task to `In Progress`. Avoid routine reads, comments, and section changes between boundaries.

## Task identity

Store the Asana task GID at the end of the `.todos` line:

```markdown
- [ ] 🟠 📝 Fix login redirect <!-- asana:121234567890 -->
```

Keep the marker when moving the line or changing its ADLC stage.
Never put the marker in the Asana task name.

For an unlinked `.todos` task:

1. Search the matched Asana project for the clean task title.
2. Reuse one exact match.
3. Create the task when no exact match exists.
4. Append its GID marker to the `.todos` line.
5. Ask before choosing between multiple exact matches.

## Status mapping

| State | `.todos` file | Asana section | Completed |
| --- | --- | --- | --- |
| Active from spec through ship | `inprogress.md` | `In Progress` | `false` |
| Verified; awaiting user review | `inprogress.md` (unchecked, 🔍 In Review) | `In Review` | `false` |
| User marked Done | `done.md` | `Done` | `true` |

Do not mirror individual ADLC stages to Asana. Stage emojis and transitions belong only in `.todos/inprogress.md`.

At each boundary, mutate Asana first and then move the `.todos` line. Stop and reconcile if either boundary write fails.

## Work cycle

1. **Use the bounded execution contract:** inspect the exact seam, implement, self-review the changed code, run focused tests, then ship only when required. Separate planning, reviewer, visual-QA, full-suite, and final-gate agents are opt-in or failure-driven.
2. **Start boundary:** before project edits, use the active linked GID directly. For an unlinked task, use at most one exact lookup, then reuse or create it. Put it in `In Progress` with `completed=false` in one mutation; stop and reconcile if that mutation fails.
3. Add the GID marker and move the local line to `inprogress.md` at 📝 spec.
4. Cover bookkeeping stages in the same bounded implementation pass. UI verification is code-only unless the user explicitly requests browser, simulator, screenshot, or design review.
5. Routine stage changes and milestone comments are forbidden. Never discover or sync Plane, Jira, or another tracker unless the user explicitly asks.
6. **Dev delivery boundary when required:** run `megai finish --verified --target dev`. It merges task work into `dev`, pushes `dev`, reuses one open `dev` → `main` request, and removes only merged task branches/registered worktrees.
7. **Handoff boundary:** after verification and required dev delivery succeed, move the Asana task to `In Review` with `completed=false`; keep its linked line unchecked in `inprogress.md`, labelled 🔍 In Review. Only after observing the user's Done transition may reconciliation move the line to `done.md`; agents never set `completed=true`.
8. Ask whether to promote `dev` to `main`. Run `megai promote --approved` only after an explicit affirmative answer; never infer approval or enable auto-merge.
9. Stop after the current requested task; never auto-drain the queue or launch `/loop`.

## Reconciliation

Reconcile only when starting/resuming work and boundary state may differ, or when a boundary mutation fails:

1. Use the linked Asana GID directly; never search while a marker exists.
2. Fetch only when local and remote boundary state may disagree.
3. Preserve local priority and ADLC stage metadata.
4. Prefer Asana for title, completion, assignment, and due-date conflicts.
5. Never create a second task while a linked GID exists.

Pure questions and read-only investigations do not require a mirrored task. Never move unrelated tasks or mark them complete.

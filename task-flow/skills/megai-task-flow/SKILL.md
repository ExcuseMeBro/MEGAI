---
name: megai-task-flow
description: Synchronizes MEGAI's per-project .todos execution board with Asana projects and tasks. Use for non-trivial project work when both Asana coordination and the local MEGAI task-flow must stay current.
---

# MEGAI Task Flow

Keep Asana and `.todos/` synchronized for tracked or high-risk project tasks. Bounded fast-path changes do not enter this protocol.

## Hard gates for tracked/high-risk work

- Treat Asana as the coordination source of truth at task boundaries.
- Treat `.todos` as the local ADLC execution source between boundaries.
- Stop before implementation when required Asana access is unavailable or unauthenticated.
- Do not guess when workspace or project matching is ambiguous.
- Start tracked work only after one Asana mutation leaves the task in `In Progress`.
- Complete tracked work only after verification and its required delivery succeed. A dev-to-main PR and worktree cleanup are required only when the task must ship through that lifecycle.

## Project setup

1. Resolve the Git root and repository basename.
2. Locate or create `<root>/.todos/` with `todo.md`, `inprogress.md`, and `done.md`.
3. At a new task or resumed session, read `todo.md` and `inprogress.md` once. Read `done.md` only when resolving an existing task or completing work.
4. Reuse a known project GID from current context before searching.
5. When the project is unknown, call `asana_search_objects` once for the exact repository basename. Never use premium `search_tasks`.
6. Create the project only when absent. Ask when multiple projects match.
7. Read sections only when their GIDs are unknown; reuse known `In Progress` and `Done` section GIDs for later tasks.

Boundary-only Asana sync is mandatory after a task enters this protocol: one start mutation and one completion mutation. Avoid routine reads, comments, and section changes between them.

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
| Verified and finished | `done.md` | `Done` | `true` |

Do not mirror individual ADLC stages to Asana. Stage emojis and transitions belong only in `.todos/inprogress.md`.

At each boundary, mutate Asana first and then move the `.todos` line. Stop and reconcile if either boundary write fails.

## Work cycle

1. **Classify first:** bounded localized copy/style/layout or presentation-only constant changes across at most three directly related files use the fast path only after an explicit blast-radius check confirms no public API/schema/auth/security/dependency/data-migration, production/CI/deployment, infrastructure, permissions, retention, destructive-behavior, or operational-config impact.
2. **Start boundary:** for tracked/high-risk work, use a linked GID directly. For an unlinked task, use at most one exact lookup, then reuse or create it. Put it in `In Progress` with `completed=false` in one mutation; stop and reconcile if that mutation fails.
3. Add the GID marker and move the local line to `inprogress.md` at 📝 spec.
4. Cover `spec → plan → generate → verify → review → ship` at risk-appropriate depth. Phase coverage does not require a separate model/tool round trip per label.
5. Routine stage changes and milestone comments are forbidden. Never discover or sync Plane, Jira, or another tracker unless the user explicitly asks.
6. **Ship boundary when required:** run `megai finish --verified --target dev` only when the tracked delivery requires commit/PR publication. It merges task work into `dev` when needed, pushes `dev`, opens/reuses a `dev` → `main` PR/MR, then removes only merged task branches/registered worktrees. Stop on dirty state, conflict, missing branches/remote, failed verification, forge/auth/push/PR failure, or ambiguous ownership. Never auto-merge `main`.
7. **Completion boundary:** after verification and any required delivery succeed, move the Asana task to `Done` and set `completed=true` in one mutation. Do not add a routine completion comment.
8. Move the local line to `done.md` and let the task-flow monitor regenerate `monitoring.md`.

## Reconciliation

Reconcile only when starting/resuming work and boundary state may differ, or when a boundary mutation fails:

1. Use the linked Asana GID directly; never search while a marker exists.
2. Fetch only when local and remote boundary state may disagree.
3. Preserve local priority and ADLC stage metadata.
4. Prefer Asana for title, completion, assignment, and due-date conflicts.
5. Never create a second task while a linked GID exists.

Pure questions and bounded fast-path changes do not require a mirrored task.

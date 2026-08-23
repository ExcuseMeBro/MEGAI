---
name: megai-task-flow
description: Synchronizes MEGAI's per-project .todos execution board with Asana projects and tasks. Use for non-trivial project work when both Asana coordination and the local MEGAI task-flow must stay current.
---

# MEGAI Task Flow

Keep Asana and `.todos/` synchronized for every non-trivial project task.

## Hard gates

- Treat Asana as the coordination source of truth.
- Treat `.todos/` as the local execution mirror.
- Stop before implementation when Asana is unavailable or unauthenticated.
- Do not guess when workspace or project matching is ambiguous.
- Do not start work until both stores show the task as in progress.
- Complete the task only after verification succeeds.

## Project setup

1. Resolve the Git root and repository basename.
2. Locate or create `<root>/.todos/` with `todo.md`, `inprogress.md`, and `done.md`.
3. Read all three files. Never edit `monitoring.md` directly.
4. Search Asana projects for the exact repository basename.
5. Create the project when absent. Ask when multiple projects match.
6. Ensure the project uses Board view with these sections:
   `Todo`, `In Progress`, `In Review`, and `Done`.
7. Read existing sections before adding or renaming sections.

Use `asana_search_objects` before specialized Asana search tools.

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

| State | `.todos` file | Asana section | Asana completed |
| --- | --- | --- | --- |
| Queued or paused | `todo.md` | `Todo` | `false` |
| Spec through verify | `inprogress.md` | `In Progress` | `false` |
| Review or ship | `inprogress.md` | `In Review` | `false` |
| Verified and finished | `done.md` | `Done` | `true` |

Move the Asana task first. Then move the `.todos` line.
Stop and report the mismatch if either write fails.
Reconcile the mismatch before implementation continues.

## Work cycle

1. Add or link the task in `todo.md` and Asana `Todo`.
2. Move it to `inprogress.md` and Asana `In Progress` before coding.
3. Run `spec → plan → generate → verify → review → ship`.
4. Preserve the existing priority and ADLC emojis in `.todos`.
5. Move Asana to `In Review` when the review stage begins.
6. Add Asana milestone and blocker comments when state materially changes.
7. After verification and review, move to `done.md` and Asana `Done`.
8. Set Asana `completed=true` only at the final transition.
9. Regenerate `.todos/monitoring.md` with the MEGAI task-flow monitor.

## Reconciliation

At each session start and before every status transition:

1. Re-read `.todos/`.
2. Fetch the linked Asana task by GID.
3. Apply the status mapping.
4. Preserve local priority and ADLC stage metadata.
5. Prefer Asana for title, completion, assignment, and due-date conflicts.
6. Never create a second task while a linked GID exists.

Pure questions and trivial one-line edits do not require a mirrored task.

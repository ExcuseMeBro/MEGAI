---
name: task-flow
description: "Priority-driven task queue. Plan -> break into small tasks -> queue with priority -> execute by priority with workflows. Use when the user gives any multi-step work request, when a new task arrives while work is in progress, or when the prompt carries a priority marker (!, !!, !!!, !!!!)."
allowed_tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Workflow
  - Skill
---

# task-flow

Standing protocol for tracked or high-risk work. The queue lives **only** in a per-project markdown board (`.todos/`) and follows risk-scaled ADLC phase coverage. Bounded fast-path changes skip the board entirely. The `.todos/` files are the single source of truth for work that enters this protocol.

## Project Board — the source of truth

Every project has a `.todos/` folder at its root:

```
.todos/
  todo.md         # 📋 pending tasks
  inprogress.md   # 🚧 active tasks (ideally one)
  done.md         # ✅ completed
  monitoring.md   # 📊 auto-generated dashboard — DO NOT hand-edit
```

**File = status.** A task is wherever its line lives — moving a task means cutting the line from one file and appending it to another.

**Task line format — use emoji** (priority emoji first, optional ADLC-stage emoji, then text):

```
- [ ] 🔴 🔨 Add payment flow      # urgent, in generate stage
- [ ] 🟡 Clean up the logs        # medium, no stage yet
```

| Priority | emoji | marker |
|----------|-------|--------|
| urgent | 🔴 | `!!!!` |
| high   | 🟠 | `!!!`  |
| medium | 🟡 | `!!` / none |
| low    | 🟢 | `!`    |

| Stage | emoji |
|-------|-------|
| spec / plan / generate / verify / review / ship | 📝 / 📐 / 🔨 / 🧪 / 🔍 / 🚀 |

**Always write emoji lines.** The `!`-markers and `(stage)` text are still parsed (for hand-typed input), but when *you* create or move a task, write the emoji form. The statusline and `monitoring.md` both read these emojis.

**Commands (deterministic, keep the board in sync):**

- `/ta <text>` — add a task to `todo.md`
- `/ts <text|index>` — **start**: move todo → `inprogress.md` (stage set to 📝 spec)
- `/tg <stage|next>` — **advance stage** of the in-progress task (spec→plan→generate→verify→review→ship)
- `/td <text|index>` — **done**: move → `done.md`
- `/tp <text|index>` — **pause**: move inprogress → `todo.md`

Prefer these over hand-editing — they move the line atomically and refresh `monitoring.md`.

**`monitoring.md` is auto-generated** by a hook on every board change (and by the commands) — it holds count tables by status, priority, and stage. Never edit it by hand; it regenerates from the other three files.

### Rules

**Choose the path first.**

- **Bounded fast path:** pure questions and localized copy/style/layout or presentation-only constant changes across at most three directly related files may skip Asana, `.todos`, worktrees, subagents, TDD, and commit/PR only after an explicit blast-radius check. Require an obvious acceptance condition, a focused behavioral/visual/diagnostic check, and no public API/schema/auth/security/dependency/data-migration, production/CI/deployment, infrastructure, permissions, retention, destructive-behavior, or operational-config impact. Batch independent reads, edit the narrowest seam, self-review the changed range, and stop. Target at most eight assistant requests; exceed that only for a concrete acceptance blocker.
- **Tracked/high-risk path:** multi-module or public-contract work, auth/security, schema/data/dependency migrations, production/CI/deployment or infrastructure configuration, permissions/retention/destructive behavior, explicitly tracked tasks, or explicit ship/PR requests. Order is analyze → satisfy the required external start boundary → write the local task → act.
- **Parallel implementation invariant:** when tracked/high-risk work has two or more independent implementation slices, the parent owns integration and fans them out in one batch. Give every writing agent one registered isolated worktree/task branch from the same `dev` baseline (`isolated: true` in OMP), define non-overlapping file ownership up front, and serialize shared-file or dependency-ordered boundaries. A single indivisible task uses one worktree.

For tracked/high-risk work:

1. **Locate or create the board once per task/resume.** Ensure `<project>/.todos/` contains `todo.md`, `inprogress.md`, and `done.md`.
2. **Read only what decides current work.** Read `todo.md` and `inprogress.md` once at task start, resume, or a new user turn where external edits are possible. Read `done.md` only to resolve prior identity or complete a task. Do not re-read unchanged board files between ADLC stages.
3. **The board, not memory, is the truth.** Re-read after a user edit, session resume, failed board mutation, or `/loop` boundary.
4. **Break work into small lines.** Split into independently completable units while keeping one active line.
5. **Execute by priority.** Move the selected line to `inprogress.md`, cover the required ADLC phases at risk-appropriate depth, then move it to `done.md`.
6. **Drain until empty.** After completion, read `todo.md` and `inprogress.md` once to select the next task.

## Inner Loop — risk-scaled ADLC

ADLC is phase coverage, not one tool/model round trip per phase. Collapse spec+plan and verify+review into the same pass when one evidence set covers both. Advance the stage with `/tg next` only when a tracked task actually crosses a boundary.

| # | Stage | Required outcome |
|---|-------|------------------|
| 1 | **spec** | Observable acceptance condition and risk classification. |
| 2 | **plan** | Narrowest responsible seam, affected callers, and verification choice. |
| 3 | **generate** | Smallest complete change; TDD only for a new observable contract or regression seam. |
| 4 | **verify** | Run the changed behavior or the narrowest test that proves acceptance. |
| 5 | **review** | Self-review focused changes; independent review only for material risk. |
| 6 | **ship** | Commit/PR/worktree lifecycle only when explicitly requested or required by the tracked delivery. |

Depth follows risk. Standard tracked work may cover several stages in one model turn and one evidence pass. High-risk work uses full TDD, independent review, and delivery gates. Never add a tracker, integration, full suite, or ship step after acceptance unless the task requires it.

## Priority Markers

The user encodes priority in the prompt. Mapping:

| Marker | Priority | Detection |
|--------|----------|-----------|
| `!!!!` | urgent   | run of 4 `!`, anywhere (attached or standalone) |
| `!!!`  | high     | run of 3 `!`, anywhere |
| `!!`   | medium   | run of 2 `!`, anywhere |
| `!`    | low      | single `!` only when **standalone** (whitespace/line boundary both sides) |
| none   | medium   | default |

- A single `!` attached to a word (`done!`, `login page!`) is **normal punctuation, not a marker** — ignore it.
- Markers may appear anywhere in the prompt. If several appear for one task, use the highest.
- Write the priority as an **emoji prefix** on the task line in `todo.md` (`- [ ] 🟠 the task`). The statusline shows it and orders the queue by it. Quickest way to add: the `/ta` command (`/ta fix the login bug !!!`) converts the marker to an emoji and appends it for you.

## Urgent Preemption

When an **urgent** (`!!!!`) task arrives while another task is `in_progress`:

1. **Pause** the running task: move its line back to `todo.md`. It keeps its place by priority.
2. **Create + run** the urgent task to completion.
3. **Resume** the paused task: move it back to `inprogress.md` and continue.

High/medium/low tasks do **not** preempt — they wait their turn. Only urgent interrupts.

## Gotchas

- **Never skip a required outcome on the tracked/high-risk path.** Do not manufacture separate tool calls for each ADLC label; one direct evidence pass may cover multiple adjacent phases.
- Default primary work to `dev`; create task worktrees from `dev`. At ship, `megai finish --verified --target dev` merges when needed, pushes `dev`, and opens/reuses a `dev` → `main` PR/MR. Never auto-merge `main`; delete only merged task branches and registered linked worktrees.
- **Use TDD where it buys regression proof.** Write a failing test first for a new observable contract or a reproduced bug with a correct seam. Do not create plumbing tests for bounded copy/style/layout changes.
- **Advance the stage emoji as you go.** Update 📝→📐→🔨→🧪→🔍→🚀 in `inprogress.md` at each transition so the statusline + `monitoring.md` reflect reality. A task stuck on 📝 while you write code means the marker is lying.
- **Do not poll the board between stages.** Re-read only at a new user turn, session resume, failed mutation, explicit `/loop` boundary, or known external edit.
- **Keep one line in `inprogress.md`.** Moving several tasks to in-progress at once destroys the "what am I doing now" signal and breaks the timer/stage display. Finish or move the current one back to `todo.md` before starting the next.
- **Move lines, don't duplicate them.** When advancing status, cut the line from the old file before appending to the new one. A task appearing in both `todo.md` and `done.md` is a sync bug.
- **Claude is turn-based — "never stops" is bounded.** True background continuation while the user types is impossible. What this protocol guarantees: the queue persists, in-progress work is never silently dropped, urgent preempts, and the queue is drained within each turn. For hands-off draining, the user must start `/loop`.
- **Single `!` is usually punctuation.** Do not downgrade a normal sentence ending in `!` to low priority. Only a standalone `!` token counts.
- **Terse wording does not define risk.** Classify by blast radius and acceptance. Bounded localized changes use the fast path; risky changes still require an explicit plan.
- **`.todos/` is the ONLY task store.** There is no session/Task-tools mirror. Every status change is a file edit (move the line between `todo.md` / `inprogress.md` / `done.md`). If the files and reality disagree, the files win — fix them.
- **Put a priority marker on every line.** A line with no marker defaults to medium; the statusline still shows and orders it, but be explicit for anything non-default.
- **Resume after urgent — don't forget the paused task.** After an urgent preemption completes, the previously-running task is back in `todo.md`; pick it up rather than leaving it stranded.
- **One line in `inprogress.md` at a time.** More than one destroys the "what am I doing now" signal. Move the current one to `done.md` (or back to `todo.md`) before starting the next.

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

Standing protocol. The queue lives **only** in a per-project markdown board (`.todos/`), executed by priority through the **full ADLC** (AI Development Life Cycle). No stage is skipped. The `.todos/` files are the single source of truth — there is no other task store; keep them in sync at all times by editing them as status changes.

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

**Order is fixed: analyze → satisfy any required external start boundary → write the local task → act.** Pure questions and trivial one-liners are answered directly without a board entry.

1. **Locate or create the board once per task/resume.** Ensure `<project>/.todos/` contains `todo.md`, `inprogress.md`, and `done.md`.
2. **Read only what decides current work.** Read `todo.md` and `inprogress.md` once at task start, resume, or a new user turn where external edits are possible. Read `done.md` only to resolve prior identity or complete a task. Do not re-read unchanged board files between ADLC stages.
3. **The board, not memory, is the truth.** Re-read after a user edit, session resume, failed board mutation, or `/loop` boundary.
4. **Break work into small lines.** Split into independently completable units while keeping one active line.
5. **Execute by priority.** Move the selected line to `inprogress.md` before implementation, run full ADLC, then move it to `done.md`.
6. **Drain until empty.** After completion, read `todo.md` and `inprogress.md` once to select the next task.

## Inner Loop — ADLC (every task runs all 6 stages)

Advance the stage with `/tg next` (or `/tg generate`, etc.) as you enter each — it updates the stage emoji (📝→📐→🔨→🧪→🔍→🚀) on the in-progress line and refreshes the statusline + `monitoring.md`. `/ts` enters at 📝 spec.

| # | Stage | Do | Tools |
|---|-------|----|----|
| 1 | **spec** | Clarify intent, requirements, acceptance criteria. | `brainstorming`, `/spartan:spec` |
| 2 | **plan** | Design + ordered steps + key files/risks. No plan → no code. | `writing-plans`, `/spartan:plan` |
| 3 | **generate** | Write code **test-first** (red → green → refactor). | `tdd`, `Workflow` for big/parallel work |
| 4 | **verify** | Run tests, lint, build; confirm behaviour against acceptance criteria. | `verify`, run the app |
| 5 | **review** | Independent review before shipping (dual-agent for real changes). | `/spartan:gate-review`, `/code-review` |
| 6 | **ship** | Commit / PR with description; iterate on feedback. | `/spartan:pr-ready` |

**Scale depth to size:** a full feature runs each stage with its heavy tool; a small task still touches every stage but lightly (spec = one line, plan = mental, review = self `/code-review`). Genuinely trivial single-file typo edits run a minimal spec→generate→verify and skip formal review/ship gates. **Use `Workflow` to drive the heavy stages** (generate across many files, parallel review) when a task is substantial.

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

- **Never skip an ADLC stage.** The order is spec → plan → generate → verify → review → ship. Jumping straight to generate (code without spec/plan) or shipping without verify+review is the failure this protocol exists to prevent. Scale the depth, not the coverage.
- **`generate` means test-first.** Don't write implementation then bolt on tests. Red (failing test) → green (make it pass) → refactor. That is the generate stage, not a separate optional step.
- **Advance the stage emoji as you go.** Update 📝→📐→🔨→🧪→🔍→🚀 in `inprogress.md` at each transition so the statusline + `monitoring.md` reflect reality. A task stuck on 📝 while you write code means the marker is lying.
- **Do not poll the board between stages.** Re-read only at a new user turn, session resume, failed mutation, explicit `/loop` boundary, or known external edit.
- **Keep one line in `inprogress.md`.** Moving several tasks to in-progress at once destroys the "what am I doing now" signal and breaks the timer/stage display. Finish or move the current one back to `todo.md` before starting the next.
- **Move lines, don't duplicate them.** When advancing status, cut the line from the old file before appending to the new one. A task appearing in both `todo.md` and `done.md` is a sync bug.
- **Claude is turn-based — "never stops" is bounded.** True background continuation while the user types is impossible. What this protocol guarantees: the queue persists, in-progress work is never silently dropped, urgent preempts, and the queue is drained within each turn. For hands-off draining, the user must start `/loop`.
- **Single `!` is usually punctuation.** Do not downgrade a normal sentence ending in `!` to low priority. Only a standalone `!` token counts.
- **Don't skip the plan on "just do X" phrasing.** A terse instruction is still a task — plan and split it. The exception is genuinely trivial single-file edits (typo, one-liner), which run without the full protocol.
- **`.todos/` is the ONLY task store.** There is no session/Task-tools mirror. Every status change is a file edit (move the line between `todo.md` / `inprogress.md` / `done.md`). If the files and reality disagree, the files win — fix them.
- **Put a priority marker on every line.** A line with no marker defaults to medium; the statusline still shows and orders it, but be explicit for anything non-default.
- **Resume after urgent — don't forget the paused task.** After an urgent preemption completes, the previously-running task is back in `todo.md`; pick it up rather than leaving it stranded.
- **One line in `inprogress.md` at a time.** More than one destroys the "what am I doing now" signal. Move the current one to `done.md` (or back to `todo.md`) before starting the next.

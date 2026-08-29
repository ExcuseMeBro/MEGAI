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

- **Default fast path:** for every task, run one bounded inspect → implement → code self-review → focused-test sequence. Do not add separate planner, reviewer, UI/design, browser, final-gate, or full-suite agents unless the user explicitly asks or the focused test fails. UI checks are code-only by default: structure, states, accessibility semantics, token/style usage, diagnostics, and component tests; the user owns visual/manual review.
- **Tracked/high-risk path:** multi-module or public-contract work, auth/security, schema/data/dependency migrations, production/CI/deployment or infrastructure configuration, permissions/retention/destructive behavior, explicitly tracked tasks, or explicit ship/PR requests. Order is analyze → satisfy the required external start boundary → write the local task → act.
- **Parallel implementation invariant:** when tracked/high-risk work has two or more independent implementation slices, the parent owns integration. Inside Paseo, create one visible managed worktree workspace per writer from `dev`, then launch the writer with that workspace ID; read-only workers remain tabs in the parent workspace. Outside Paseo, native isolated task worktrees are allowed. Define non-overlapping ownership up front and serialize shared-file or dependency boundaries.

For tracked/high-risk work:

1. **Locate or create the board once per task/resume.** Ensure `<project>/.todos/` contains `todo.md`, `inprogress.md`, and `done.md`.
2. **Read only what decides current work.** Read `todo.md` and `inprogress.md` once at task start, resume, or a new user turn where external edits are possible. Read `done.md` only to resolve prior identity or complete a task. Do not re-read unchanged board files between ADLC stages.
3. **The board, not memory, is the truth.** Re-read after a user edit, session resume, or failed board mutation.
4. **Break work into small lines.** Split into independently completable units while keeping one active line.
5. **Execute the selected task only.** Move it to `inprogress.md`, implement, self-review the changed code, run focused tests, then move it to `done.md`.
6. **Stop after the requested task.** Never auto-drain queued tasks or start an autonomous loop.

## Bounded execution

ADLC labels are bookkeeping, not separate model/tool passes. The execution contract is implement → self-review → focused test → ship when required. Advance the stage with `/tg next` only when a tracked task actually crosses a boundary.

| # | Stage | Required outcome |
|---|-------|------------------|
| 1 | **spec** | Observable acceptance condition and risk classification. |
| 2 | **plan** | Narrowest responsible seam, affected callers, and verification choice. |
| 3 | **generate** | Smallest complete implementation; no automatic TDD loop. |
| 4 | **verify** | Run the narrowest test or diagnostic that proves the changed code. |
| 5 | **review** | Self-review the focused diff for correctness, quality, and unnecessary complexity. |
| 6 | **ship** | Commit/PR/worktree lifecycle only when explicitly requested or required by the tracked delivery. |

Depth follows the user's task. Independent review, full TDD, full suites, security/design audits, visual QA, and final-gate agents run only when explicitly requested or when a focused failure requires escalation.

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

- **Keep execution bounded.** One direct evidence pass may cover multiple adjacent ADLC labels; never create a tool or model round trip for a label.
- Default primary work to `dev`; create task worktrees from `dev`. At ship, `megai finish --verified --target dev` merges when needed, pushes `dev`, and opens/reuses a `dev` → `main` PR/MR. Never auto-merge `main`; delete only merged task branches and registered linked worktrees.
- **Test after implementation.** Use the narrowest existing test, typecheck, lint, or build check that covers the change. Add a regression test only when the user asks or the new observable contract otherwise has no focused proof.
- **Advance the stage emoji as you go.** Update 📝→📐→🔨→🧪→🔍→🚀 in `inprogress.md` at each transition so the statusline + `monitoring.md` reflect reality. A task stuck on 📝 while you write code means the marker is lying.
- **Do not poll the board between stages.** Re-read only at a new user turn, session resume, failed mutation, or known external edit.
- **Keep one line in `inprogress.md`.** Moving several tasks to in-progress at once destroys the "what am I doing now" signal and breaks the timer/stage display. Finish or move the current one back to `todo.md` before starting the next.
- **Move lines, don't duplicate them.** When advancing status, cut the line from the old file before appending to the new one. A task appearing in both `todo.md` and `done.md` is a sync bug.
- **No autonomous loops.** Do not invoke `/loop`, auto-drain `.todos`, or continue into unrelated queued work. Finish the current user-requested task and stop.
- **Single `!` is usually punctuation.** Do not downgrade a normal sentence ending in `!` to low priority. Only a standalone `!` token counts.
- **Terse wording does not define risk.** Classify by blast radius and acceptance, but keep the same bounded implementation/self-review/test path unless the user requests a specialty.
- **`.todos/` is the ONLY task store.** There is no session/Task-tools mirror. Every status change is a file edit (move the line between `todo.md` / `inprogress.md` / `done.md`). If the files and reality disagree, the files win — fix them.
- **Put a priority marker on every line.** A line with no marker defaults to medium; the statusline still shows and orders it, but be explicit for anything non-default.
- **Resume after urgent — don't forget the paused task.** After an urgent preemption completes, the previously-running task is back in `todo.md`; pick it up rather than leaving it stranded.
- **One line in `inprogress.md` at a time.** More than one destroys the "what am I doing now" signal. Move the current one to `done.md` (or back to `todo.md`) before starting the next.

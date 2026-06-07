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
  - TaskCreate
  - TaskUpdate
  - TaskList
  - TaskGet
  - Task
  - Workflow
  - Skill
---

# task-flow

Standing protocol. The queue lives in a **per-project markdown board**, executed by priority through the **full ADLC** (AI Development Life Cycle). No stage is skipped.

## Project Board — the source of truth

Every project has a `.todos/` folder at its root with three files:

```
.todos/
  todo.md         # pending tasks
  inprogress.md   # active tasks (ideally one)
  done.md         # completed
```

**File = status.** A task is wherever its line lives — moving a task means cutting the line from one file and appending it to another.

**Task line format** (priority + ADLC stage optional, so hand-edited lines work too):

```
- [ ] !!! (generate) Add payment flow
- [ ] do a simple thing          # no marker = medium, stage defaults to spec
```

Priority markers: `!`=low (standalone), `!!`=medium, `!!!`=high, `!!!!`=urgent. Stage in `(...)`: one of `spec plan generate verify review ship`.

### Rules

1. **Always locate or create the board first.** At the start of every task — and every `/loop` iteration — find `<project>/.todos/`. If missing, create the folder and the three files (with `# TODO` / `# IN PROGRESS` / `# DONE` headers). Then **read all three**.
2. **The board, not memory, is the truth. Re-read every loop.** The user may edit, add, reorder, or delete lines between turns. Pick up those changes on the next read and continue from the board's current state — never from a stale in-memory list.
3. **Break work into small lines.** Split into the smallest independently-completable units (3–8 beats one vague task). Append new tasks to `todo.md` with a priority marker.
4. **Queue, never discard.** A new task arriving mid-work is **added** to `todo.md`, not a reason to abandon the in-progress one.
5. **Execute by priority.** Take the highest-priority line in `todo.md`. Move it to `inprogress.md`, run its full ADLC, then move it to `done.md` (`[x]`).
6. **Drain until empty.** After a task moves to done, re-read and continue with the next by priority until `todo.md` + `inprogress.md` are empty or user input is needed. For unattended draining, suggest `/loop`.

## Inner Loop — ADLC (every task runs all 6 stages)

Advance the stage by editing the `(stage)` token on the task's line in `inprogress.md` as you enter each — the statusline reads it and shows `◐ n/6 <stage>` on the active task. (For projects driven by the Task tools instead of a board, use `TaskUpdate { taskId, metadata: { stage } }`.)

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
- Strip the marker from the task text before saving the subject.
- Pass priority into every `TaskCreate` via `metadata`: `metadata: { priority: "urgent" | "high" | "medium" | "low" }`. The task-state hook reads this; the statusline shows it (‼ urgent, ! high, ↓ low) and orders the queue by it.

## Urgent Preemption

When an **urgent** (`!!!!`) task arrives while another task is `in_progress`:

1. **Pause** the running task: move its line back to `todo.md` (or `TaskUpdate { taskId, status: "pending" }`). It keeps its place by priority.
2. **Create + run** the urgent task to completion.
3. **Resume** the paused task: move it back to `inprogress.md` and continue.

High/medium/low tasks do **not** preempt — they wait their turn. Only urgent interrupts.

## Gotchas

- **Never skip an ADLC stage.** The order is spec → plan → generate → verify → review → ship. Jumping straight to generate (code without spec/plan) or shipping without verify+review is the failure this protocol exists to prevent. Scale the depth, not the coverage.
- **`generate` means test-first.** Don't write implementation then bolt on tests. Red (failing test) → green (make it pass) → refactor. That is the generate stage, not a separate optional step.
- **Advance the stage marker as you go.** Edit the `(stage)` token in `inprogress.md` at each transition so the statusline reflects reality. A task stuck showing `1/6 spec` while you write code means the marker is lying.
- **Re-read the board every loop — trust the files, not your memory.** The user edits `todo.md`/`inprogress.md` between turns. If you skip the re-read, you will work a stale list and miss tasks the user added or reprioritised.
- **Keep one line in `inprogress.md`.** Moving several tasks to in-progress at once destroys the "what am I doing now" signal and breaks the timer/stage display. Finish or move the current one back to `todo.md` before starting the next.
- **Move lines, don't duplicate them.** When advancing status, cut the line from the old file before appending to the new one. A task appearing in both `todo.md` and `done.md` is a sync bug.
- **Claude is turn-based — "never stops" is bounded.** True background continuation while the user types is impossible. What this protocol guarantees: the queue persists, in-progress work is never silently dropped, urgent preempts, and the queue is drained within each turn. For hands-off draining, the user must start `/loop`.
- **Single `!` is usually punctuation.** Do not downgrade a normal sentence ending in `!` to low priority. Only a standalone `!` token counts.
- **Don't skip the plan on "just do X" phrasing.** A terse instruction is still a task — plan and split it. The exception is genuinely trivial single-file edits (typo, one-liner), which run without the full protocol.
- **Set `metadata.priority` on every TaskCreate.** If you omit it, the task defaults to medium and the statusline can't show or order it correctly.
- **Resume after urgent — don't forget the paused task.** After an urgent preemption completes, the previously-running task is still `pending`; pick it back up rather than leaving it stranded.
- **One task `in_progress` at a time.** Marking several `in_progress` makes the "what am I doing now" signal meaningless. Start the next only after completing or pausing the current.

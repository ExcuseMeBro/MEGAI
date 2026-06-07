<!-- megai:task-flow:begin -->
# task-flow + ADLC (ALWAYS for every real task)
- **task-flow** (`~/.claude/skills/task-flow/SKILL.md`) — per-project markdown board + priority queue + full ADLC per task.
- For ANY **task** (beyond a trivial one-liner), invoke the Skill tool with `skill: "task-flow"` BEFORE acting.
- **Project board is the source of truth.** Every project has `.todos/` with `todo.md` / `inprogress.md` / `done.md` (file = status). Always locate it or create it first, and **re-read it every turn / every `/loop` iteration** — the user may edit the files, and those edits drive the work. Move task lines between files as status changes; never work from a stale in-memory list.
- **Every task runs the full ADLC, no stage skipped:** `spec → plan → generate (test-first/TDD) → verify → review → ship`. Scale the depth to task size, never the coverage. Advance the stage by editing the `(stage)` token in `inprogress.md` so the statusline shows `◐ n/6 <stage>`.
- Priority markers in the prompt (anywhere): `!`=low (standalone only), `!!`=medium, `!!!`=high, `!!!!`=urgent; no marker = medium. Always obey the prompt's priority. Urgent (`!!!!`) preempts the running task.
<!-- megai:task-flow:end -->

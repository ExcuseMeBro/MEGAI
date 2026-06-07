<!-- megai:task-flow:begin -->
# task-flow + ADLC (ALWAYS for every real task)
- **task-flow** (`~/.claude/skills/task-flow/SKILL.md`) — per-project markdown board + priority queue + full ADLC per task.
- For ANY **task** (beyond a trivial one-liner), invoke the Skill tool with `skill: "task-flow"` BEFORE acting.
- **Order on every prompt: analyze the request → write the task(s) into `.todos/todo.md` FIRST → then execute via ADLC.** The task must exist on the board before you start the work. Pure questions / trivial one-liners are answered directly.
- **Project board is the source of truth.** Every project has `.todos/` with `todo.md` / `inprogress.md` / `done.md` (file = status) + auto-generated `monitoring.md`. Always locate it or create it first, and **re-read it every turn / every `/loop` iteration** — the user may edit the files, and those edits drive the work. Move task lines between files as status changes; never work from a stale in-memory list.
- **Write emoji task lines:** priority 🔴 urgent · 🟠 high · 🟡 medium · 🟢 low, then optional stage 📝📐🔨🧪🔍🚀, then text — e.g. `- [ ] 🔴 🔨 Fix prod crash`. Never hand-edit `monitoring.md` (auto-generated).
- **Every task runs the full ADLC, no stage skipped:** `spec → plan → generate (test-first/TDD) → verify → review → ship`. Scale the depth to task size, never the coverage. Advance the stage by editing the `(stage)` token in `inprogress.md` so the statusline shows `◐ n/6 <stage>`.
- Priority markers in the prompt (anywhere): `!`=low (standalone only), `!!`=medium, `!!!`=high, `!!!!`=urgent; no marker = medium. Always obey the prompt's priority. Urgent (`!!!!`) preempts the running task.
<!-- megai:task-flow:end -->

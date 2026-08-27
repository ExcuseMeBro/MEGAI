<!-- megai:task-flow:begin -->
# Boundary-only Asana sync + task-flow + ADLC
- **Asana boundary sync:** for every non-trivial task, create/reuse the Asana task and set `In Progress` before implementation; after verification, set `Done` + `completed=true`. These are the only routine Asana mutations.
- Reuse linked task/project/section GIDs. Use `asana_search_objects` only when identity is unknown; never use premium `search_tasks`. Do not add routine milestone/completion comments or mirror ADLC stages to Asana. Comment only for a real external blocker.
- **task-flow** (`~/.claude/skills/task-flow/SKILL.md`) is the local execution mirror. After the Asana start boundary, add one linked line to `.todos/inprogress.md`.
- At a new task or resumed session, read `todo.md` and `inprogress.md` once. Read `done.md` only to resolve prior identity or complete work. Do not re-read unchanged board files at every stage.
- **Write emoji task lines:** priority 🔴 urgent · 🟠 high · 🟡 medium · 🟢 low, then stage 📝📐🔨🧪🔍🚀. Never hand-edit `monitoring.md`.
- **Every task runs full ADLC:** `spec → plan → generate (test-first/TDD) → verify → review → ship`. Stage changes are local `.todos` edits only.
- Asana unavailable/unauthenticated blocks code changes. A failed boundary write must be reconciled before proceeding.
- Priority markers: `!` low · `!!` medium · `!!!` high · `!!!!` urgent; no marker = medium. Only urgent preempts active work.
<!-- megai:task-flow:end -->

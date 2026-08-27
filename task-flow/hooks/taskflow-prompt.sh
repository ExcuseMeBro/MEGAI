#!/usr/bin/env bash
# UserPromptSubmit hook — keeps local task state cheap and boundary-driven.
# Output on stdout is injected as additional context for the turn.
# Pure questions, trivial edits, and steering for the already-active task avoid
# board discovery and repeated reads.
cat <<'EOF'
[task-flow] For actionable work: satisfy any required external start boundary once, then create or resume one local task. Read only .todos/todo.md and .todos/inprogress.md when starting/resuming work, the queue changed, or a prior mutation failed; read done.md only for identity lookup or completion. Do not re-read unchanged board files between ADLC stages or for steering on the active task. Keep one line in inprogress.md and run full ADLC locally: spec -> plan -> generate (test-first) -> verify -> review -> ship. External systems sync only at their start/completion boundaries; never mirror local stages or routine comments. Pure questions and trivial single-edits skip the board.
EOF

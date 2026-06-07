#!/usr/bin/env bash
# UserPromptSubmit hook — enforces the task-flow order on every prompt:
# analyze the request, create the task(s) in .todos FIRST, then run the ADLC.
# Output on stdout is injected as additional context for the turn.
# Pure questions / trivial one-liners are explicitly exempt so chat stays light.
cat <<'EOF'
[task-flow] Handle this request in order: (1) ANALYZE it. If it is actionable work (not a pure question or trivial one-liner): (2) re-read .todos/ (create it if missing), (3) write the task(s) into .todos/todo.md FIRST, each with a priority marker (! low, !! medium, !!! high, !!!! urgent), (4) move the task you start into inprogress.md, (5) execute it through the FULL ADLC — spec -> plan -> generate (test-first) -> verify -> review -> ship — advancing the (stage) token as you go, (6) move it to done.md, then drain the rest by priority. Urgent (!!!!) preempts the running task. Pure questions and trivial single-edits skip the board and are answered directly.
EOF

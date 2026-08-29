#!/usr/bin/env bash
# UserPromptSubmit hook — keeps local task state cheap and boundary-driven.
# Output on stdout is injected as additional context for the turn.
# Pure questions, trivial edits, and steering for the already-active task avoid
# board discovery and repeated reads.
cat <<'EOF'
[task-flow] Execute only the user's current task through one bounded inspect -> implement -> code self-review -> focused-test sequence. Do not launch separate planner, reviewer, final-gate, visual-QA, browser, full-suite, or autonomous-loop work unless the user explicitly requests it or the focused test fails. UI checks are code-only by default; report visual/manual review as user-owned. For tracked work, satisfy the required Asana start boundary once, keep one linked local task, ship through dev when required, mark Done, then stop.
EOF

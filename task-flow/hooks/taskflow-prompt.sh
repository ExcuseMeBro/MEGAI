#!/usr/bin/env bash
# UserPromptSubmit hook — keeps local task state cheap and boundary-driven.
# Output on stdout is injected as additional context for the turn.
# Pure questions, trivial edits, and steering for the already-active task avoid
# board discovery and repeated reads.
cat <<'EOF'
[task-flow] Execute only the user's current task through one bounded inspect -> implement -> code self-review -> focused-test sequence. No automatic planner, reviewer, visual-QA, full-suite, or loop work. For tracked delivery, run `megai finish --verified --target dev`, reuse one open dev-to-main request, clean the task worktree, mark Done, then ask whether to promote main. Run `megai promote --approved` only after an explicit affirmative reply.
EOF

#!/usr/bin/env bash
# UserPromptSubmit hook — keeps local task state cheap and boundary-driven.
# Output on stdout is injected as additional context for the turn.
# Pure questions, trivial edits, and steering for the already-active task avoid
# board discovery and repeated reads.
cat <<'EOF'
[task-flow] Execute only the current task through inspect -> implement -> code self-review -> focused test. External app/device review requires an explicit user request; do not infer permission from routine implementation or verification. For tracked delivery, finish through dev, mark Done, then ask before main promotion.
EOF

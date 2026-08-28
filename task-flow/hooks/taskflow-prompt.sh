#!/usr/bin/env bash
# UserPromptSubmit hook — keeps local task state cheap and boundary-driven.
# Output on stdout is injected as additional context for the turn.
# Pure questions, trivial edits, and steering for the already-active task avoid
# board discovery and repeated reads.
cat <<'EOF'
[task-flow] Use the bounded fast path only for pure questions and localized copy/style/layout or presentation-only constant changes across at most three directly related files after an explicit blast-radius check confirms no public API/schema/auth/security/dependency/data-migration, production/CI/deployment, infrastructure, permissions, retention, destructive-behavior, or operational-config impact: skip Asana, .todos, worktrees, subagents, TDD, and commit/PR; batch reads, make the narrow edit, run one focused behavioral/visual/diagnostic check, self-review, and stop. Target at most eight assistant requests. For tracked/high-risk work, satisfy the external start boundary once, create or resume one local task, read todo.md and inprogress.md once, and cover spec -> plan -> generate -> verify -> review -> ship at risk-appropriate depth without forcing one tool/model round trip per phase. Never discover or sync another tracker unless the user asks.
EOF

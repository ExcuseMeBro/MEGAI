---
description: Set or advance the in-progress task's ADLC stage
argument-hint: <spec|plan|generate|verify|review|ship|next> [task]
allowed-tools: Bash(node:*)
---

!`node ~/.claude/hooks/taskflow-move.js stage "$ARGUMENTS"`

Stage updated on the in-progress task — the statusline and `monitoring.md` now reflect it. Continue the ADLC work for this stage.

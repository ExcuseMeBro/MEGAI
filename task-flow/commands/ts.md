---
description: Start a task — move it from todo.md to inprogress.md
argument-hint: <task text or index>
allowed-tools: Bash(node:*)
---

!`node ~/.claude/hooks/taskflow-move.js start "$ARGUMENTS"`

The task is now in `inprogress.md`. Cover spec → plan → generate → verify → review → ship at risk-appropriate depth, collapsing phases into the same evidence pass when safe; advance the stage emoji as the work crosses each boundary.

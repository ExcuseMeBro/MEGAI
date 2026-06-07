---
description: Start a task — move it from todo.md to inprogress.md
argument-hint: <task text or index>
allowed-tools: Bash(node:*)
---

!`node ~/.claude/hooks/taskflow-move.js start "$ARGUMENTS"`

The task is now in `inprogress.md`. Work it through the full ADLC (spec → plan → generate → verify → review → ship), advancing its stage emoji as you go.

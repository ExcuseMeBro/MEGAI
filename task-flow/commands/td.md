---
description: Mark a task done — move it to done.md
argument-hint: <task text or index>
allowed-tools: Bash(node:*)
---

!`node ~/.claude/hooks/taskflow-move.js done "$ARGUMENTS"`

Task moved to `done.md`. Pick up the next task by priority from `todo.md`.

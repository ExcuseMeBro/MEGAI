---
description: Pause a task — move it back from inprogress.md to todo.md
argument-hint: <task text or index>
allowed-tools: Bash(node:*)
---

!`node ~/.claude/hooks/taskflow-move.js pause "$ARGUMENTS"`

Task moved back to `todo.md`, keeping its priority. Resume it later with `/ts`.

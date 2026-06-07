---
description: Add a task to the project's .todos/todo.md board
argument-hint: <task text>  (optional !! !!! !!!! priority)
allowed-tools: Bash(bash:*)
---

Append the task to the project's `.todos` board (created if missing):

!`bash ~/.claude/bin/taskflow-add.sh "$ARGUMENTS"`

The task is now on the board. Confirm briefly what was added. Do NOT start working on it now unless it is urgent (`!!!!`).

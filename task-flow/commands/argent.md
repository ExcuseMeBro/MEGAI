---
description: Run an explicit Argent app or device review
argument-hint: [target or scenario]
managed-by: megai
allowed-tools: Bash(argent:*)
---

The user explicitly invoked `/argent`, so Argent review is authorized for this turn only.

Use the `argent` skill. Review `$ARGUMENTS` or, when omitted, the current task's active app/device scenario. Run the narrowest relevant Argent interaction, make no code edits, report observed findings and blockers, then stop.

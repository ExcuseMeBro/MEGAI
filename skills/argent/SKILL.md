---
name: argent
description: Explicit-only Argent app/device review. Activate only when the user invokes /argent; never infer or auto-run it during implementation, review, verification, UI checks, or delivery.
managed-by: megai
---

# Argent explicit review

## Activation gate

Run this skill only when the current user message explicitly invokes `/argent`. A request such as "review", "test", "check UI", or "verify" without `/argent` is not permission to use Argent.

Never invoke Argent automatically from task-flow, OMP routing, UI verification, code review, focused tests, ship gates, or failure recovery.

## Execution

After `/argent`:

1. Use the supplied target/scenario; otherwise derive the current app/device target from the active task without broad discovery.
2. Inspect `argent tools` and `argent server status` only as needed.
3. Run the narrowest Argent review that exercises the requested scenario.
4. Do not edit code unless the user separately asks for a fix after seeing findings.
5. Stop after the review; never start a watcher or autonomous loop.

Return concise findings with the exercised target/scenario, observed evidence, and any blocker. Do not claim coverage beyond the interaction actually run.

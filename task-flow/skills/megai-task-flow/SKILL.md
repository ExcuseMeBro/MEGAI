---
name: megai-task-flow
description: Start tracked project changes and hand off verified work in Plane. Parent-only; questions and read-only investigation need no task.
managed-by: megai
---

# Plane-only task flow

Plane owns task identity, acceptance, execution notes and status. The parent loads this skill once at task start/resume; children inherit the `(project UUID, work item UUID)` pair and never mutate Plane or launch agents.

## Start boundary

1. Reuse the active identity for refinements. Otherwise resolve the Git root and consume every Plane project page; require exactly one exact Git-root folder-name match. A managed worktree inherits its parent's project identity. Zero/multiple matches require the user; never create a project implicitly.
2. Consume every workflow-state page. Require exactly one `In Progress` and one `In Review`, both `group=started`, before mutation. Failed/incomplete responses, missing states or ambiguity block edits.
3. Reuse a known work-item pair directly. Otherwise consume every project work-item page and compare the exact requested title. One match: reuse; multiple: ask. Zero matches after a successful complete lookup: automatically create exactly one item without asking for approval, using that exact title and the resolved `In Progress` state UUID. Failed or incomplete lookup is never zero matches. For a supplied historical Asana identity, match both `external_id=GID` and `external_source=asana-migration-v1`; zero/multiple matches block reconciliation, never create a replacement. Preserve historical source identity/markers until the Plane pair is confirmed.
4. Update the existing item to `In Progress` once, or create the missing item in that state. Inspect the returned state. Reconcile an uncertain write by lookup before retrying; never duplicate it. Retain the returned pair in session context. Acceptance belongs in that Plane item, not a second execution board.

Unavailable or unauthenticated Plane blocks project edits. Pure questions/read-only work need no mutation. Resume with the known pair; fetch only if its boundary state may disagree.

## Execute and hand off

- Inspect, implement, self-review, and verify observable acceptance with relevant tests. Security/data-integrity risks or consequential cross-module changes require independent review. Preserve accessibility, compatibility and error handling.
- Reuse the active pair throughout refinements. Keep only boundary writes: no routine stage sync, milestone comments, polling, second tracker or automatic queue draining.
- Complete the user's agreed branch delivery before handoff. Default worktree delivery uses `agent-worktree-lifecycle`; an explicitly requested persistent branch is pushed and retained without merging into other branches.
- At verified handoff, record concise evidence/remaining risks on the same item and move it to started `In Review`. Keep it incomplete; do not invent a completion boolean. Only the user may move it to `Done`.
- Main promotion requires separate explicit user approval. Stop after the requested task.

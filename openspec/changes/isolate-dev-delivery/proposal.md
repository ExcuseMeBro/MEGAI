## Why

Git edits on a shared `dev` checkout can interfere with other tasks, and leaving verified task commits in isolated branches requires a later manual handoff. Make isolated work and safe local `dev` delivery the agent's normal end-to-end flow.

Plane: MEGAI `59005e36-ecd4-46ed-bb42-f779858b20ce` / `27864243-8365-457d-b7e8-41b7ce81f863`; no historical source marker.

## What Changes

- Require a separate managed task worktree/workspace for every Git edit, regardless of task size; never edit source directly in `dev`.
- After verified acceptance and review, automatically reserve and fast-forward task commits into local `dev` with no additional user confirmation; check delivery and release the reservation.
- Automatically retire only idle, clean, task-owned workspaces and safely merged temporary branches after delivery. Retain and report anything active, dirty, uncertain or not proven merged.
- Keep main promotion, push, publication and force/destructive cleanup outside automatic delivery.

## Capabilities

### New Capabilities

- `isolated-dev-delivery`: Agent-managed task isolation, verified local dev integration and safe task-resource retirement.

### Modified Capabilities

None (no existing specs).

## Impact

`pi-defaults/AGENTS.md`, `pi-defaults/skills/pi-workflow/SKILL.md`, `skills/agent-worktree-lifecycle/SKILL.md`, and the installed Pi instruction copies after approved delivery. Existing Paseo, Plane, `megai queue` and Git operations are reused; no daemon, hook, force operation, new dependency, or unapproved push/main mutation.

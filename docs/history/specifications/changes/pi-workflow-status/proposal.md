## Why

`/mdev` step 1-3 requires a fetch-fresh, project-scoped inventory before it may
write anything, but the shipped CLI has no `status` subcommand: the launcher
`~/.local/bin/pi-workflow` (`python3 ~/.pi/agent/defaults/workflow.py`) rejects
`pi-workflow status` with `invalid choice` and exit code 2, so the SPMAPP `/mdev`
run blocked at its first mandatory command. The launcher, the installed
`~/.pi/agent/defaults/workflow.py`, and the canonical
`pi-defaults/workflow.py` all expose only `context`, `start`, `review`, `done`
and `verify-main`.

Historical source marker:
`/Users/bro/PROJECTS/SPMAPP/.pi/state/pi-workflow-status-repair.md`.
Linked Plane identity: project `59005e36-ecd4-46ed-bb42-f779858b20ce`, task
`1c67cabf-d7c7-4693-923f-0e23d43c4c34` (MEGAI-88). This refines that existing
task; it creates no new identity.

## What Changes

- Add a read-only `pi-workflow status [--cwd PATH] [--workspace WORKSPACE_ID]`
  subcommand returning a project-scoped JSON inventory.
- Inventory exactly the project's configured repositories and persistent
  branches, refreshed only from approved remotes, with remote-`dev` ancestry.
- Report dirty/untracked state, unfinished Git operations, and fail-closed
  busy/unknown ownership; unknown is never reported as safe.
- Observe scoped Paseo workspaces (exact HEAD, archive eligibility) through the
  documented `paseo project|workspace|agent ls --json` read commands.
- Emit advisory `pendingDelivery`, `cleanupEligible` and `blocked` fields.
- Preserve `context`, `start`, `review`, `done` and `verify-main` behavior.

## Capabilities

### New Capabilities
- `pi-workflow-status`: fetch-fresh, project-scoped, read-only repository and
  workspace inventory with fail-closed safety reporting.

### Modified Capabilities
None. The existing commands and Plane boundaries are unchanged.

## Impact

One function plus one argparse subparser in `pi-defaults/workflow.py`, one
regression test `tests/pi_workflow_status.py`, and documentation. `status` is
observation only: it never merges, pushes, archives, deletes, mutates Plane,
edits source/config/refs, or authorizes an integration-queue bypass. Its only
write side effect is the approved fetch, which may write Git objects and
`FETCH_HEAD`. Its `archiveEligible`/`cleanupEligible` output is advisory; actual
archive still requires the separate parent cleanup gate (owner plus
terminal/service release). Later installation of the updated file
into the runtime profile is a separate, approved, backup-and-drift-checked step;
no model, settings, daemon or profile restore is involved. No new dependency:
`subprocess` and stdlib `json`/`argparse` already present.

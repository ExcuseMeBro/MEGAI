## Why

Pi decision behavior is now local through Laya, but pending branch refinements and retained legacy artifacts leave `dev` and the installed profile inconsistent. Consolidating the applicable work and removing the retired stack gives the repository and local harness one clear runtime.

Plane project/work item: `59005e36-ecd4-46ed-bb42-f779858b20ce` / `03f8d6a8-710b-4485-9bd1-02c871a42b44`.

## What Changes

- **BREAKING**: make Laya the only decision tool and runtime represented by the tracked `dev` tree and active local Pi harness; no compatibility alias or hosted decision path remains.
- Integrate the pending Laya policy refinements first, then the independent workflow-status work; recognize installer-fix commits already patch-equivalent to `dev` instead of duplicating them.
- Remove every tracked legacy-only implementation, installer, prompt, test, benchmark, result, document, migration guard, name and reference from the final tree.
- Keep legacy-only branches unchanged and separate so their work remains available without entering `dev`.
- Back up active local Pi resources privately, install the Laya-only profile, and verify that only Laya-backed decision behavior loads. Existing private backups and session transcripts remain untouched.
- Deliver only to `dev`; promotion to `main` is a later, separately approved action after verified review.

## Capabilities

### New Capabilities

- `local-laya-decisions`: Laya-only typed decisions, source/install cleanliness, branch consolidation order, local profile behavior and delivery boundaries.

### Modified Capabilities

None; this repository has no existing main capability specs.

## Impact

Affected areas are the Laya extension and bridge, runtime/profile installers, model-policy wiring, workflow status command, focused Python/Node/shell tests, OpenSpec artifacts, documentation and the active `~/.pi/agent` profile. No new service, hosted credential, compatibility layer or dependency is added. The accepted task commit is integrated into `dev`; `main` remains unchanged until explicit approval.

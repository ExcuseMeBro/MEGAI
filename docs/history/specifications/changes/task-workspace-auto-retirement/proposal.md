## Why
MEGAI-162 (Plane project `59005e36-ecd4-46ed-bb42-f779858b20ce`, work item `18dbd5aa-97e1-4c9a-8cf7-178fd7e23d0a`) added guarded local-dev cleanup, but requires an already archived agent while the parent instruction defers child archival until *after* workspace cleanup. This circular ordering strands clean delivered work. `/mdev` must reconcile recoverable rows instead of treating its advisory status inventory as an irreversible verdict.

## What Changes
- Retire verified idle direct child agents as part of the pinned cleanup transaction, before retiring their worktree; preserve parent, foreign, active and unknown agents.
- In ordinary task delivery the retained parent runs the exact cleanup command after delivery and prior to In Review; `/mdev` reuses it per delivered candidate rather than reimplementing unsafe archival.
- Before acceptance, resolve task-owned dirty source as normal work and recapture evidence; preserve ignored/untracked data in verified private storage before workspace retirement. If owner or data cannot be proven, retain it and continue independently deliverable rows.

## Non-goals
No forced removal, reset/stash of foreign or user-owned work, remote branch deletion, main promotion, automatic push, daemon or bulk sweep. `codedb.snapshot` already dirty in the shared primary dev checkout is not owned by this task; `/mdev` may use its separately authorized isolated *remote dev* path, ordinary local-dev delivery must not rewrite that checkout.

## Affected paths
`pi-defaults/workflow.py`, `tests/pi_workflow_status.py`, `pi-defaults/AGENTS.md`, `pi-defaults/prompts/mdev.md`, `pi-defaults/skills/pi-workflow/SKILL.md`, `skills/agent-worktree-lifecycle/SKILL.md`, focused policy tests. Existing `pi-workflow-status` specs remain unchanged.

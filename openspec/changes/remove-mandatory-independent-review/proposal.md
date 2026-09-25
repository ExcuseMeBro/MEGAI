## Why

The user wants the independent-review step removed entirely from new Pi task workflows. Today guarded handoff and the acceptance gate cannot pass without a separate reviewer even after source-current tests and parent self-review.

Plane: project `59005e36-ecd4-46ed-bb42-f779858b20ce`, work item `2ec19057-8497-440f-92c7-bd4e6d2f57ce`. No historical source marker.

## What Changes

- **BREAKING for new acceptance contracts:** create a review-free contract schema with source-current checks and parent self-review; preserve historical schema-1/2 verification unchanged.
- Remove the separate independent-review step from Pi workflow instructions in every risk category, including guarded, delegated and security-sensitive flows; do not suggest an opt-in reviewer stage.
- Preserve focused tests, regression/runtime evidence, safety boundaries, approval requirements and Plane handoff.

## Capabilities

### New Capabilities

- `pi-review-free-acceptance`: New-task acceptance without any separate-review stage, with backwards compatibility for frozen historical contracts.

### Modified Capabilities

- None (there are no main specs in this project).

## Impact

`lib/acceptance_gate.py`, acceptance tests, `pi-skill/acceptance/`, `pi-skill/ADAPTIVE.md`, `pi-skill/delegation.md`, `pi-defaults/AGENTS.md`, task-flow source and focused installer/policy tests. No push, main promotion, installation or unrelated policy changes.

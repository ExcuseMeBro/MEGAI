## Why

Requirements currently live across chat and task summaries, so handoffs can lose acceptance details. Add one optional, durable spec layer without making small fixes pay for a second orchestrator.

Asana: 1218202555904869. This refines the existing orchestration task; it does not create another task identity.

## What Changes

- Add a pinned, optional OpenSpec installer and a single on-demand global Pi skill.
- Use OpenSpec for multi-module/risky changes; retain the normal fast path for small known-seam fixes.
- Keep Asana status, one `.todos` summary/link, and one detailed OpenSpec checklist.
- Require actual verification evidence and explicit user approval before archive; preserve In Review and separate main-promotion authority.
- Initialize only MEGAI, with repo-specific context and this real integration change.

## Capabilities

### New Capabilities
- `selective-spec-workflow`: bounded spec planning, child handoff, verification and safe installation for Pi.

### Modified Capabilities
None.

## Impact

New optional installer, Pi skill, shell tests, uninstall hook, README guidance, and MEGAI's `openspec/` artifacts. Dependency: @fission-ai/openspec 1.12.0 (Node >=20.19.0). No changes to model routing, thinking, authentication, default install pipeline, existing test gates or other repositories. No beta stores, automatic archive, new services, or duplicated OPSX skill bundles.

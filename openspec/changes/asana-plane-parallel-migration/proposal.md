## Why

Asana: 1218209651694005. The user requests a complete, non-destructive copy of their Asana projects and task data into Plane, including archived projects, while retaining both services during rollout. MEGAI also needs a secure, supported Plane MCP connection without disabling its existing Asana integration.

## What Changes

- Inventory every accessible Asana workspace/project, explicitly including archived projects and empty projects, and export source data privately outside Git before destination writes. Include completed and incomplete tasks, recursively discovered subtasks, descriptions, sections, memberships, comments/stories, attachments, dependencies, tags/custom fields, attribution and timestamps to the extent exposed by authorized source APIs.
- Implement or reuse a resumable migration path with stable source-to-destination identity mapping, pagination, rate-limit handling, uncertain-write reconciliation, and explicit unsupported/inaccessible-data reporting. Do not treat a partial export as complete.
- Preserve project privacy and source provenance. Never silently grant access, invite users, publish files, change original task completion, or collapse multi-project membership. Represent destination limitations explicitly and preserve the original data in the export.
- Verify destination content and relationships, attachment byte integrity, original completion/archive semantics, and retry idempotency against the source inventory. Report native imports separately from archive-only preservation and unresolved gaps.
- Add Plane MCP alongside Asana to MEGAI using the official server or supported local mode. Keep credentials outside repository files, process arguments, logs, fixtures, and prompts. Private local attachment upload must not depend on publishing files.
- Retain Asana as the task-flow status authority during the compatibility window. Keep existing linked GIDs, record Plane identities separately, and detect post-snapshot source/destination changes before applying a catch-up. Both services remain usable; no background two-way sync daemon or automatic conflict overwrite.

## Capabilities

### New Capabilities

- `asana-plane-migration`: Non-destructive inventory/export, resumable transfer, identity and privacy preservation, explicit data-fidelity gaps, verification and controlled catch-up.
- `parallel-plane-mcp`: Secure Plane MCP installation/configuration and task-flow coexistence with Asana, including safe failure and removal behavior.

### Modified Capabilities

None. Existing Asana completion authority, parent-only tracker writes, user-only Done, and separate main-promotion approval remain unchanged.

## Impact

Likely seams: `lib/wire_pi.sh`, relevant other supported client wiring, `bin/megai`, `task-flow/skills/megai-task-flow/SKILL.md`, focused `tests/mcp-wiring.sh` and `tests/pi-task-flow.sh` coverage, new narrowly scoped migration code/tests if existing supported tooling is insufficient, and `README.md`. OpenSpec/worktree guidance changes only where coexistence requires clarification; historical evidence and Asana links are not globally rewritten.

Private exports, credential files and migration ledgers live outside Git. This proposal contains no source customer/task contents or credentials. The linked task is mirrored in the primary checkout's ignored `.todos/inprogress.md`; implementation lives in the registered `feat/plane-migration` worktree.

## Preconditions and non-goals

- Plane authentication succeeded, but its target workspace is not yet identified. Request the workspace URL/slug; do not guess or create destination projects before that identity is confirmed.
- Confirm destination plan capabilities/storage and export API coverage before selecting the transfer mechanism. The currently connected Asana user exposes one workspace; both archived and active project listings were paginated to completion. Task/comment/attachment export is not yet complete.
- Existing private Asana projects must not become workspace-public. Member mapping requires verified identity and permission compatibility.
- Non-goals: deleting source data, disabling Asana, final authority cutover, automatic bidirectional synchronization, new member invitations, paid-plan purchases, claiming restored authorship/timestamps when the target API cannot preserve them, and main promotion.
- Rollback initially means stop transfers and disable only the new Plane integration; Asana remains untouched and usable. Any removal of destination data requires an explicit, mapping-scoped plan and separate authorization.

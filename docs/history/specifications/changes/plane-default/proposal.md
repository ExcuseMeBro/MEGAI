## Why

The user explicitly requests replacing Asana with Plane as MEGAI's default task tracker, including the local Pi and Codex clients. Plane is already authenticated and the existing projects and task identities exist; runtime policy still requires Asana.

Linked legacy Asana GID: 1218209651694005. Plane project/work item: 59005e36-ecd4-46ed-bb42-f779858b20ce / 385d6c9f-8b6f-461f-b6b8-9fc419bdc2f5. Parent completed both start boundaries. This is the authorized cutover refinement, not a new data import.

## What Changes

- Make Plane the sole default coordination authority in distributed task-flow, OpenSpec, delivery guidance and documentation.
- Provide reversible, credential-safe Pi and Codex Plane MCP setup; explicitly replace the local Asana connector, preserving unrelated configuration and private backups.
- Update managed local Pi/Codex policy and shared skills without changing model/provider settings or unrelated user instructions.
- Preserve existing source IDs as legacy metadata and resolve imported work items without duplication. New work uses Plane identity, exact project matching and paginated lookups.
- Keep In Progress and In Review in Plane's started group, with no agent-owned Done transition. No Asana fallback or routine dual sync after cutover.

## Capabilities

### New Capabilities
- `plane-default-tracker`: Plane-first task lifecycle and reversible Pi/Codex connector cutover.

### Modified Capabilities

None in the archived base spec tree.

## Impact

Existing Plane MCP implementation commits 80e39f1 and 74faf05 are reusable groundwork. Affected paths include task-flow/, skills/megai-openspec, skills/agent-worktree-lifecycle, lib/wire_pi.sh, Plane lifecycle/helpers, Codex wiring, bin/megai, README.md, openspec/config.yaml and focused shell tests. Parent applies reviewed assets under ~/.megai, ~/.pi/agent and ~/.codex with backups.

Non-goals: deleting remote Asana history, OAuth credentials or exported data; bulk task/status migration; completing the prior historical-detail/cover import; editing unrelated repositories; new daemons/dependencies; changing models; main promotion or OpenSpec archival. Existing historical proposal/verification records retain their truthful Asana references.

Acceptance: installer tests prove Pi and Codex Plane config, Asana retirement, repeat safety, malformed-input refusal, private credential references and unrelated-setting preservation; policy tests prove no active Asana dependency and safe legacy identity resolution; live read-only handshakes verify both client transports. Final task handoff remains In Review, incomplete. Rollback restores private backups and the previous verified configuration without remote data deletion.

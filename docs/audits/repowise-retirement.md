# RepoWise retirement

The requested removal was split into independently checked slices: local runtime removal, lifecycle retirement, and documentation/verification. Required gates are retained under the five-minute checkpoint rule.

## Result and preservation

- Removed MEGAI's installer, update/status/doctor/help references and background-index function/calls. The install pipeline has 16 steps; core preparation has five. Graphify's explicit opt-in and core memory/codedb/zvec behavior remain.
- Removed the locally registered `uv` tool `repowise` 0.44.0 and its three executables (`repowise`, `repowise-augment`, `repowise-rewrite`). Removed the verified MEGAI shim/helper and only its tool-state entry. No RepoWise init/serve process was found before removal.
- Retained `.repowise/` indexes and existing logs. All 33 files in the primary project's index matched their pre-removal hashes. No index deletion command was used.
- No RepoWise registration was found in the checked global Claude/Codex/Gemini/OpenCode/Pi MCP maps. Existing wiring cleanup remains deliberately: it removes only stale `megai-repowise` registrations and preserves user-owned entries. It must not be deleted just because its name refers to the retired tool.
- Updated managed Pi/OMP guidance without reinstalling other tools or changing credentials.

## Focused proof

`tests/repowise-integration.sh` uses the shared `tests/ui-craft-retirement.sh` sandbox to exercise real install/update/status/doctor/uninstall dispatch against forbidden CLIs and stale installers. Both independent tools and sample project data survive generic MEGAI uninstall. Explicit failing assertions are used rather than relying on Bash `set -e` for negated `grep` commands.

`tests/repowise-background.sh` checks actual default and specialist-opt-in preparation: neither starts RepoWise, while core indexing and opt-in graphify remain. Both retirement regressions fail against the preceding source and pass after removal. Related Ruff, Pi runtime and MCP wiring gates provide compatibility evidence.

## Recovery limits

Private receipt, state and installer backup: `~/.repowise-retired/20260907T153932Z/` (0700), outside MEGAI's uninstall scope. Do not publish it. The isolated package environment was removed, not archived; reinstall the recorded version with `uv tool install --python 3.11 repowise==0.44.0` if rollback is explicitly wanted. Reconcile later edits before restoring any owned shim/state entry; never overwrite whole shared state/configuration files. Retained indexes require no restoration. Reload existing agent sessions to discard cached guidance.

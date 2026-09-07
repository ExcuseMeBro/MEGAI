# Dembrandt retirement

Removed MEGAI's Dembrandt installer, install/update/status/doctor/help references and OMP recommendation. This removes one install step; the remaining numbering is contiguous. Existing compatibility cleanup for `megai-dembrandt` MCP registrations remains; it preserves user-owned entries.

## Local removal

The registered global npm package was `dembrandt` 0.28.0 under `~/.npm-global/lib/node_modules/`, owning the `dembrandt` and `dembrandt-mcp` executable links. Removed it with `npm uninstall -g --ignore-scripts --no-audit --no-fund dembrandt`, then removed the verified MEGAI helper and only its tool-state entry. No matching server was found (the process search matched only its own inspection shell). Both executable lookups are now absent.

Global Claude/Codex/Gemini/OpenCode/Pi MCP maps had no Dembrandt registrations. No shared configuration or design-output deletion was performed. Other top-level global npm package names/versions and shared Playwright browser-cache directory entries were unchanged. These checks do not claim byte-level verification of all package or cache contents.

## Verification and recovery

The shared `tests/ui-craft-retirement.sh` now checks all three retired tools. It executes actual install/update/status/doctor/uninstall dispatch with stale installers and forbidden CLI stubs, and verifies independent executables/sample project data survive generic MEGAI removal. The regression fails against preceding source and passes after retirement. Ruff's pipeline check and existing MCP/OMP compatibility gates cover retained behavior.

Private metadata, installer and state backup: `~/.dembrandt-retired/20260907T155158Z/` (0700), outside MEGAI's uninstall scope. The npm package runtime was not archived; explicitly reinstall `dembrandt@0.28.0` if rollback is wanted. Do not publish private state or restore it wholesale over later edits. Generated design outputs and shared browser caches need no restoration. Existing sessions may cache old recommendations until reloaded.

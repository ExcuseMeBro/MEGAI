# Argent retirement

Removed the Argent installer, managed skill/command sources, CLI recommendations and startup installation step. The pipeline has 13 contiguous steps. OMP no longer installs even a leftover Argent skill source. Task-flow no longer generates `/argent` or unconditionally deletes a user replacement during its own removal. Generic explicit-user authorization for external app/device review remains; normal code/testing gates are unchanged.

## Local removal

The installed npm package was `@swmansion/argent` 0.22.0, owning `argent` and `argent-simulator-server`. Backed up metadata, installer, state and the three observed regular owned artifacts (shared skill, Claude skill, Claude command) under `~/.argent-retired/20260907T161502Z/` (0700), outside MEGAI's uninstall scope. Used the inspected installer removal branch, archived managed sources, then removed the package with npm `--ignore-scripts --no-audit --no-fund`. Both executable lookups are absent; state differs only by removal of `.tools.argent`.

No Argent CLI/app/device review was invoked. Process inspection found only its own shell, not a matching Argent server. Checked global Claude/Codex/Gemini/OpenCode/Pi MCP maps contained no Argent entries. No SDK, browser-cache, device, simulator or report cleanup was performed. These are scoped-operation checks, not a byte-level audit of all application data.

## Compatibility and proof

`lib/retire_argent.sh` removes only the original known marked MEGAI copies in shared/Claude/Pi/OMP skill roots, OMP profiles and the Claude command path. It preserves unmarked files and linked file/skill-directory replacements. State transformation is prepared before deletion and requires exactly one JSON object. Empty input, null, arrays, multiple documents and malformed input fail before artifact changes. The same corrected input guard covers the related Numasec/OpenSpec retirement helpers. It never invokes or uninstalls an independent CLI. Retired MCP-key cleanup remains; user-owned entries stay intact.

`tests/argent-integration.sh` checks actual cleanup, repeated execution, foreign files/links, report and independent-CLI preservation, malformed state and actual status/doctor output. An ownership-marker bypass mutation is rejected. Pi task-flow tests seed a stale command source to simulate overlay upgrades and prove no command recreation or overwriting of user replacements, including on task-flow removal. OMP tests include a stale Argent source and prove it is not rewired. Shared retirement, Ruff, Pi runtime, MCP and orchestration gates cover the remaining system.

For rollback, reconcile later edits first. Managed sources/artifacts are privately archived; the npm runtime is not. Reinstall the recorded package version only when explicitly wanted, then restore selected owned artifacts/state fields rather than overwriting shared files. Existing sessions may retain cached skill descriptions until reloaded. Project outputs and shared SDKs require no restoration.

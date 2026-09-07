# OpenSpec retirement

Removed the optional OpenSpec installer and `megai-openspec` skill from MEGAI. Installation was already opt-in, so the normal pipeline remains at 15 steps. Superseded upstream CLI/prompt-policy tests are replaced by retirement preservation checks; existing `openspec/` specifications and historical evidence are not removed.

The former installer's owned-link removal behavior remains as `lib/retire_openspec.sh`. Generic MEGAI uninstall calls it to avoid leaving dangling Pi links on older installations. It checks each registered link target, preserves foreign links/directories, supports custom paths with spaces/newlines, removes only the OpenSpec state entry, and never invokes or installs the CLI. It can run after the skill source is already gone.

## Local removal

- Backed up package metadata, installer, state and owned-link targets under `~/.openspec-retired/20260907T155727Z/` (0700), outside MEGAI's uninstall scope.
- Used the inspected existing removal path to unlink the registered global Pi bridge. Archived the installed managed skill in the private backup and removed the installed installer.
- Removed `@fission-ai/openspec` 1.12.0 with `npm uninstall -g --ignore-scripts --no-audit --no-fund @fission-ai/openspec`; executable lookup is absent.
- All 21 specification files in the primary project's `openspec/` tree matched their pre-removal hashes. Shared state differs only by removal of `.tools.openspec`. Existing privacy settings were not reset.

## Proof and rollback

`bash tests/openspec-integration.sh` exercises actual cleanup with owned/custom/dangling links, foreign links and user directories, repeated cleanup, retained independent CLI/specifications and malformed state failing before unlink. A mutation removing the ownership check must fail this gate. Shared retirement and Pi/task-flow checks protect the remaining runtime; no live OpenSpec dependency is needed.

To undo removal, reconcile later edits first. The managed skill is archived; the npm runtime is not. Reinstall the recorded package version only if explicitly wanted, and restore only the desired owned link/state fields rather than replacing shared configuration. Project specifications need no restoration. Old sessions may retain the removed skill description until reloaded.

# Numasec retirement

Removed the Numasec installer, global handoff skill source, install/update/status/doctor recommendations and `megai security` launcher. The install pipeline now has 14 contiguous steps. Security, authorization and task-specific validation requirements are unchanged.

## Local removal and preservation

The global npm package was `numasec` 1.2.1. Metadata, installer, state and link targets were backed up under `~/.numasec-retired/20260907T160457Z/` (0700), outside MEGAI's uninstall scope. The three observed owned skill links (shared/Codex discovery, Claude and Codex-specific) were unlinked; the default Pi link was already absent. The installed managed skill was archived in that private backup.

Used the inspected existing removal path, then `npm uninstall -g --ignore-scripts --no-audit --no-fund numasec`. Removed the installed installer and its state entry, including the old uninstaller's null tombstone. CLI lookup is absent. Shared state was structurally identical except for removal of `.tools.numasec`. No report/project/configuration deletion or security-agent invocation was performed; private security-session data was not inspected.

## Compatibility and verification

`lib/retire_numasec.sh` keeps only legacy owned-link cleanup for older installations and generic MEGAI uninstall. It checks exact targets in the original known skill roots and the selected Pi directory, including dangling links. Foreign links and user directories survive. State transformation is prepared before unlinking, so malformed state fails before changes. Cleanup does not install, launch or remove independently installed CLIs. Historical custom Pi destinations were not registered by the old installer; a non-default installation must supply its original `PI_CODING_AGENT_DIR` when cleaning up.

`tests/numasec-integration.sh` checks actual cleanup, idempotence, a foreign final Pi link, user skill/report preservation, invalid state, actual status/doctor output and rejection of the old security command without executing its forbidden CLI stub. An ownership-check removal mutation is rejected. Shared retirement, Ruff pipeline and relevant runtime/wiring gates protect retained behavior.

The npm runtime was not archived. If rollback is explicitly wanted, reconcile later edits, reinstall `numasec@1.2.1` and restore only desired owned links/state fields. Do not publish private backups or overwrite shared state wholesale. Existing sessions may cache the removed skill until reloaded.

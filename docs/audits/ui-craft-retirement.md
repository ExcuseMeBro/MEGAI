# ui-craft retirement

ui-craft is no longer a MEGAI dependency. Its installer and active install/update/status/doctor/uninstall dispatch are removed. ui-craft removal reduced the pipeline by one step. Ruff and unrelated UX/UI skills remain. Existing `.ui-craft/` design notes stay retained and gitignored.

## Local removal and preservation

The user explicitly requested removal. The installed Homebrew cask was `educlopez/tap/ui-craft` 1.0.3. Its binary was privately backed up, then removed with Homebrew without `--zap` or dependency autoremove. The installed MEGAI helper was backed up and removed; only `.tools["ui-craft"]` was deleted from MEGAI state. Pi settings, instructions and MCP config were not changed by this task.

**Upstream defect:** ui-craft 1.0.3's `uninstall --dry-run --yes --json` ignores dry-run and JSON flags and performs real removal. This occurred during the requested uninstall investigation; it is not represented as a read-only preview. The [v1.0.3 command source](https://github.com/educlopez/ui-craft/blob/v1.0.3/cli/cmd/uninstall.go) lacks a dry-run guard. Do not rerun that command expecting a preview.

The uninstaller created snapshot `~/.ui-craft-backups/20260907T151647-357678000/` before removing its generated skill directories, aliases, review agents and MCP registrations. It left project design memory intact. Parent verification against that snapshot found:

- 120 retained snapshotted files byte-identical.
- All 188 removed snapshotted skill/agent files byte-match blobs in the official v1.0.3 source tree; no unmatched removed skill/agent file.
- Codex TOML and Gemini/OpenCode JSON preserve every field except their ui-craft MCP entry.
- Codex AGENTS preserves nonempty content outside the ui-craft managed block; one extra blank line was normalized.

Limits: the upstream snapshot omits command directories, so their pre-removal customizations cannot be independently verified from it. Upstream source removal is scoped to embedded command filenames; unrelated directories are retained. Tar modes are normalized to 0640 by upstream backup code and must not be mistaken for original host permissions. No blanket restore or chmod was performed.

## Verification and rollback

`bash tests/ui-craft-retirement.sh` executes actual installer/update/status/doctor/uninstall dispatch in a sandbox containing both a stale installer and a forbidden ui-craft stub. It fails against the prior source and passes after retirement, preserving an independent CLI and sample design notes during generic MEGAI uninstall. `bash tests/ruff-integration.sh` verifies the renumbered pipeline and retained non-mutating Ruff behavior. Bash syntax/diff checks and local command/state/source-parity checks complete the focused proof.

Durable private backup: `~/.ui-craft-retired/20260907T151647-357678000/`, including the original binary, managed files/state and a copy of the upstream snapshot. This directory and the original upstream snapshot remain outside MEGAI's uninstall scope. The initial copy at `~/.megai/backups/ui-craft-retirement-9f3v_j6n/` is not durable against `megai uninstall`, which deletes its home tree; use the independent copy for recovery. Do not publish these archives; they contain private harness configuration.

To undo removal, first reconcile subsequent edits. Restore only the desired ui-craft-owned assets or reinstall the independently verified version; restore MCP keys/managed blocks surgically. Do not use whole-harness rollback over newer user configuration. Design notes and unrelated tools do not need restoration. Existing sessions may retain cached resources until reloaded/restarted.

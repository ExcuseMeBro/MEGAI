# Pi-only slim verification

## Scope

The persistent `slim` branch now supports Pi only. The ten task-appropriate defaults, full Caveman core, raw acceptance evidence, unchanged model/thinking choices and no-prewarm startup contract remain intact.

Supported lifecycle: install/update, `megai pi`, Pi/path wiring, doctor, Pi Plane setup/status/remove/restore, owned Pi uninstall and the existing shared CLI utilities. `cc`, `codex`, `omp`, non-Pi wire targets, and Plane `--client all|codex` fail before mutation. Existing non-Pi policies are preserved, not automatically uninstalled. Historical non-Pi source/recovery artifacts remain unwired.

Pi skills now live under `PI_CODING_AGENT_DIR/skills`. Pi-only kit source trees are under `~/.megai/pi-kits`; exact legacy Pi symlinks migrate to those trees without modifying the old shared source trees or other harness links. Pi defaults exclude automatic `~/.agents/skills/**` discovery, avoiding duplicate legacy copies; existing explicit resource selections remain after that default. Uninstall removes only the owned exclusion and Pi assets, never shared skills. Removing the exclusion restores Pi's ordinary shared discovery, including any deliberately retained legacy shared copies.

## Verification

- Two new boundary/source-isolation tests fail against all-harness baseline `4715f8f`.
- `tests/slim-distribution.sh`: 31 tests pass. New coverage includes malformed non-Pi config preservation, rejected clients, private source migration, kit symlink ancestors, Pi-only Plane lifecycle and full Plane config ancestry refusal.
- `tests/plane-mcp.sh`: original credential privacy, endpoint/envelope binding, ownership/customization, secure backup, restore/idempotence, missing/unsafe credentials and symlink protections pass with Pi-only lifecycle expectations.
- UX integration, Pi performance contracts, Ruff integration, orchestration policy, changed-Python Ruff, shell syntax and diff checks pass.
- Canonical local source installer and main pipeline pass. Pi doctor and Plane configured/credential checks pass.
- Actual Pi resource loader: 58 skills, one Caveman from `~/.pi/agent/skills/caveman/SKILL.md`, one MCP adapter, zero diagnostics and no model requests.
- Immediately after the canonical local rollout, all 1,064 tracked non-Pi/shared/config/auth/index files and links matched the preflight inventory. Pi settings changed only by adding the intended shared-discovery exclusion; other values and existing selections were preserved.
- A later final inventory detected concurrent changes in Claude settings, Codex hooks and Codex config. New Tempest hook registrations were visible; these files were outside this migration's mutation targets and were left untouched. The other 1,061 inventory entries still matched. Do not interpret the earlier check as a blanket final byte-identity claim for concurrently active harnesses.
- Independent security/data-integrity review found a missing Plane ancestor check. It now reuses the common fail-closed path guard before reading/staging config; both `.pi` and agent-root symlink cases are tested for setup/status/remove/restore. Focused independent re-review passed.

No task-speed, model-token or code-quality improvement is inferred from this scope reduction. Behavioral tests and task acceptance remain authoritative.

## Recovery and delivery

Source and wiring changes retain private ownership/recovery manifests under `~/.megai/backups`. Old shared kit directories and other harness configuration stay intact. Reconcile subsequent local edits before restoring only manifest-listed targets; do not sweep old shared registrations. Restart Pi to adopt the new resource layout. Push only `slim`; retain its clean managed worktree and leave `dev`/`main` unchanged.

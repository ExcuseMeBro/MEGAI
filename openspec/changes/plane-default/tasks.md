## 1. Plane policy and OpenSpec contract

- [x] 1.1 Update `openspec/config.yaml`, `skills/megai-openspec/SKILL.md`, task-flow, OMP, lifecycle, and README guidance to use paginated Plane project/work-item identity, started `In Progress`/`In Review`, and historical `external_source=asana-migration-v1`; verify with `bash tests/openspec-policy.sh` and focused policy searches.
- [x] 1.2 Add the `plane-default-tracker` requirements, design, and bounded migration/rollback plan; verify with `OPENSPEC_TELEMETRY=0 openspec validate plane-default --type change --strict --no-interactive`.

## 2. Credential-safe connector cutover

- [x] 2.1 Extend Plane lifecycle setup with explicit client selection, additive default, replacement flag, private backups, restore, and CODEX_HOME/PI_CODING_AGENT_DIR support; verify with `bash tests/plane-mcp.sh` and shell syntax checks.
- [x] 2.2 Add the pinned mcp-remote Codex wrapper using private token-file loading and environment-placeholder headers; verify no synthetic token appears in config, argv, stdout, or stderr and run Python compilation/Ruff checks when available.
- [x] 2.3 Preserve normal MEGAI wiring and unrelated Codex/Pi MCP settings while retaining managed Plane entries; verify with `bash tests/mcp-wiring.sh` and repeat/removal checks.

## 3. Managed local policy installer

- [x] 3.1 Source concise Pi/Codex policy snippets and replace only the managed Pi section or exact Codex workflow markers, refusing ambiguous/symlinked targets; verify with `bash tests/pi-task-flow.sh` and policy-preservation regressions.
- [x] 3.2 Add regression coverage for Codex Plane wiring, Asana removal only under explicit replacement, unrelated-setting preservation, malformed input refusal, and repeat safety; verify with the focused shell tests.

## 4. Handoff evidence

- [ ] 4.1 Run the complete affected focused shell set (`plane-mcp`, `pi-task-flow`, `mcp-wiring`, OpenSpec policy/contract), strict OpenSpec validation, shell syntax, and non-mutating Python Ruff; record command results and remaining live-handshake/local-apply steps in `verification.md`.
- [x] 4.2 Self-review the diff, commit this worktree slice, and provide the parent exact isolated local-apply commands; verify `git status --short` is clean after commit.

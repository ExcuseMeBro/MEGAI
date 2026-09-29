# Verification

Linked legacy source: `1218209651694005`. Plane identity pair remains `59005e36-ecd4-46ed-bb42-f779858b20ce / 385d6c9f-8b6f-461f-b6b8-9fc419bdc2f5`. Parent owns real home-config application and live read-only handshakes.

| Requirement | Evidence | Result |
| --- | --- | --- |
| Plane policy and identity contract | `bash tests/openspec-policy.sh`; `OPENSPEC_TELEMETRY=0 openspec validate plane-default --type change --strict --no-interactive --json` | PASS |
| Pi/Codex policy preservation | `bash tests/pi-task-flow.sh` | PASS; exact Codex legacy marker replacement and Pi delegation preservation covered |
| Credential-safe Pi/Codex wiring | `bash tests/plane-mcp.sh`; `bash tests/plane-codex-config.sh` | PASS; isolated HOME, CODEX_HOME, PI_CODING_AGENT_DIR, staged replacement, target-bound restore, malformed/symlink input, repeat safety, quoted TOML ownership, dotted-key refusal, and token-safe absolute bridge argv covered |
| Existing MCP preservation | `bash tests/mcp-wiring.sh` | PASS |
| OpenSpec CLI contract | `bash tests/openspec-contract.sh`; `bash tests/openspec-integration.sh` | PASS |
| Static validation | `bash -n bin/megai lib/*.sh`; Python compilation; non-mutating Ruff on changed Python files; `git diff --check` | PASS |

## Parent correction evidence

- `bash tests/plane-cutover-regressions.sh`: PASS with real system Node, modified/deleted/added runtime chunk rejection, external symlink rejection, byte-identical repeated Codex policy installation with stable backup count, and all-client uninstall failure preserving assets.
- Parent reran Plane MCP/Codex config, Pi task-flow, MCP wiring and all three OpenSpec focused suites: PASS; strict change validation, non-mutating Ruff and shell syntax: PASS.
- Policy scenario review: ordinary clean exact-title zero matches requires approval then creates once in the resolved start state; one reuses, multiple stops; incomplete lookup and unresolved legacy IDs cannot create. State lookup requires unique exact In Progress/In Review UUIDs with started groups, and stops on missing/duplicate/wrong-group responses. These instructions and static guards do not prove future model compliance.

## Local cutover and final review

- Independent Sol review PASS on parent correction `0f053c7`: all accepted findings resolved; independent runtime-integrity, Plane lifecycle and Pi task-flow tests passed.
- Applied the reviewed MEGAI runtime assets; installed the pinned bridge explicitly without token material, then ran `megai wire pi`, `megai wire codex`, `megai plane setup --workspace brodev --token-file <private-file> --client all --replace-asana`, and `megai plane status --client all`: PASS. Preserved the installed CLI executable bit, as the repository's installer does.
- Fresh read-only handshakes using the actual configured Pi HTTP header command and Codex stdio executable each returned 30 tools, 21 active projects, and the unique expected MEGAI project. Codex bridge stderr: 0 bytes. `codex mcp get plane --json` confirms the native client entry is enabled.
- Parsed before/after equality proves unrelated Pi MCP entries, all unrelated Codex settings, Pi model/settings and non-task-flow global instructions were preserved. Asana connector absent in both clients; active policies and shared lifecycle skill are Plane-first. No remote records were deleted.
- Private rollback/evidence directory: `~/.megai/backups/plane-default-20260907-134833/`, including `live-verification.json`, original client policies/configs and installed runtime asset backups. `megai plane restore --client all` restores connectors only; restore the explicitly backed-up policy/runtime files separately if reverting the whole rollout.
- Existing Pi sessions require `/reload`; restart Codex sessions to consume the new instructions and MCP configuration. New on-disk defaults do not rewrite already-loaded prompts.
- User explicitly approved main promotion in this conversation. Git delivery receipts are recorded at the linked task handoff after verified delivery. OpenSpec archival and cleanup of unrelated historical migration work remain unapproved.

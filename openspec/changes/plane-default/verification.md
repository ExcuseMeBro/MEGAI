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

## Remaining parent-owned evidence

- Apply the explicit cutover only in an isolated/approved local environment after review:
  `megai wire pi && megai wire codex && megai plane bridge install && megai plane setup --workspace SLUG --token-file PRIVATE_TOKEN --client all --replace-asana`.
- Run `megai plane status --client all`, then perform read-only Pi and Codex MCP handshakes with the real private credential. Do not print or copy token material.
- If local connector verification fails, use `megai plane restore --client all`; this restores connector backups only, leaves policy/`AGENTS.md` backups untouched, and does not delete remote records.

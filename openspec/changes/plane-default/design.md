## Context

See `proposal.md` for motivation. Existing `lib/plane_mcp.sh` and `lib/plane_mcp_headers.py` already provide a Pi HTTPS request-header path with owner-only token validation. Codex 0.149.1 currently has a pinned `mcp-remote@0.1.43` stdio bridge but no Plane entry. The installed mcp-remote contract accepts `${ENV_VAR}` substitutions inside `--header` values; it logs header names, not values, and rejects non-HTTPS URLs unless explicitly allowed.

## Goals / Non-Goals

**Goals:**

- Make Plane identity and boundary semantics the active task-flow contract.
- Add a Codex bridge that reads a private token file in a short-lived wrapper environment and passes only an environment placeholder in argv.
- Make replacement explicit, additive setup the default, and rollback local/private.
- Keep user-owned settings and policy text intact outside managed seams.

**Non-Goals:**

- Remote migration, deletion, or bulk status changes.
- OAuth or credential export.
- New daemons, npm dependencies, TLS exceptions, model changes, or automatic Done transitions.
- Rewriting historical OpenSpec records whose Asana references are factual.

## Decisions

1. **Reuse the existing Pi helper.** Pi continues to use `requestHeadersCommand` with exact URL and envelope validation. This avoids putting a token in JSON or spawning a long-lived secret-bearing process.
2. **Use a pinned Codex wrapper around existing mcp-remote.** `lib/plane_mcp_remote.py` validates the same token file, sets `MEGAI_PLANE_AUTH` only in the child environment, and executes the already-pinned `mcp-remote@0.1.43` with `Authorization:${MEGAI_PLANE_AUTH}` and the workspace header. The token is not in config, argv, or logs; no `--allow-http` or TLS override is used. A direct token-in-argv or config `env` value was rejected because process/config inspection would expose the credential.
3. **Keep independent managed seams.** Pi JSON is updated with jq and a private atomic backup. Codex Plane TOML is stored in its own marker block, separate from the existing MEGAI marker, so routine `wire codex` does not delete the Plane entry. TOML is validated before explicit Plane replacement; ambiguous user-owned `plane` entries are refused.
4. **Use explicit replacement.** `megai plane setup` remains additive by default. `--replace-asana` removes only named legacy MCP entries after backups. `megai plane restore` restores the latest private client backup; remote records are untouched.
5. **Install policy through exact boundaries.** Pi replaces the managed `## MEGAI task flow` section up to the next level-two heading, preserving `## Paseo-visible delegation`. Codex replaces either the exact legacy `asana-workflow` markers or the new `plane-workflow` markers. Duplicate/unpaired markers and symlinks fail closed.
6. **Represent identity as a pair.** Policy names project UUID and work-item UUID together, uses exact project matching over paginated lists, and requires the actual `external_source=asana-migration-v1` alongside `external_id` for imported work. No unresolved candidate may cause creation.

## Risks / Trade-offs

- [Risk] Codex's mcp-remote process environment can be inspected by a same-user process while connected → Mitigation: read the owner-only file at launch, never log it or place it in config/argv, and keep the bridge lifetime under Codex's stdio process.
- [Risk] TOML cannot be safely round-tripped without a parser while preserving comments → Mitigation: validate with Python `tomllib`, edit only exact managed/legacy table ranges, preserve all other text, and back up before writes.
- [Risk] Plane API filtering may differ by deployment → Mitigation: require pagination and local matching fallback, with duplicate creation forbidden until identity resolves.
- [Risk] A stale policy shape could be user-owned → Mitigation: exact marker/heading counts, symlink refusal, private backups, and no broad file rewrite.

## Migration Plan

1. Ship policy/spec and focused regression coverage.
2. Parent applies `megai wire pi` and `megai wire codex` in isolated temporary-home tests first.
3. Parent performs the explicit local cutover only after review:
   `megai plane setup --workspace SLUG --token-file PRIVATE_TOKEN --client all --replace-asana`.
4. Parent validates `megai plane status --client all` and runs read-only MCP handshakes for Pi and Codex.
5. Roll back with `megai plane restore --client all` if local verification fails; do not delete remote history.

## Open Questions

None. Live workspace slug, credential path, and parent-owned home-config application remain explicit local inputs.

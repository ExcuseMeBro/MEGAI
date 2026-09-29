## Context

Ix's installer writes shared Codex hooks/MCP and Claude plugin settings in addition to its own runtime. The global Codex hooks also contain Paseo and Muxy commands. See proposal.md for scope and the user-approved free stack.

## Goals / Non-Goals

Retire supported Ix paths with recoverable local changes. Do not install CodeDB Pro, rewrite existing codedb/zvec wiring, delete graph data, or clean arbitrary repositories.

## Decisions

- Delete the old installer and safety patch rather than maintain unused active integration. Preserve historical records.
- Supply an explicit Python retirement helper (existing runtime dependency), not an automatic destructive installer migration. Preview by default; apply removes exact legacy hook commands/registrations and MEGAI leftovers, backing up originals. Parse all candidate configuration before the first write. Match hook commands exactly, not substrings such as `ix` that occur in unrelated content.
- Shared JSON updates preserve unrelated values; TOML uses parsed ownership and section-level removal, preserving unrelated text. Atomic replacement and restrictive backup permissions protect partial writes and credentials.
- Stop/remove the current host backend by verified container identity separately; archive its runtime and plugin assets. Keep Docker volumes. The helper does not manage Docker or arbitrary host installations.

## Risks / Trade-offs

- Custom Ix hooks may survive exact matching → report residual/custom references for manual review rather than broad-delete them.
- Existing installations retain external runtime files until explicit retirement → document the upgrade steps instead of mutating external services on every install.
- Multi-file writes are not a transaction → preflight all inputs, back up before writes, atomic per-file replacement, idempotent retries and explicit failure.

## Migration Plan

Verify sandbox removal and preserved search wiring; independently review shared-config safety; deploy changed MEGAI files and run the explicit helper; retire only verified local Ix resources. Roll back via the recorded backups and prior Git commit. Main promotion remains separately approved.

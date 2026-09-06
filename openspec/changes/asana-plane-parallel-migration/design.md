## Context

See proposal.md. The user confirmed Plane Cloud workspace `brodev`. Read-only API checks resolved it to one workspace with an existing project and confirmed the migration user is an administrator; the existing project is not owned by this migration. The connected Asana user has one source workspace. Its project listings contain 17 active and 38 archived projects and 1,252 summed project task memberships, not necessarily unique tasks or recursive subtasks.

## Goals / Non-Goals

**Goals:** Preserve accessible source data and privacy; distinguish native destination fidelity from archive-only preservation; keep all operations resumable and reviewable; add Plane without disabling Asana.

**Non-goals:** Final cutover, deleting source or existing destination data, perpetual bidirectional sync, public attachment staging, silent member invitations, paid upgrades, and retroactively fabricating source authorship or timestamps.

## Decisions

1. Export through the existing authorized Asana MCP connection when its read tools provide complete pagination. Reuse the adapter's documented URL-bound OAuth helper in a local Node process; never scrape keychain internals or persist bearer credentials in exports. A read-only allowlist prevents this exporter from mutating Asana. If a data category lacks complete API coverage, report and block the full-migration claim instead of treating a truncated result as complete. Direct Asana PAT/export remains an explicit fallback requiring authorization if existing MCP coverage is insufficient.
2. Store export JSON, original attachment bytes, checksums and the migration ledger in a private external directory. Use restrictive permissions, atomic replacement, a single-run lock and durable request receipts. Keep only synthetic fixtures and source code in Git. Raw record contents and URLs are not printed to ordinary command output.
3. Destination writes use Plane REST for deterministic bulk transfer and binary uploads; the official MCP remains the everyday agent interface. Fix the destination API origin and workspace. Never send tracker credentials to attachment hosts. Validate attachment destinations/redirects to reject local/private networks and stage bytes privately, not through public URLs.
4. Default imported projects to private. Map source identities explicitly and preserve unsupported membership/permission metadata without inviting or granting new users access. Preserve original state/section data and a source link; archived source projects are not silently represented as active or tasks marked Done just because the project was archived.
5. Native records carry deterministic source provenance, backed by an external identity ledger. Reconcile uncertain POST outcomes before retrying. Existing destination projects and hand edits are not adopted or overwritten by name alone. Multiple source memberships and cross-project relationships need explicit representations and verification.
6. Source snapshot time and content hashes support controlled catch-up: detect changes rather than treating a long-running export as an atomic snapshot. Both trackers stay available; Asana remains authoritative for MEGAI's task-flow. No daemon is introduced.
7. Add credential-reference-based MCP configuration using existing MEGAI wiring patterns and backups. Preserve all Asana and unrelated user-owned config. Use synthetic HOME/config fixtures for setup, upgrade, removal and missing-credential tests. Live setup is parent-owned after code review.

## Risks / Trade-offs

- Hosted APIs can limit history, member identity, original timestamps and paid-only properties → preserve originals in exports and explicit destination provenance; record fidelity gaps and never claim native parity without readback.
- Tool success can hide pagination or nested errors → validate each response shape, completion marker and count; retain failures for resumable retry.
- Migrating while Asana remains editable creates drift → re-enumerate and compare modified timestamps before declaring completion; flag destination edits during catch-up.
- Attachment retrieval may need signed URLs or inaccessible external providers → record per-file failures and byte checksums; no credential forwarding or public hosting workaround.
- Parallel writers can duplicate records → one destination writer, durable pending receipts, identity-based reconciliation and a lock.

## Migration Plan

Complete private source export and coverage report, validate mappings on synthetic tests, independently review security/data-integrity behavior, import a bounded real project with its original provenance, read it back, then expand to the full inventory. Verify every imported object category and checksum, perform a controlled final drift check, and report remaining gaps. Integrate and verify Plane MCP alongside Asana. Rollback stops transfer and restores only owned configuration from backup; source remains available. Destination cleanup is separately authorized and ledger-scoped.

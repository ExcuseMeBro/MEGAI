## 1. Source preservation and migration contract

- [x] 1.1 Confirm source and destination identities without guessing; verify authorized source workspace and Plane `brodev` project/member API reads, retain private discovery metadata.
- [ ] 1.2 Implement read-only paginated source export and recursive task discovery; verify synthetic pagination/error/duplicate cases and a private live coverage report (Complete source accounting).
- [ ] 1.3 Preserve original comments/history, metadata and attachment bytes; verify per-category completion and byte checksums, report inaccessible or unsupported data (Secure private preservation).

## 2. Destination transfer

- [ ] 2.1 Implement source identity mappings, private projects, task/state/subtask/link/comment/attachment representation and explicit fidelity metadata; verify synthetic transformations and privacy checks (Stable resumable identity).
- [ ] 2.2 Implement locking, atomic receipts, ambiguous-write reconciliation and safe retries; verify failure-injection tests and no blind POST retry (Stable resumable identity).
- [ ] 2.3 Obtain fresh independent security/data-integrity review before bulk writes; resolve critical findings and rerun affected tests.
- [ ] 2.4 Import and read back a bounded source project, then transfer the complete inventory; verify counts/content/relationships/checksums including archives and record native versus archive-only coverage (Observable data fidelity).
- [ ] 2.5 Check post-snapshot source drift and destination edits; verify controlled catch-up or report conflicts without overwriting user data (Parallel safety).

## 3. MEGAI Plane integration

- [ ] 3.1 Add secure credential-reference Plane MCP setup and diagnostics alongside Asana; verify synthetic HOME/config tests for missing credentials, existing config, repeat setup and scoped removal (Additive secure configuration).
- [ ] 3.2 Document coexistence and preserve Asana authority/GID linkage and user-only Done; verify task-flow regression tests (Safe lifecycle and task-flow coexistence).
- [ ] 3.3 Independently review auth/configuration changes and perform parent-owned live Plane MCP setup; verify discovery and read-only calls with Asana still working, plus safe local attachment handling.

## 4. Verified delivery

- [ ] 4.1 Run strict OpenSpec validation and focused integration tests; record requirement-to-evidence mapping, fidelity gaps and recovery paths in verification.md.
- [ ] 4.2 Deliver verified work through the existing dev lifecycle and retain Asana In Review/completed=false only after requested migration acceptance is proven; report source/destination coverage and ask separately before main promotion.

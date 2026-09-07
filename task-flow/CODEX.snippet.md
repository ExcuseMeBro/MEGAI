<!-- plane-workflow:begin -->
# Plane task flow
- Plane is the sole coordination authority for tracked work; use the Plane API/MCP project list with pagination and exact Git-root project matching. `.todos` is the local execution mirror.
- At task start, reuse the linked `(project UUID, work item UUID)` pair. Resolve imported work by `external_id` plus `external_source=asana-migration-v1`; paginate when filtering is unavailable. Keep the legacy source marker as historical metadata and never create a duplicate while identity is unresolved.
- Tracked/high-risk work uses one Plane start boundary in the started group. `In Progress` and `In Review` are started states; do not infer or write a completed boolean. The agent hands off in `In Review`; only the user may move the work item to `Done`.
- Keep the bounded loop: inspect, implement, self-review, focused test, then stop. Do not mirror routine stages, comments, or dual-sync to another tracker.
- The local Plane connector is credential-safe: keep tokens in owner-readable files, use TLS-only MCP transports, preserve unrelated settings, and keep private backups for rollback.
<!-- plane-workflow:end -->

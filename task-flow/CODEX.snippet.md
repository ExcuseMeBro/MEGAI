<!-- plane-workflow:begin -->
# Plane task flow
- Plane is the sole coordination authority for tracked work. Consume every paginated project and project-work-item page; require exactly one exact Git-root project and one exact item before mutation.
- Reuse the linked `(project UUID, work item UUID)` pair. Imported work requires `external_id` plus `external_source=asana-migration-v1`; preserve the original `<!-- asana:GID -->` marker until the pair is confirmed and never create a duplicate while identity is unresolved.
- The parent performs one started `In Progress` boundary before edits. An unavailable, incomplete, or ambiguous Plane lookup blocks changes; do not fall back to local bookkeeping.
- Run inspect → implement → self-review → focused verification. Hand off at started `In Review` with the item incomplete; only the user moves it to `Done`.
- Do not add routine milestone comments, poll for progress, or mirror stages into another tracker. Main promotion requires separate explicit user approval.
<!-- plane-workflow:end -->

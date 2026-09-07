<!-- megai:task-flow:begin -->
# MEGAI Plane workflow
- Plane is the only tracker for active MEGAI work. The parent resolves exactly one Git-root project and work item by consuming every paginated page before mutation.
- Reuse the linked `(project UUID, work item UUID)` pair. Imported work requires `external_id` plus `external_source=asana-migration-v1`; preserve the original `<!-- asana:GID -->` marker until the pair is confirmed.
- The parent performs the started `In Progress` boundary before edits. Plane unavailable, incomplete, or ambiguous blocks the change; do not use a local tracker fallback.
- Execute inspect → implement → self-review → focused verification, then hand off at started `In Review`. Only the user moves the item to `Done`.
- Keep boundaries quiet: no routine milestone comments, polling, or mirror trackers. Main promotion requires explicit user approval.
<!-- megai:task-flow:end -->

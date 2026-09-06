# Asana snapshot to Plane importer

`lib/asana_plane_import.py` is a standalone, resumable importer. It reads only the
private snapshot produced by the Asana exporter; the snapshot and destination
ledger must be outside Git and mode `0700`. It never calls Asana.

## Safety contract

- The source workspace GID and destination workspace slug are mandatory. The
  source manifest must say `export_complete: true`; incomplete exports are
  blocked.
- `plan` is local-only. `apply` is the only command that writes Plane. `--project`
  is the bounded pilot; `--all` also creates a separate private My Tasks project
  for unprojected records.
- Plane is fixed to `https://api.plane.so`. Credentials are read from a regular,
  current-user-owned `0600` token file, never from arguments or logs.
- Projects are created with a nonsensitive placeholder and migration identity,
  then read back. The importer requires `network == 0` before patching the source
  title/description. If Plane ignores the privacy setting, the migration stops
  before source data is inserted.
- The atomic `destination-ledger.json`, lock, and pending receipts reconcile
  `external_source`/`external_id` before any retry. POST failures are never
  blindly retried. Existing non-migration records are not adopted by name.
- Parent tasks are created before children. Completed tasks use the completed
  semantic state; an incomplete “In Review” task remains in the started group.
  Archived projects are archived only after tasks, comments, metadata bundles,
  and uploads, using the archive endpoint (never DELETE).
- Source task/stories/attachment metadata is retained in a per-task
  `migration-record.json` attachment. Signed download URLs, bearer values and
  credentials are removed from that user-facing bundle. Source binary receipts
  retain byte count and SHA-256 evidence.
- Multiple project memberships are rejected instead of being silently collapsed.
  Unmatched assignees are reported and no invitations are sent. Unsupported
  history/custom fields remain in the metadata bundle and fidelity report.

## Parent invocation

Use the parent-owned private export and a pre-approved token file. Do not run
`apply` against a live destination until independent review is complete.

```bash
python3 lib/asana_plane_import.py plan \
  --source PRIVATE_ROOT \
  --source-workspace-gid SOURCE_WORKSPACE_GID \
  --workspace-slug DESTINATION_SLUG \
  --project SOURCE_PROJECT_GID

python3 lib/asana_plane_import.py apply \
  --source PRIVATE_ROOT \
  --source-workspace-gid SOURCE_WORKSPACE_GID \
  --workspace-slug DESTINATION_SLUG \
  --token-file /private/path/plane-token \
  --project SOURCE_PROJECT_GID
```

For the reviewed bulk operation, replace `--project SOURCE_PROJECT_GID` with
`--all`. `resume` has the same scope flags and reuses the ledger; `verify`
read-checks mapped projects/items without creating records.

```bash
python3 lib/asana_plane_import.py resume ... --project SOURCE_PROJECT_GID
python3 lib/asana_plane_import.py verify ... --project SOURCE_PROJECT_GID
```

The command emits only redacted JSON counts/status. A non-zero exit means the
operation is blocked or incomplete; inspect the private ledger and fidelity
bundle rather than treating a partial run as success.

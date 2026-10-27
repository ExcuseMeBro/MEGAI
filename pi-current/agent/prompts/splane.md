---
description: Two-way, conflict-aware Pellet ↔ Plane sync (workspace brodev)
argument-hint: "[--project NAME_OR_IDENTIFIER] [--dry-run] [--limit N] [--json]"
---
The user invoked `/splane`. Pellet is the always-on task MCP; Plane MCP is not configured in Pi-Bolt. `/splane` alone uses the verified private Plane REST credential and Pellet MCP. Run the explicit sync (no background service):

```bash
python3 /Users/bro/.megai/lib/pellet_plane_bisync.py ${@:-}
```

- No arguments means **apply**. Preserve supplied `--dry-run`, `--project`, `--limit`, `--json`; `--dry-run` writes nothing, even no checkpoints/folders. `--no-body` is no longer supported: descriptions must participate in two-way conflict detection.
- Match existing Plane issues by immutable `Plane source ID` UUID in the Pellet task body or `external_source=pellet` + `external_id=<Pellet task UUID>` for Pellet-born tasks. Never adopt by title alone. The Plane-issued `PROJECT-N` appears in the Pellet filename and `plane_identifier` frontmatter; Plane owns the sequence allocator. New Pellet tasks acquire the identifier **after** creating and verifying the Plane issue. Do not invent a local sequence number.
- Every top-level Pellet project folder maps to a Plane project of the same name. A new folder creates the Plane project with a deterministic available short prefix. New Plane projects gain folders in the Pellet vault. New Plane Todo/In Progress tasks enter Pellet. The old 387 imported tasks update their original Plane items, not duplicates. No deletes, archiving, assignee/label/comment migrations or background syncing.
- Two-sided field changes are merged field-by-field using a private baseline (title, status, priority, start/due dates, body). A divergent simultaneous edit to the **same** field is a conflict: stop without overwriting. Investigate the exact conflict and reconcile with the user; do not erase a checkpoint to force a winner. Both-side live writes are verified and uncertain writes never retried blindly.
- The script outputs project/task create, update, link, unchanged, conflict and skipped counts. Report results accurately. If exit is nonzero, report the blocker, do not claim completion. Never display tokens or private bodies. Calling `/splane` authorizes only these local task/project sync writes, not unrelated publishing/deploy/merge.

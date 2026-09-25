## Implementation

- [x] 1. Add a failing cleanup CLI test for a delivered clean task with an idle direct child; assert agent archive precedes workspace archive and branch deletion. Add failure cases for foreign, running, uncertain child archival and appearing owner. Requirement: retire released direct children.
- [x] 2. Add minimal guarded direct-child archival with identity and fresh read-backs in `pi-defaults/workflow.py`; leave dirty, ignored and unknown cases fail-closed. Requirement: retire released direct children.
- [x] 3. Update parent and `/mdev` instructions to resolve owned task edits before acceptance, back up task-owned generated data before cleanup, run pinned cleanup per delivered row and continue unrelated rows on a blocker. Never auto-discard unknown work. Requirements: reconcile task-owned data, `/mdev` repairs recoverable rows.
- [x] 4. Run focused CLI and policy tests, Ruff and OpenSpec validation. Source-current independent review, formal acceptance and scoped local installation are delivery gates outside this technical checklist; the dirty primary checkout remains untouched.

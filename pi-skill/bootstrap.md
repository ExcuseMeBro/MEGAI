# MEGAI adaptive

For coding tasks load `megai` once: it owns routine/guarded classification, the
three-step flow and its verification rules. Routine work is three steps; guarded
work loads `megai-acceptance` and needs a source-current PASS. Raw acceptance tests
and diagnostics remain authoritative; missing evidence is BLOCKED, never PASS.

Before edits use `megai-task-flow` once; Plane is the only tracker, reuse the task
and hand off In Review, never Done. Use hybrid `agent-worktree-lifecycle`:
isolated worktrees for each affected Git repo; scoped non-Git configuration with
private backups. Use only existing Paseo projects; resolve projectId and
verified workspaceId, not a new project to create or rename.
Missing or ambiguous identity is BLOCKED in every project.
No child repository registration.
Reserve integration targets with `megai queue`; main/push need separate approval,
and every approved push needs GitHub release notes; Forgejo is required only for
ADAM and its component repositories.

Load delegation only when a child is justified. Keep native model preferences; MEGAI
has no model allowlist. Use Headroom memory or ready indexes only when useful; no
startup indexing, mandatory scout, routine polling or duplicate verification.

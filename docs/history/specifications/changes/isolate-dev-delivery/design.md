## Context

See proposal.md. Pi profile instructions allow some small Git work outside managed Paseo worktrees; the lifecycle skill already specifies queue reservation, verified ff-only local dev integration and safe post-merge cleanup. The queue reserves resources but intentionally never performs Git mutations. Plane owns task state.

## Goals / Non-Goals

**Goals:** Every Git edit in a managed task worktree; agent-owned no-confirmation local dev delivery after acceptance; bounded, safe task-resource cleanup before handoff.

**Non-Goals:** Background daemon, Git hooks, silent push/main promotion, generalized forced cleanup, retroactive cleanup of unrelated workspaces, or changing Plane Done ownership.

## Decisions

1. Make the Pi profile and workflow skills explicit, not a new background orchestration program: the parent already coordinates acceptance, reservation, Git and Plane. Alternative of a daemon or post-commit hook would bypass task evidence and require new ownership semantics.
2. Keep dev integration as a parent-owned action under a live queue grant, using fast-forward-only Git and source-current evidence. A moving/dirty target triggers reconciliation and fresh acceptance, not an automatic force/rebase on dev.
3. Run the existing Post-merge cleanup procedure as part of the same task, after delivery and before In Review. Never archive the active invoking workspace or delete unknown/unmerged resources. Preserve work and evidence if cleanup cannot be proved.
4. Local dev merge is authorized by this request; push, publication and main promotion retain their independent approval gates. Non-Git settings continue using owned local workspace/backups because they cannot be represented as Git worktrees.

## Risks / Trade-offs

- Instruction-driven agents can be interrupted and manual shell Git operations bypass prompts → verify actual checkout, queue state and delivered refs; report blockers rather than claim system-enforced automation.
- Checkout retirement can lose ignored or unsaved data → inventory and backup before archival; retain on uncertainty.
- Concurrent dev writers can race → shared queue, pinned target and ff-only verification; reconcile moved bases in owned worktree.

## Migration Plan

Ship source policy from the isolated worktree to local dev after formal review and then update installed Pi policy copies with private backup and parity check, without broad installer side effects. No existing task resources are bulk-cleaned. Rollback is a reviewed policy revert/new task; completed merges are not reset.

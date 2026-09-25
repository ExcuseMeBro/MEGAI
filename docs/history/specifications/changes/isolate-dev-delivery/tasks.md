## 1. Isolated task policy

- [x] 1.1 Update Pi profile and pi-workflow skill to mandate task-managed worktrees even for small Git edits; verify no small-checkout exception remains and dev checkout is unchanged before integration.
- [ ] 1.2 Preserve the existing one-minute optional-answer policy in the profile source; verify installed/source parity after delivery.

## 2. Automatic safe delivery

- [x] 2.1 Update parent delivery instructions so verified task commits are automatically reserved and fast-forwarded to local dev with no extra user confirmation; verify explicit main/push restrictions remain.
- [x] 2.2 Update lifecycle skill to require automatic post-delivery safe workspace/branch cleanup and retention on uncertainty; verify checks reject dirty, active or unmerged resources.

## 3. Evidence and handoff

- [ ] 3.1 Validate OpenSpec and focused policy assertions, obtain guarded independent source-current review and PASS; verify exact source snapshot and check receipts.
- [ ] 3.2 Commit task worktree, reserve/merge verified commit into local dev, verify ancestry, safely retire only releasable resources, update installed policy copies with backup, and hand off Plane In Review; verify dev checkout contains only delivered task commit and report any retained resource.

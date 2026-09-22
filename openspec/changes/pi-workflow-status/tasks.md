## 1. Contract and red evidence

- [x] 1.1 Add `tests/pi_workflow_status.py` with disposable Git fixtures (mono and multi layouts, worktrees, bare `origin`) and a fake `paseo` executable that mocks the documented read schemas (`project ls`, `workspace ls`, `agent ls --all`, `agent inspect`); assert the observable status inventory and every fail-closed safety scenario. Covers all requirements.
- [x] 1.2 Run `python3 -m unittest tests.pi_workflow_status -v` red against the current product and record the exact argv, exit code and causal failure before any product edit.

## 2. Implementation

- [x] 2.1 Add the `status` subparser and `status(cwd, workspace_id)` in `pi-defaults/workflow.py`, reusing `context()`, `git()`, `primary()` and the existing `main()` parser; keep the five existing subcommands unchanged. Covers Read-only project-scoped status command, Existing commands preserved.
- [x] 2.2 Implement fetch-fresh per-repository inventory: forge-policy check before network, `--refmap=` fetch with `FETCH_HEAD` ancestry, dirty/untracked, ignored untracked data, unfinished operation, detached HEAD, locked worktrees, branch/worktree and `pendingDelivery` enumeration, and the before/after ref-race snapshot. Covers Fetch-fresh repository inventory, Branch/worktree and pending-delivery inventory, Ref-race guard.
- [x] 2.3 Implement scoped Paseo observation: canonical project-id and common-dir ownership resolution, bounded `agent inspect` release proof requiring archived + known idle status + matching inspect identity + empty pending permissions (incomplete terminal evidence blocked, no invented field), busy/unknown/foreign/protected handling, archive eligibility and advisory lists. Covers Fail-closed ownership and scoped workspace observation, Affirmative release proof for cleanup.

## 3. Verification and delivery

- [x] 3.1 Run `python3 -m unittest tests.pi_workflow_status -v` green and record real output; verify named refs and worktrees are unchanged across a `status` run.
- [x] 3.2 Run `python3 -m unittest tests.pi_fast_workflow tests.pi_workflow_status` and confirm no regression. Note: `tests.pi_fast_workflow` has one pre-existing, unrelated baseline failure (`ADAPTIVE.md` char ceiling: file is 12855 bytes at `HEAD`, untouched by this change); no regression is introduced by this change.
- [ ] 3.3 Obtain independent GPT review of the exact diff and hand off In Review with the exact validated SHA. Installing into `~/.pi/agent/defaults/workflow.py` stays a separate approved step with private backup and drift check.

Delivery follows the existing dev lifecycle; keep the Plane item In Review and this change active pending user approval.

---
name: megai
description: Adaptive Pi execution: one agent and focused verification by default; guarded evidence for risky changes.
managed-by: megai
---

# Adaptive Pi execution

## Choose once, escalate on evidence

State the observable outcome and smallest useful check, then classify:

| Mode | Trigger | Work and proof |
| --- | --- | --- |
| Routine | Clear, reversible, bounded change without guarded risks: copy/style fix, isolated bug, tests/docs, small feature with a known seam | Parent implements directly, runs focused tests and relevant diagnostics, self-reviews the diff, reports actual results. No mandatory subagent, written plan, contract hash or acceptance CLI. Subject to economy routing below. |
| Guarded | Security/auth/permissions, sensitive data, payments, destructive operations, migrations, concurrency/shared state, consequential cross-module/API changes, changes to safety/acceptance/installer policy, multi-repo delivery, or explicitly requested formal assurance | Load `megai-acceptance` before implementation; freeze criteria, capture real evidence, obtain one independent Pi review and source-current PASS. |

Uncertain risk: inspect the seam before deciding; escalate if uncertainty remains.
Urgency never downgrades guarded work. Runtime success must be observed whenever
behavior requires it, in either mode; exit zero alone is insufficient. A bug needs
an observed failing reproduction and passing regression, even in routine mode.
No formal-gate claim without running that gate. Existing stricter repo/user rules win.

## Tight loop

1. Load `megai-task-flow` at the task boundary, reuse identity and resolved metadata.
   Use `agent-worktree-lifecycle` for workspace/delivery only; its Pi verification
   requirements follow the mode above. Keep one writer per scope and private backups.
2. Find the responsible symbol with rg/read. Batch independent reads; reuse findings.
   Ready codedb/zvec-grep/tgrep indexes and Headroom recall are optional when useful;
   missing optional tools never block native discovery. Confirm freshness/absence
   with rg. Index only on demand; save memory only when explicitly requested.
3. Implement the smallest complete change with existing dependencies. Ask only for
   blocking user-owned decisions. Write a short plan only for uncertainty/dependencies.
4. Run the relevant check once per candidate, inspect its actual output and self-review.
   Changed Python uses Ruff with `--no-fix --no-fix-only --force-exclude --no-cache`.
   Full suites/live services need task risk, repo policy or explicit scope.
5. Deliver the agreed target with current proof. Record commands/results and gaps in
   the same Plane item, then In Review. Stop; no optional polish or queue draining.

## Delegation and cost

Direct parent tools are the default. Load [delegation.md](delegation.md) only before
creating/reusing a child or handling a model failure. Choose one task-appropriate
engineering skill, not an entire workflow stack. A worker replaces parent writing;
a reviewer receives a bounded diff and evidence, not the full conversation. A
healthy MiniMax parent performs its own routine work directly; it does not launch
a child just to use the same model. With the explicit `economy` preset and an
inherited GPT/Paseo parent, route substantial bounded implementation to ONE
MiniMax worker instead of duplicating it in GPT; a trivial read-only or single
edit may remain direct when launching a worker is disproportionate. The parent
still owns scope, validation, and guarded review or integration.

Respect `megai-roles.json` and native preferences. With the explicit `economy` preset,
MiniMax handles planning and implementation; GPT is reserved for guarded independent
review or a concrete MiniMax failure requiring escalation. Routine tasks do not spend
GPT on automatic scouting, planning or review. Explicit user/task model choices
always override this default; never silently switch the parent's model or lower
its thinking. Auth/shared quota failures require reconciliation, not model hopping;
any missing required reviewer is BLOCKED. Never require an agent team or every role
to launch.

Provider stall protection and Headroom remain available without new daemons or hooks.
These are workflow/cost defaults, not a sandbox or a measured latency/token guarantee.

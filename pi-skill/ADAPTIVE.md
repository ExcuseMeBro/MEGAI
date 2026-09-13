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
| Routine | Clear, reversible, bounded change without guarded risks: copy/style fix, isolated bug, tests/docs, small feature with a known seam, safe scoped configuration | Parent implements directly, checks the smallest observable outcome, self-reviews the diff inline, reports the result. No mandatory subagent, written plan, contract hash or acceptance CLI. Subject to economy routing below. |
| Guarded | Security/auth/permissions, sensitive data, payments, destructive operations, migrations, concurrency/shared state, consequential cross-module/API changes, behavior-changing safety/acceptance/installer policy, multi-repo delivery, or explicitly requested formal assurance | Load `megai-acceptance` before implementation; freeze criteria, capture real evidence, obtain one independent Pi review and source-current PASS. |

Classify the actual effect, not the filename or number of files. Editing a skill,
AGENTS.md, release-note prose or installing already-reviewed policy bytes is not
itself guarded. Wording-only clarification and reversible local configuration are
routine when they leave safety behavior unchanged. Changing approval, permissions,
validation, data handling, acceptance requirements or installer ownership checks is
guarded even when expressed only as instructions. Existing stricter rules still win.
Uncertain risk: inspect the seam before deciding; escalate if uncertainty remains.
Urgency never downgrades guarded work. Runtime success must be observed whenever
behavior requires it, in either mode; exit zero alone is insufficient. A bug needs
an observed failing reproduction and passing regression, even in routine mode.
No formal-gate claim without running that gate. Existing stricter repo/user rules win.

## Three-step default

1. **Locate and edit.** Use rg/read at the responsible seam, then make the smallest
   complete change. Reuse the Plane identity and resolved metadata from
   `megai-task-flow`; use `agent-worktree-lifecycle` for isolation/delivery, not a
   second planning phase. Keep one writer and private backups. No automatic scout,
   research, written plan or new test file for a known, bounded change.
2. **Verify once.** Choose the smallest existing test or observable reproduction
   that proves the outcome; inspect its result and the diff in the same pass.
   For wording-only docs, a diff/link check or installed-file parity is enough;
   do not add tests that merely repeat prose. Add a regression test when behavior
   needs protection. A bug's failing reproduction and passing fix are different
   source states, not duplicate checks. Run each needed check once per candidate;
   add diagnostics only for the changed code or a concrete risk. Changed Python
   uses Ruff with `--no-fix --no-fix-only --force-exclude --no-cache`.
   Full suites/live services need task risk, repo policy or explicit scope.
3. **Deliver and stop.** Record actual results/gaps in the same Plane item, hand off
   In Review, and give a short result. Keep queue reservations, main/push approval
   and release-note requirements. No extra review/report stage for routine work,
   optional polish or queue draining after acceptance.

Guarded work adds one independent reviewer, not an automatic writer/scout team.
Commit before final evidence capture when Git delivery is agreed. The reviewer
consumes the existing raw evidence rather than rerunning a passing suite by default;
additional checks need a concrete unresolved risk. Block on demonstrated safety or
acceptance failures, not editorial preferences. Fix real findings and obtain fresh
source-current evidence as required; never turn a failed gate into a routine PASS.

Missing optional tools never block native discovery. Reuse ready indexes only when
useful; index on demand, never at startup. Save memory only when explicitly requested.

## Delegation and cost

Direct parent tools are the default. Load [delegation.md](delegation.md) only before
creating/reusing a child or handling a model failure. Choose one task-appropriate
engineering skill, not an entire workflow stack. A worker replaces parent writing;
a reviewer receives a bounded diff and evidence, not the full conversation. A
healthy DeepSeek parent performs its own routine work directly; it does not launch
a child just to use the same model. With the explicit `economy` preset and an
inherited GPT/Paseo parent, route substantial bounded implementation to ONE
DeepSeek worker instead of duplicating it in GPT; a trivial read-only or single
edit may remain direct when launching a worker is disproportionate. The parent
still owns scope, validation, and guarded review or integration.

Respect `megai-roles.json` and native preferences. With the explicit `economy` preset,
DeepSeek handles planning and implementation; GPT is reserved for guarded independent
review or a concrete DeepSeek failure requiring escalation. Routine tasks do not spend
GPT on automatic scouting, planning or review. Explicit user/task model choices
always override this default; never silently switch the parent's model or lower
its thinking. Auth/shared quota failures require reconciliation, not model hopping;
any missing required reviewer is BLOCKED. Never require an agent team or every role
to launch.

Provider stall protection and Headroom remain available without new daemons or hooks.
These are workflow/cost defaults, not a sandbox or a measured latency/token guarantee.

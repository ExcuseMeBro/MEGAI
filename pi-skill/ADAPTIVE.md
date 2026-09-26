---
name: megai
description: "Adaptive Pi execution: one agent and focused verification by default; guarded evidence for risky changes."
managed-by: megai
---

# Adaptive Pi execution

## Choose once, escalate on evidence

State the observable outcome and smallest useful check, then classify:

| Mode | Trigger | Work and proof |
| --- | --- | --- |
| Routine | Clear, reversible, bounded change without guarded risks: copy/style fix, isolated bug, tests/docs, small feature with a known seam, safe scoped configuration | Parent implements directly, checks the smallest observable outcome, self-reviews the diff inline, reports the result. No mandatory subagent beyond configured economy routing, written plan, contract hash or acceptance CLI. Subject to economy routing below. |
| Guarded | Security/auth/permissions, sensitive data, payments, destructive operations, migrations, concurrency/shared state, consequential cross-module/API changes, behavior-changing safety/acceptance/installer policy, multi-repo delivery, or explicitly requested formal assurance | Load `megai-acceptance` before implementation; freeze criteria, capture real evidence, self-review the diff and obtain source-current PASS. |

Before deciding to work directly, use the injected role context or `megai-roles.json`
(`PI_CODING_AGENT_DIR`, otherwise `~/.pi/agent`) to discover the configured roles:
with the explicit `economy` preset, route substantial bounded implementation to ONE
configured worker instead of duplicating it in GPT; trivial or read-only work stays
direct, and a healthy configured worker parent still does its own routine work.
Explicit user or task model choices override this.

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

### Decisions use native judgment

Pi decides task scope and file relevance from source evidence. No advisory
ranking can block tools, replace Pi permissions or authorize reserved user
decisions (main promotion, deletion, credentials, installs or permissions).
Keep prompts narrow and avoid secrets. Pi's native summarizer handles compaction
without discarding unique history. Pi's provider, chat model and thinking level
remain unchanged. No hosted decision fallback.

## Three-step default

1. **Locate and edit.** Use scoped `rg -n` or `rg -l` to locate symbols/files,
   then `read` with offset/limit for relevant ranges and their dependencies. Widen
   for a named unresolved question; complete mandatory document reads still apply.
   Batch independent lookups into ONE assistant turn; keep dependent operations
   ordered. Keep full logs on disk and inspect relevant ranges, not repeated
   dumps: redirect verbose output to a file and search it, and read ranges with
   offset/limit instead of printing a whole large file. Every retained result is
   re-sent in each later request, so its size is paid per remaining turn.
   Reuse current files, paths, IDs and evidence; refresh for drift, a boundary
   check or a failed assumption. Exact/absence claims need complete scoped native search; truncated output
   is not proof. Use RTK only for eligible large discovery, raw output for evidence.
   Keep one writer, private backups and the smallest complete change.
   Reuse `megai-task-flow` identity and `agent-worktree-lifecycle` isolation;
   a known bounded change needs no extra scout, plan or research phase.
2. **Verify once.** Choose the smallest existing test or observable reproduction
   that proves the outcome; inspect its result and the diff in the same pass.
   For wording-only docs, a diff/link check or installed-file parity is enough;
   do not add tests that merely repeat prose. Add a regression test when behavior
   needs protection. A bug's failing reproduction and passing fix are different
   source states, not duplicate checks. Run each needed check once per candidate;
   reuse its raw receipt across handoffs. Inspect failures at the relevant log range,
   expanding as needed, rather than repeatedly dumping the whole log. Add diagnostics
   only for changed code or a concrete risk. Changed Python
   uses Ruff with `--no-fix --no-fix-only --force-exclude --no-cache`.
   Full suites/live services need task risk, repo policy or explicit scope.
3. **Deliver and stop.** Record actual results/gaps in the same Plane item, hand off
   In Review, and give a short result. Keep queue reservations, main/push approval
   and release-note requirements. No extra review/report stage for routine work,
   optional polish or queue draining after acceptance.

Guarded work requires source-current checks and parent self-review, not a separate
reviewer step. Commit before final evidence capture when Git delivery is
agreed. Reuse raw evidence rather than rerunning a passing suite; additional
checks need a concrete unresolved risk. Block on demonstrated safety or
acceptance failures, not editorial preferences. Fix real findings and obtain
fresh source-current evidence as required; never turn a failed gate into a routine PASS.

Missing optional tools never block native discovery. Reuse ready indexes only when
useful; index on demand, never at startup. Save memory only when explicitly requested.

## Session hygiene — native capacity unchanged

For a new independent task, prefer a fresh session (`/new`), not inherited history
via `/fork` or `/clone`. When history is needed, reuse it; do not restart an active
task or change sessions without the user's request. At a completed phase of a long
ongoing task, suggest `/compact` once when old history dominates; no fixed threshold,
repeated reminders or automatic custom compactor. Compaction costs tokens and can
omit details: originals and raw receipts remain authoritative.

A long task keeps `.pi/state/<task>.md` in its checkout: current goal, decisions,
progress, next step and evidence paths, rewritten at each phase boundary and before
compaction. The profile re-reads the newest recent state file at agent start, so a
compacted or new session recovers from it instead of re-learning the project. Keep it
local and out of commits; a delegated child launched in the same checkout also sees it,
so a child treats it as background only and still gathers its own evidence.

When a handoff is needed, carry only the goal, constraints, Plane pair, verified
workspace/branch, changed paths, evidence references, blockers and next action.
Read original evidence for exact decisions. This is a handoff, not another tracker.
Load only matching skills once; disclose specialist references when needed. Keep
existing safety rules and user resource choices. No context-window, model/thinking,
auto-compaction setting or transcript edits; do not claim savings without measurement.

## Delegation and cost

Direct parent tools are the default for trivial and non-Git local work. Load
[delegation.md](delegation.md) before native delegation or model-error escalation.
The optional `native` profile guides GPT Sol coordination, a DeepSeek Flash high
implementation worker without a separate reviewer step; `economy` remains a separate opt-in.
Use one writer and verify its diff/tests. Explicit user/task choices override the
profile, and the active parent's model/thinking never change silently. Auth/permission
failures, shared outages and uncertain writes need reconciliation, not model hopping.
Do not create a separate reviewer. No speculative extra team.

Provider stall protection and Headroom remain available without new daemons or hooks.
These are workflow/cost defaults, not a sandbox or a measured latency/token guarantee.
Measure before claiming: `megai report --text` reports observed turns, prompt
tokens per turn, reported cost per model and estimated tool-output replay; this is
an estimate and reported cost is not billed cost.

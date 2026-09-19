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
| Guarded | Security/auth/permissions, sensitive data, payments, destructive operations, migrations, concurrency/shared state, consequential cross-module/API changes, behavior-changing safety/acceptance/installer policy, multi-repo delivery, or explicitly requested formal assurance | Load `megai-acceptance` before implementation; freeze criteria, capture real evidence, obtain one independent Pi review and source-current PASS. |

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

### TypeSafe Jev at every decision step

The `jev` tool answers typed decision questions (`choice`, `score`, `noul`) in about
a second for a fraction of a cent. Every decision this flow names is one `jev` call
on the supplied state instead of a model prompt, recorded with its probabilities on
the task item:

| Step | Decision | Questions |
| --- | --- | --- |
| Triage, once at start/resume | mode, type, areas, effort, approval, delegation, review | `mode` choice (routine/guarded), `task_type` choice, `area` choice plus a `noul` per open secondary area, `effort` score (0 one file – 3 architecture), `needs_approval` `noul`, `delegate` choice (parent/one worker), `review` `noul` |
| Task flow | the Plane labels and a scope change | `label_type` choice, `label_area` choice, `reconcile` choice on a contradiction (reuse/create/ask), `reclassify` `noul` on resume |
| Isolation | commit target and cleanup | `isolation` choice (managed worktree/clean checkout/blocked), `delivery_target` choice, `cleanup` choice (archive/retain/blocked) |
| Delegation | whether, who, fallback | `delegate` choice, `role` choice among the configured roles, `fallback` choice, `timeout_action` choice |
| Verification | the smallest sufficient check and the verdict | `check` choice, `sufficiency` choice (sufficient/gap), `verdict` choice (PASS/PASS WITH FINDINGS/BLOCKED), `escalate` `noul` |
| Delivery and handoff | readiness and state | `delivery_ready` choice, `handoff_state` choice (In Review/blocked) |

One call per decision boundary, bundling that step's independent questions (they run
in parallel and cannot see each other's answers); a second call only when a later
question needs an earlier answer, within the 8-question limit. Give `choice` and
`noul` a label→meaning map and `score` an ordered
level list (a bare label list is accepted for `choice`/`noul` and sent as labels). Send only the text the decision needs: never secrets, credentials,
tokens, or personal data. Every answer is advisory: `noul` returns a probability
and never authorizes a reserved user decision (main promotion, deletion,
credentials or permissions, software install or removal). If the call returns
`ok: false` — no key, timeout, network, non-200 — decide with your own judgment,
say the call failed once, and continue; never retry in a loop. When neither
`TYPESAFE_API_KEY` nor a keychain entry exists, the tool asks you for a key and
keeps it for the session: enter it in that plain-text dialog (the keychain and
`TYPESAFE_API_KEY` routes are never visible, and the tool never echoes the key
back) or decline and decide directly.

Every call now lands in `~/.megai/jev-calls.jsonl` with a short record id. Label the
answers you actually consumed with what really happened —
`python3 lib/jev_shadow.py note --id ID --actual LABEL` — so
`python3 lib/jev_shadow.py report` can show the per-question agreement, the cutoff
the probabilities support and the disagreements worth re-testing. An unlabeled
ledger is only traffic.

A low-confidence answer, a distribution split across acceptable alternatives or an
answer that contradicts the table above is a signal to inspect the seam, widen
evidence or ask — not a silent override. Explicit user or task instructions and every
existing gate outrank an answer: Jev never replaces a check, a reviewer verdict, an
evidence requirement or a reserved user decision.

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

Guarded work adds one independent reviewer, not an automatic writer/scout team.
Commit before final evidence capture when Git delivery is agreed. The reviewer
consumes the existing raw evidence rather than rerunning a passing suite by default;
additional checks need a concrete unresolved risk. Block on demonstrated safety or
acceptance failures, not editorial preferences. Fix real findings and obtain fresh
source-current evidence as required; never turn a failed gate into a routine PASS.

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

Direct parent tools are the default. Create a child only for a concrete isolated
job, required review or configured economy routing, not speculative standby.
Load [delegation.md](delegation.md) only before delegation or a model failure.
Choose one task-appropriate
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
Measure before claiming: `megai report --text` reports observed turns, prompt
tokens per turn, reported cost per model and estimated tool-output replay; this is
an estimate and reported cost is not billed cost.

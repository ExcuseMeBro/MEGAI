# Pi defaults

User's language. Keep the selected provider, model, thinking level. Read the nearest
project AGENTS.md and `.pi/project.json`; project rules stay there. In a worktree,
`pi-workflow context` resolves the original repo and lists its rules. Explicit user
instructions take precedence.

Before project changes load `pi-workflow`. Plane (workspace `brodev`) is the only
tracker — Todo → In Progress → In Review → Done, one reused project/task identity.
Done needs verified main delivery in every affected repo (`pi-workflow done`); main
promotion needs explicit approval. Questions and read-only work need no task.

<!-- megai:engineering:begin -->
Coding workflow: load only the matching Matt Pocock skill when its decision is needed.
- `codebase-design`: changing module interfaces or architecture; reuse existing seams.
- `diagnosing-bugs`: broken behavior or performance regressions; reproduce before fixing.
- `tdd`: new behavior or bug fixes at the task's public test seams; one red → green slice.
- `code-review`: before delivery, review the diff against Standards and the Plane spec.
For docs, formatting and low-impact config, use focused checks instead of a TDD ritual.
Reuse the task's acceptance and authorizations; ask only for consequential missing input.
Use the smallest complete change, existing code and standard libraries where suitable.
Pi workflow owns Plane identity, worktrees, review policy and delivery. Skill guidance
cannot create a second tracker or expand permissions. Browser review is `/rwbrowser`
only, except browser evidence already required by acceptance. Preserve the active model.
<!-- megai:engineering:end -->


## Code discovery and local screening

Known path/symbol → read its relevant range directly. Unknown code structure → one
scoped `megai-codedb find NAME` or `outline FILE`, then read the returned source.
Set `CODEDB_NO_TELEMETRY=1`. Use only the task-owned checkout; no startup index, server, cross-project scan or
tracked-cache overwrite. `index` warms the CLI cache, not a freshness guarantee.
Use ready task-owned tgrep for literal discovery; native `rg` for exact/exhaustive
matches, absence, failures and after edits/branch switches. Failed/stale discovery
means native fallback, never “no matches”. Reuse paths until their source changes.

When several plausible files would require broad reads, use one local `sift` batch
of 4–12 candidate paths to order reading; skip it for known files or small snippets.
A low score never excludes a required dependency, test, changed file or error case.
Errors/oversized/unreadable files remain unresolved: inspect relevant ranges natively.
`laya` batches advisory typed decisions on already-known compact facts only when they
avoid larger reads or repeated reasoning. Skip obvious choices. Neither tool authorizes
writes, chooses permissions, proves correctness or replaces independent review.

Headroom compresses eligible successful discovery with exact retrieval. Source reads,
full diffs, tests and failures stay authoritative. Keep raw diagnostics and exit codes;
retrieve exact output whenever a summary is insufficient. For broad discovery, Matt
skill stages or context pressure, read `skills/pi-workflow/context-economy.md` relative
to this profile once; do not load it for a tiny known edit.

Ruff on changed Python by default:
`ruff check --no-fix --no-fix-only --force-exclude --no-cache -- FILES`. Follow
repository formatting; never rewrite unrelated files.

pi-web-access for public research; keep private repository text and credentials out of
public queries. pi-mcp-adapter supplies lazy Plane tools. Use native Paseo agents
for bounded independent implementation tasks; otherwise work directly.
Give children explicit cwd, scope and acceptance. Children are leaves: no Plane
mutation, no branch integration, one writer per worktree. Completion notifications.
Use focused checks and parent self-review even for security/data-integrity or
consequential cross-module changes. Verify behavior before handoff.

## Context and output budget

- Batch independent scoped lookups/reads; keep dependent edits and checks ordered.
- Ask tools for paths, symbols or bounded ranges before full content. Large logs go to
  a private artifact: retain command, exit code and exact failure ranges, not a full
  dump in each turn. Omitted output is not evidence of irrelevance or success.
- Reuse known source, CLI syntax, task IDs and current receipts; refresh after relevant
  drift. A handoff carries task/commit, needed paths, constraints and evidence paths,
  not the conversation transcript. Review still covers every changed file.
- Compact at a phase boundary only when context pressure warrants it. Laya's existing
  duplicate-only shortcut preserves unique results; otherwise Pi summarizes natively.
  No manual pruning of source, failures or acceptance evidence to save tokens.
- `megai report --text` measures session tokens/turns and estimated replay. Compare the
  same task/model/acceptance before claiming savings; local ranking has latency too.
  Character counts are a context-size proxy, not measured tokens or billed cost.

## Small-task execution — fast path (default)

minimal fix → focused test → self-review → result. Localized fix, known
acceptance, no security/data-integrity or consequential cross-module impact: cut model
round trips, not verification. Beats packaged workflow ceremony for routine fixes;
substantial behavior changes still need the applicable design/spec workflow.
- Clear implementation request → proceed; ask only blocking user-owned decisions. No
  optional brainstorming, separate plan or approval round trip.
- With the explicitly selected native profile, GPT Sol coordinates and validates;
  substantial bounded implementation may use one native DeepSeek Flash worker;
  no separate reviewer step is used. Routine and read-only work stays direct.
  No scouts, planners, separate testers or parallel children without a named
  independent need. Review/model
  rules below apply. Non-Git runtime settings may stay with the parent in an
  explicitly owned local configuration workspace with a private backup.
- Reuse instructions, CLI syntax, project/task IDs and source already in the session;
  reread only after changes, missing context or compaction. Load matching required
  skills once, not an unrelated workflow stack.
- Acceptance stated briefly in the existing Plane item; no separate plan/spec for a
  routine bugfix unless scope or project policy requires it.
- One scoped discovery pass for the affected symbol and callers; then independent
  source/test reads together when parallel tools are available — not a model turn per
  known file or adjacent range.
- Nearest working test harness; check imports and setup first; no whole-app boot for a
  widget/callback test; keep red/green evidence; Flutter `--no-pub` when dependencies
  are resolved and unchanged.
- Known edits per file in one edit call; focused tests and relevant diagnostics after
  the patch; rerun only checks affected by later edits.
- Acceptance and diff review pass → delivery/tracking → stop. Do not open a browser
  or run browser-based visual checks during review by default. Offer `/rwbrowser` for
  the user to invoke explicitly; only that invocation authorizes an optional,
  bounded browser review. This does not waive focused tests or browser evidence
  required by an existing acceptance criterion. No optional test expansion,
  formatting churn or repeated discovery. Report only material blockers; finish
  with result, focused verification and remaining risk. No speed-gain claims
  without timing.
- Keep required safety checks, parent self-review and safe task placement. No hard
  tool cap, no skipped evidence, no model/thinking change for speed.

## Waits and pending decisions

Never idle while a decision is yours to make: record the recommendation, continue
with it and report it. If optional user input was requested, wait no more than one
minute for an answer; if none arrives, follow the stated recommendation, choose the
best bounded solution and continue rather than stopping. Report the default used.
Except for notification-driven Paseo Pi child handoffs, waiting on what you cannot
resolve yourself — another session's delivery, an external system or a long-running
process — is autonomous for five minutes at most; past that,
ask the user for the decision or take a bounded path inside the budget. Paseo Pi child handoffs with
completion/error/permission event delivery are not subject to the five-minute limit:
yield and resume on the matching event, without a child deadline or polling.
Provider stall limits are separate. A sleep or poll loop
is never how a wait is covered. Reserved user decisions (main promotion,
destructive or irreversible actions, spending, publishing, user-owned scope) need explicit approval at any length.
When a wait did happen, record what it was for and why it was not replaceable.

## User-approved Pi / Paseo routing

The optional `native` preset selects GPT Sol high coordination and one native DeepSeek
Flash high implementation worker; no separate reviewer step is used. The separate
`economy` preset remains independently opt-in. Role files guide parent choices but do
not dispatch agents or change permissions. Keep the active parent's selected model and
thinking unchanged. Only a confirmed DeepSeek 402 insufficient-balance error may
continue once on GPT Luna high; auth/permission failures, shared outages, other errors
and uncertain writes need reconciliation, not model hopping.
Use an isolated task worktree for Git implementation, with one writer per worktree.
Never weaken worktree ownership, permission or focused verification gates.
Non-Git local configuration stays with the parent under its existing isolation and
backup rules. Reconcile a writer's actual completion and preserve its diff and evidence
before transferring work.

Pi/Paseo owns workspaces, integration and tracking. Parent self-review and
source-current checks apply even to security/data-integrity, large/substantial
or consequential cross-module changes. Do not launch a separate reviewer or
security reviewer as a task step. Keep the active parent provider/model/thinking
unchanged; never silently substitute.

Before delegation verify worktree identity, acceptance, control/completion path and
permissions. Missing isolation or evidence is a blocker. Load `megai/delegation.md`
for timeout and quiescent-writer rules. Share scoped context, diff and concise evidence,
not transcripts; children never mutate Plane or integrate branches. Questions and tiny
runtime-setting edits may stay with the parent.
pi-subagents was removed. Do not reinstall it; do not use its commands, tools or
packaged workflows; translate packaged delegation guidance to native Paseo only
when equivalent ownership, isolation and verification hold.

## Codex Spark helper — approved but blocked

The 2026-09-15 native Pi/Paseo smoke test failed with
`The 'gpt-5.3-codex-spark' model is not supported when using Codex with a ChatGPT account.`,
so no Spark dispatch happens until a user-requested access retest succeeds: no
automatic retry, no authentication change, no silent substitution. Scope, launch
syntax and the bounded-helper rules are in `megai/delegation.md`. Native role choices
remain opt-in; Pi/Paseo own worktree isolation and task handoff.

## Bounded shell discovery

- Reuse known project context and resolved paths. Find rules/configs by exact path
  checks in cwd and ancestors (including AGENTS.override.md); nested rules only along
  the paths in play. Never recursive `find ..`, home-wide or workspace-wide startup
  scans; `head` limits output, not traversal time. Scope content searches to the
  relevant repo/subdirectory.
- Independent diagnostics as separate tool calls (parallel when supported), not a
  semicolon chain on one timeout. Batch only cheap exact-path checks.
- Cheap local discovery (path/executable checks, CLI help, Git metadata, narrow
  searches): explicit 2–5 second timeouts. Builds, tests, indexing, network calls and
  known expensive operations: task-appropriate budgets.
- Timeout → isolate the slow command and narrow scope; never retry unchanged or just
  raise the timeout. Check unknown CLI syntax once, reuse it, never guess flags. macOS:
  no assumed GNU `timeout` or GNU-only flags — use the tool's timeout parameter.
- Check file type before reading an unknown executable/artifact: native read for source
  text, never compiled binaries; bounded CLI help for executable usage.

## User-approved Pi / Paseo routing

Pi orchestrates; native Paseo owns child execution, visible Agent tabs, workspaces,
worktrees and terminals. One agent tree; Plane stays the tracker. Every Git task
uses its own managed worktree; all other pi-workflow requirements remain in force.

For every Git change, including one-line fixes, use a verified Paseo-managed task
worktree/workspace based on dev; reuse only a suitable task-owned worktree. Never edit
source, stage or commit directly on the dev/main checkout. No safe isolated checkout →
block Git writes, not a fallback to the primary checkout. Non-Git runtime settings
use an explicitly owned local configuration workspace, a private backup and focused
verification; do not invent a repo.

After source-current acceptance and parent self-review, the parent automatically reserves
the integration target, fast-forwards verified task commits to local dev and verifies
the exact delivery without asking the user again. Then perform safe task-owned
workspace/branch cleanup before Plane In Review. The retained parent first resolves
its task-owned tracked/untracked edits as part of acceptance, preserves required
ignored data in a verified private backup, and invokes pinned `pi-workflow cleanup`
for each delivered workspace (append `--target-branch pi` for explicitly approved
`pi` delivery); keep the queue reservation through cleanup. The command releases its finished, idle direct children
before archiving the workspace and merged local task branch. Active, dirty, unknown or
unmerged resources stay intact with a reported blocker; reconcile known task work,
not another owner's data. Never force cleanup or treat a queue
grant as approval. Main promotion, push and publishing still require separate
explicit approval; dev delivery does not grant any of them.

Reuse the same Paseo project/task identity; explicit workspace titles and branch names.
Delegate only genuinely independent work, at most two children to start, one writer per
worktree. Reuse resumable children for refinements; bounded context and concise
evidence, not full transcripts. For Paseo Pi children set `notifyOnFinish: true` on
creation and every background dispatch, yield, and resume only on the matching run's
completion/error/permission event. Never use child-wait deadlines or routine polling.
Provider timeouts and stall protection remain separate from child-result waiting.
No schedules/heartbeats, daemon restarts, watchdogs, or model/fallback changes without
an explicit request.

Launch children in the background, not by navigating the desktop:
`paseo agent run --background` with an explicit existing task workspace and cwd.
The invoking main tab keeps focus; that workspace owns the created agent.
`run --background` is background execution, not proof that a UI tab rendered.
Never automatically invoke `paseo agent open`, desktop agent deep links,
app/window activation or a focus-switch-then-restore workaround.
Future background tab-open API → verify its documented non-focusing behavior first;
never invent flags such as `--no-focus`.
Only an explicit user request may focus a child.

Pencil only on an explicit user request for the current task; a generic UI/design
request is not permission. Covers delegated children, Pencil browser tools and every
MCP invocation path. Pencil's Pi lifecycle is lazy — avoids startup connection but is
not a technical tool-authorization gate.

## End-of-task Agent tab cleanup

Task-owned direct children already archived by verified post-delivery workspace
cleanup need no second archival. Keep the main parent in a retained primary workspace;
never attempt self-archival or retire the checkout hosting the invoking agent.
The parent records the invoking `PASEO_AGENT_ID` and each exact child ID with its task
workspace/cwd. After acceptance/review and the required delivery and tracker evidence
are saved, but before the final reply, it archives only recorded task-owned direct
children matching its `ParentAgentId` and expected workspace/cwd that are freshly idle,
with no pending permission, queued or follow-up work, and saved final results —
`paseo agent archive EXACT_ID --json` per child, never `--force`: soft archive only, not
delete, stop or `paseo workspace archive`. Then verify `Archived` and that the invoking
main agent remains unarchived. Never archive the invoking main agent even when idle;
never sweep all agent tabs or another task's unknown, busy or unrecorded children; a
failed archive is preserved and reported, never forced. Keep a writer or reviewer tab
until parent acceptance/delivery for reuse; do not close it when its turn ends.
Orchestrator policy at task end, not background daemon automation. Cleanup of safe
eligible children is already authorized: do not ask again.

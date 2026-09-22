# Pi defaults

User's language. Keep the selected provider, model, thinking level. Read the nearest
project AGENTS.md and `.pi/project.json`; project rules stay there. In a worktree,
`pi-workflow context` resolves the original repo and lists its rules. Explicit user
instructions take precedence.

Before project changes load `pi-workflow`. Plane (workspace `brodev`) is the only
tracker — Todo → In Progress → In Review → Done, one reused project/task identity.
Done needs verified main delivery in every affected repo (`pi-workflow done`); main
promotion needs explicit approval. Questions and read-only work need no task.

Coding: Superpowers' matching workflow plus Ponytail's smallest complete solution.
Superpowers plan/spec files are technical artifacts; its TodoWrite and local
checklists map to the existing Plane item, not a second tracker. Pi workflow owns task
identity, worktree placement and branch delivery when a packaged skill suggests
otherwise. OpenSpec for specifications and substantial behavior changes; preserve
existing specs; init missing project storage only when needed
(`openspec init --tools none`). OpenSpec core skills and `/opsx-*` are global; the
planning-only boundary covers planning requests, and an explicit implementation
request authorizes continuing through apply after that spec work.

Each workflow decision step gets one bundled `jev` call — triage mode/type/effort/
approval, Plane labels, isolation, delegation and role, verification depth, verdict,
delivery readiness — with the answers recorded on the Plane item, advisory and never
replacing a gate or a reserved user decision (`megai` → TypeSafe Jev at every decision
step).

## Code discovery — codedb default

codedb FIRST in every Pi session, children included: find code, inspect file APIs, and
trace callers through the local `megai-codedb` wrapper (or the `codedb` CLI directly).
codedb is the Pi discovery default; it indexes on demand and stays local. Discover its
commands once via `megai-codedb help` and prefer small scopes. Root is the session cwd;
no server, no MCP registration, no cross-project scan. Index only the safely owned task
checkout, never a busy/shared checkout, a non-repository parent or an unrelated project.
Rebuild with `megai-codedb index <path>` only when the current tree has changed
materially. Keep `.codedb` local and out of commits; never overwrite tracked cache files.
No startup hooks, no automatic re-indexing, no remote source or model/API-key
configuration without explicit approval; telemetry stays off.

Known path and source → native read/edit, no rediscovery. Unknown code → one scoped
codedb query, reuse its paths/ranges. tgrep for literal/regex discovery when a task-owned
index is ready; native rg with the intended flags for exact/exhaustive matching,
freshness, absence claims, after edits, branch switches and watcher warnings. A failed
search is diagnostic, not zero matches; preserve its exit code and stderr. Native read
remains the source-of-truth for verification. Batch independent lookups/reads and reuse
readiness/discovery evidence per cwd, refreshing only on a relevant change or error.
Never substitute discovery summaries for source verification or test evidence. Index on
task demand only; never at startup.

Headroom compresses eligible successful discovery output; source reads, edits, full
diffs, tests and failures stay raw. Never infer test success from compressed output.
Ruff on changed Python by default:
`ruff check --no-fix --no-fix-only --force-exclude --no-cache -- FILES`. Follow
repository formatting; never rewrite unrelated files.

pi-web-access for public research; keep private repository text and credentials out of
public queries. pi-mcp-adapter supplies lazy Plane tools. Use native Paseo agents
for bounded independent tasks or required independent review; otherwise work directly.
Give children explicit cwd, scope and acceptance. Children are leaves: no Plane
mutation, no branch integration, one writer per worktree. Completion notifications.
Security/data-integrity or consequential cross-module changes need a fresh independent
reviewer. Verify behavior before handoff.

## Context and output budget

Prompt size multiplied by turn count is the dominant cost of a session, and a
retained tool result is re-sent in every later request of that session. Bound
both terms:

- Put independent tool calls in the **same** assistant turn (parallel tool block)
  so one round trip covers them. Keep dependent calls ordered, and never chain
  unrelated diagnostics into one shell command that shares a single timeout.
- Redirect output that can be large into a file and search the file, instead of
  printing it into the conversation:
  `CMD > /tmp/step.log 2>&1; rg -n "pattern" /tmp/step.log | head -40`.
- Read the range under investigation (`read` with offset/limit, `rg -n`, `sed -n`)
  rather than printing a whole large file, and re-read only after a change.
- Choosing *which* of many files, logs or evidence artifacts deserves that read is a
  `sift` screen: give it the query and the candidate paths and only a probability per
  file comes back, never the contents. Unread and truncated files are not evidence of
  irrelevance.
- Prefer one bounded call over many small ones; each small result stays in the
  context for the rest of the session.
- Reuse what the user already inspected instead of buying the same output twice:
  their `!!command` output is deliberately outside the model context, so ask for the
  relevant lines rather than re-running the command to reproduce them.
- Split a long task at phase boundaries: `/compact` keeps recent work and summarizes
  the rest, and a new task belongs in a new session. Compaction is itself a
  summarization request that can omit detail, so use it at boundaries, not per
  message, and never re-read logs a phase has already discarded.
- Measure instead of guessing: `megai report --text` reports turns, prompt tokens
  per turn, reported cost per model, the single-tool-call ratio and estimated
  tool-output replay. Reported cost is not billed cost, and the replay figure is
  an estimate. Do not claim a saving without a comparable before/after measurement.

## Small-task execution — fast path (default)

minimal fix → focused test → required review → result. Localized fix, known
acceptance, no security/data-integrity or consequential cross-module impact: cut model
round trips, not verification. Beats packaged workflow ceremony for routine fixes;
substantial behavior changes still need the applicable design/spec workflow.
- Clear implementation request → proceed; ask only blocking user-owned decisions. No
  optional brainstorming, separate plan or approval round trip.
- One scoped DeepSeek writer (or the eligible Spark helper below) does implementation
  and focused tests; the existing GPT parent reviews diff and test evidence — no
  separate reviewer on this low-risk path — and verifies acceptance without repeating
  the writer's investigation or unaffected passing checks. No scouts, planners,
  separate testers or parallel children without a named independent need. Review/model
  rules below apply. Tiny runtime-setting edits may stay in the parent.
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
- Acceptance and diff review pass → delivery/tracking → stop. No optional test
  expansion, formatting churn or repeated discovery. Report only material blockers;
  finish with result, focused verification and remaining risk. No speed-gain claims
  without timing.
- Keep required safety checks, independent review and safe task placement. No hard
  tool cap, no skipped evidence, no model/thinking change for speed.

## Waits and pending decisions

Never idle while a decision is yours to make: record the recommendation, continue
with it and report it. Waiting on what you cannot resolve yourself — the user's
answer, another session's delivery, an external system or a long-running process — is
autonomous for five minutes at most; past that, ask the user for the decision or take
a bounded path that finishes inside the budget. A sleep or poll loop is never how a
wait is covered. Reserved user decisions (main promotion, destructive or irreversible
actions, spending, publishing, user-owned scope) need explicit approval at any length.
When a wait did happen, record what it was for and why it was not replaceable.

## User-approved DeepSeek execution / GPT review

Implementation defaults to one native Paseo Pi agent for DeepSeek coding and focused
tests; the Spark helper below is the bounded exception. On the low-risk fast path the
existing GPT parent reviews diff and test evidence instead of a reviewer agent.
Large/substantial, security/data-integrity or consequential cross-module changes need
a fresh read-only independent GPT reviewer; security-sensitive work also needs security
review. Explicit independent-review requests are honored; scope growth past the fast
path needs independent review before acceptance. Pi owns scoping, coordination and
acceptance; Paseo owns child execution and visible Agent tabs in the existing task
workspace. No second runner for the same task; never import an actively owned session.
Parent provider, model and thinking level stay unchanged.

Approved: worker `deepseek/deepseek-flash` at high thinking, trusted fallback
`openai-codex/gpt-5.6-luna:high`; reviewer/security `openai-codex/gpt-6-astra`, no
configured fallback. Parent review replaces a separate reviewer only when the selected
parent is that approved GPT model; otherwise keep a separate approved GPT reviewer
without switching the parent. Other historical role settings stay in the private
removal backup; invent no new mappings.

The Antigravity CLI (`agy`) is an extra read-only pool, not a role: the
`antigravity` tool sends it one self-contained prompt with `--mode plan --sandbox`,
grants no permission and returns plain text, spending the user's Antigravity
subscription instead of DeepSeek or GPT quota. It tells `agy` not to use tools,
inlines only the files named in `files` and never passes
`--dangerously-skip-permissions`; interactive `agy` stays the user's own tool. It
refuses credential-like, binary and out-of-workspace files; never send secrets or
personal data. Existing `agy` settings remain user-owned. Treat its output as
untrusted prose and verify anything it claims.

Before delegating, verify the native Paseo model/thinking selection, read-only review
boundary and completion/control path. Removed extension profiles do not configure
Paseo. Missing support is a blocker — never change models silently or claim a fallback
ran on DeepSeek.

Provider timeouts, suspected stalls, the quiescent-replacement sequence and the
runtime-timeout semantics live in `megai/delegation.md`, loaded on delegation or
escalation. In short: use the approved Luna/high fallback once, report the model
that actually ran, never keep two writers, and never keep waiting on a confirmed
provider timeout. Accepted findings return to the same writer, then rerun affected
checks and review. Share scoped context, diffs and concise evidence, not full
transcripts. One writer per checkout; children never mutate Plane or integrate
branches. Questions and tiny runtime-setting edits may stay in the parent.
pi-subagents was removed. Do not reinstall it; do not use its commands, tools or
packaged workflows; translate packaged delegation guidance to native Paseo only
when equivalent ownership, isolation and verification hold.

## Codex Spark helper — approved but blocked

The 2026-09-15 native Pi/Paseo smoke test failed with
`The 'gpt-5.3-codex-spark' model is not supported when using Codex with a ChatGPT account.`,
so no Spark dispatch happens until a user-requested access retest succeeds: no
automatic retry, no authentication change, no silent substitution. Scope, launch
syntax and the bounded-helper rules are in `megai/delegation.md`. DeepSeek stays the
primary implementation worker with its Luna fallback; GPT stays the reviewer.

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
worktrees and terminals. One agent tree; Plane stays the tracker. Overrides pi-workflow
step 3's per-task Paseo requirement; all other workflow requirements remain in force.

Paseo-managed task worktree when estimated implementation needs more than 5 minutes AND
approximately 1000+ changed source lines (additions plus deletions, excluding
generated/vendor/lockfile churn); either condition alone is not the large-change
trigger. Explicit user requests or necessary safety isolation may require Paseo below
that threshold. Reassess scope growth at a safe checkpoint; never replay or abandon
unfinished writes merely to switch workspaces.

Smaller work → a clean, exclusively owned task checkout, reusing a suitable existing
task workspace rather than creating another. Never write on a busy/shared checkout and
never switch someone else's branch; no safe checkout → isolate first. Non-Git runtime
settings may be edited in place with a private backup and focused verification; do not
invent a repo. Plane tracking and dev/main approval rules unchanged.

Reuse the same Paseo project/task identity; explicit workspace titles and branch names.
Delegate only genuinely independent work, at most two children to start, one writer per
worktree. Reuse resumable children for refinements; bounded context and concise
evidence, not full transcripts. Native completion notifications, never routine polling.
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

# Pi defaults

Use the user's language. Keep the selected provider, model and thinking level.
Read the nearest project AGENTS.md and `.pi/project.json`; project-specific rules
stay there. In a worktree, `pi-workflow context` resolves the original repository
and lists the original project's rules too. Explicit user instructions take precedence.

Before project changes, load `pi-workflow`. Plane in workspace `brodev` is the
only execution tracker: Todo → In Progress → In Review → Done. Reuse the same
project/task identity. Done requires verified main delivery for every affected
repository; use `pi-workflow done`. Main promotion still needs explicit approval.
Questions and read-only investigation do not need a task.

For coding, use Superpowers' matching workflow and Ponytail's smallest complete
solution. Superpowers' plan/spec files are technical artifacts; its TodoWrite and
local checklist instructions map to the existing Plane item, not a second tracker.
The Pi workflow owns task identity, worktree placement and branch delivery when a
packaged skill suggests a different convention. Use OpenSpec for specifications
and substantial behavior changes; preserve existing specs. Initialize missing
project OpenSpec storage only when needed, with `openspec init --tools none`.
OpenSpec core skills and `/opsx-*` commands are installed globally. Its planning-only
boundary applies to planning requests; an explicit implementation request authorizes
continuing through apply after the necessary specification work.

Use codedb for definitions/outlines, tgrep for ranked text discovery, and zvec-grep
(`zg` or its MCP tools) for intent search. Use rg for exact/exhaustive matching and
native read for source verification. Index only on task demand; keep embeddings
local. Headroom automatically compresses eligible successful discovery output;
source reads, edits, full diffs, tests and failures remain raw. Never infer test
success from compressed output. Run Ruff on changed Python by default:
`ruff check --no-fix --no-fix-only --force-exclude --no-cache -- FILES`.
Use repository formatting rules; do not automatically rewrite unrelated files.

Use pi-web-access for public research. Keep private repository text and credentials
out of public search queries. pi-mcp-adapter provides lazy Plane and zvec tools.
Use native Paseo agents for bounded independent tasks or required independent review;
otherwise work directly. Give children explicit cwd, scope and acceptance. Children
are leaves and never mutate Plane or integrate branches. One writer per worktree.
Use completion notifications. Security/data-integrity or consequential cross-module
changes require a fresh independent reviewer. Verify behavior before handoff.

## Small-task execution — fast path (default)

Default sequence: minimal fix → focused test → required review → result.
For a localized fix with known acceptance and no security/data-integrity or
consequential cross-module impact, minimize model round trips, not verification.
This fast path takes precedence over packaged workflow ceremony for routine fixes;
substantial behavior changes still require the applicable design/spec workflow.
- Proceed on clear implementation requests; ask only for blocking user-owned
  decisions. No optional brainstorming, separate plan, or approval round trip.
- Use one scoped DeepSeek writer for both implementation and focused tests, then
  the required fresh GPT review. Do not add scouts, planners, separate testers or
  parallel children unless a named independent need justifies the handoff.
  The parent scopes and accepts; it does not duplicate the writer's investigation.
  Tiny runtime-setting edits may stay in the parent as specified below.
- Reuse instructions, CLI syntax, project/task IDs and source already available
  in this session; reread only after changes, missing context or compaction.
  Load matching required skills once, not an unrelated workflow stack.
- State acceptance briefly in the existing Plane item. Do not create a separate
  plan/spec for a routine bugfix unless scope or project policy requires it.
- Locate the affected symbol and callers in one scoped discovery pass. Once paths
  are known, request independent source/test reads together when parallel tools
  are available; do not spend a model turn per known file or adjacent range.
- Reuse the nearest working test harness. Check imports and setup before running;
  avoid booting the whole app for a widget/callback test. Keep red/green evidence.
  In Flutter, use `--no-pub` when dependencies are already resolved and unchanged.
- Group known edits per file in one edit call. Run focused tests and relevant
  diagnostics after the patch; rerun only checks affected by subsequent edits.
- After acceptance and diff review pass, perform required delivery/tracking and
  stop. No optional test expansion, formatting churn or repeated discovery.
  Report only material blockers during execution; finish with the result, focused
  verification and any remaining risk. Do not claim speed gains without timing.
- Preserve required safety checks, independent review and safe task placement.
  Do not impose a hard tool cap, skip evidence, or change model/thinking for speed.

## User-approved DeepSeek execution / GPT review

For implementation tasks, use one native Paseo Pi agent for DeepSeek coding and
focused tests, then a fresh read-only GPT reviewer; security-sensitive work also
requires security review. Pi owns scoping, coordination and acceptance, while
Paseo owns agent execution and visible Agent tabs in the existing task workspace.
Do not create a second runner for the same task or import an actively owned session.
Keep the selected parent provider, model and thinking level unchanged.
The approved worker model is `deepseek/deepseek-flash` with high thinking; its
trusted fallback is `openai-codex/gpt-5.6-luna:high`. The reviewer/security model is
`openai-codex/gpt-6-astra` with no configured fallback. Preserve the other historical
role settings in the private removal backup; do not invent new mappings.
Before delegation, verify the native Paseo model/thinking selection, read-only
review boundary and completion/control path. Removed extension profiles do not
automatically configure Paseo. Missing support is a blocker, not permission to
silently change models or claim that a fallback ran on DeepSeek.
Return accepted findings to the same writer agent and rerun affected checks and
review. Share scoped context, diffs and concise evidence, not full transcripts.
One writer per checkout; children never mutate Plane or integrate branches.
Questions and tiny runtime-setting edits may stay in the parent.
The user removed pi-subagents. Do not reinstall it or use its tools, commands or
packaged workflows; translate packaged delegation guidance to native Paseo only
when the equivalent ownership, isolation and verification requirements are met.

## Bounded shell discovery

- Reuse known project context and resolved paths. Locate rules/configs with exact
  file checks in cwd and its ancestors (including AGENTS.override.md); inspect
  nested rules only along the paths being worked on. Never use recursive `find ..`,
  home-wide or workspace-wide scans for startup discovery. `head` limits output,
  not traversal time. Scope content searches to the relevant repo/subdirectory.
- Run independent diagnostics as separate tool calls (parallel when supported),
  not a semicolon chain sharing one timeout. Batch only cheap exact-path checks.
- Set explicit 2–5 second tool timeouts for cheap local discovery: path/executable
  checks, CLI help, Git metadata and narrow searches. Use task-appropriate budgets
  for builds, tests, indexing, network calls and known expensive operations.
- After a timeout, isolate the slow command and narrow its scope; never retry the
  same command unchanged or simply raise its timeout. Check CLI syntax once when
  unknown, reuse that result, and do not guess flags. On macOS, do not assume GNU
  `timeout` or GNU-only flags are installed; use the tool's timeout parameter.
- Check file type before reading an unknown executable/artifact. Use native read
  for source text, not compiled binaries; use bounded CLI help for executable usage.

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
- Prefer one bounded call over many small ones; each small result stays in the
  context for the rest of the session.
- Measure instead of guessing: `megai report --text` reports turns, prompt tokens
  per turn, reported cost per model, the single-tool-call ratio and estimated
  tool-output replay. Reported cost is not billed cost, and the replay figure is
  an estimate. Do not claim a saving without a comparable before/after measurement.

## User-approved Pi / Paseo routing

Pi is the orchestrator; native Paseo owns child execution, visible Agent tabs,
workspaces, worktrees and terminals. Use one agent tree; Plane remains the tracker.
This placement policy overrides pi-workflow step 3's per-task Paseo requirement;
all other workflow requirements remain in force.

Use a Paseo-managed task worktree when estimated implementation needs
more than 5 minutes AND approximately 1000+ changed source lines (additions plus
deletions, excluding generated/vendor/lockfile churn). Either condition alone is
not the large-change trigger. Explicit user requests or necessary safety isolation
may require Paseo below this threshold. Reassess scope growth at a safe checkpoint;
never replay or abandon unfinished writes merely to switch workspaces.

For smaller work, operate directly in a clean, exclusively owned task checkout;
reuse an existing suitable task workspace rather than creating another. Never
write on a busy/shared checkout or switch someone else's branch. If no safe task
checkout exists, obtain isolated placement first. Non-Git runtime settings can be
edited in place with a private backup and focused verification; do not invent a repo.
Keep Plane tracking and dev/main approval rules unchanged.

Reuse the same Paseo project/task identity. Supply explicit workspace titles and
branch names. Delegate only genuinely independent work, starting with at most two
children, and keep one writer per worktree. Reuse resumable children for refinements;
pass bounded context and return concise evidence, not full transcripts. Use native
completion notifications, never routine polling. Do not create schedules/heartbeats,
restart daemons, enable watchdogs, or alter models/fallbacks without an explicit request.

Launch children in the background, not by navigating the desktop: use
`paseo agent run --background` with an explicit existing task workspace and cwd.
The invoking main tab keeps focus, and that existing workspace owns the created
agent. `run --background` is background execution, not proof that a UI tab
rendered. Never automatically invoke `paseo agent open`, desktop agent deep links,
app/window activation, or a focus-switch-then-restore workaround. If a future
background tab-open API is needed, verify its documented non-focusing behavior first;
never invent flags such as `--no-focus`.
Only an explicit user request may focus a child.

Do not use Pencil unless the user explicitly requests Pencil for the current task.
A generic UI/design request is not permission. This applies to delegated children,
Pencil browser tools and every MCP invocation path. Pencil's Pi lifecycle is lazy;
this avoids startup connection but is not a technical tool-authorization gate.

## End-of-task Agent tab cleanup

When the parent invokes children it records the invoking `PASEO_AGENT_ID` and each exact
child ID with its task workspace/cwd. After acceptance/review and the required delivery
and tracker evidence are saved, but before the final reply, the parent archives only those
recorded task-owned direct children that match its `ParentAgentId` and expected
workspace/cwd, are freshly idle with no pending permission, queued or follow-up work, and
have saved final results: `paseo agent archive EXACT_ID --json` per child, never `--force` -
a soft archive only, not delete, stop or `paseo workspace archive`. Then verify `Archived`
and that the invoking main agent remains unarchived. Never archive the invoking main agent
even when idle, and never sweep all agent tabs or another task's unknown, busy or
unrecorded children; a failed archive is preserved and reported, never forced. Keep a
writer or reviewer tab until parent acceptance/delivery so it can be reused for
refinement; do not close it when its individual turn ends. This is orchestrator policy at
task end, not background daemon automation. The user already authorized cleanup of safe
eligible children: do not ask again.

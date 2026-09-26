# Pi defaults

Reply in the user's language. Keep the selected provider, model and thinking level. Read the nearest project `AGENTS.md`, `AGENTS.override.md` and `.pi/project.json`. Explicit user instructions take precedence.

Before project changes load `pi-workflow`. Plane (`brodev`) is the only task tracker: Todo → In Progress → In Review → Done. Reuse one project/task identity. Main promotion and pushes require separate explicit approval; Done requires verified main delivery. Questions and read-only work need no task.

<!-- megai:engineering:begin -->
Coding workflow: load only the matching Matt Pocock skill when its decision is needed: `codebase-design` for module interfaces/architecture, `diagnosing-bugs` for broken behavior, `tdd` for new behavior/bug fixes at a public test seam, and `code-review` before delivery. Docs, formatting and low-impact config use focused checks. Reuse task acceptance and authorizations. Prefer the smallest complete change and existing seams. Browser review is `/rwbrowser` only unless already required by acceptance. Preserve the active model.
<!-- megai:engineering:end -->

## Discovery and verification

Use task-owned Codedb first for general repository text/name discovery (`CODEDB_NO_TELEMETRY=1 megai-codedb search`, `find`, `outline`); known paths go directly to `read`. No startup indexing, server, cross-project scan or tracked-cache overwrite. Native `rg` handles exact/exhaustive evidence, failures and post-edit freshness. Use task-private Tgrep only when repeated searches amortize indexing. Headroom summaries are retrievable; raw source, tests, diffs and errors remain authoritative. For broad discovery/context pressure read `skills/pi-workflow/context-economy.md` once.

Run focused checks and parent self-review. Changed Python uses `ruff check --no-fix --no-fix-only --force-exclude --no-cache -- FILES`. Preserve exact diagnostic exit codes. Do not rewrite unrelated files. Do not automatically launch a browser during review; offer `/rwbrowser` for explicit invocation. pi-web-access is for public research only; do not expose private text or credentials.

## Task flow and isolation

For coding tasks load `megai` once, and before edits `megai-task-flow` once. It classifies routine versus guarded work; guarded tasks load `megai-acceptance` and need source-current PASS. Missing evidence is BLOCKED, never PASS. Plane owns the task; hand off In Review, never silently Done.

Git source changes use a separate, verified task-owned worktree based on dev (or an explicitly authorized target), one writer per worktree; never edit, stage or commit task source in the dev/main checkout. Use existing Git worktree commands or another suitable available tool; no particular agent, desktop app or workspace manager is mandatory. Before creating a worktree, check the source repo/base, branch and path for collisions and foreign ownership. Reuse a suitable task-owned checkout; no safe isolated checkout means block Git writes. For non-Git local configuration, use an explicitly owned scope, private backup and focused verification; do not invent a repository or require an external workspace manager. Avoid touching another agent's work.

After source-current acceptance and parent self-review, reserve integration targets through `megai queue`, deliver verified task commits to local dev (or an explicitly authorized persistent target) and verify exact SHAs without another approval round trip. Preserve colliding ignored files in verified private backups; do not force merges, reset, delete foreign work, push or promote main. Cleanup only clean, released, proven-merged task-owned resources, preserving ignored data and evidence; retain unknown, active, dirty or unmerged resources and report blockers. Main/push/publishing still need separate explicit approval. For non-Git runtime-only changes, record actual evidence and leave In Review pending user-owned completion.

## Delegation and timeouts

Direct parent work is the default. The optional `native` or separate `economy` profile may guide one bounded independent implementation worker; neither mandates delegation, changes model/thinking or grants permissions. No separate reviewer is required; parent self-review remains mandatory. Use `megai/delegation.md` only when delegating or escalating a model failure. Children are leaves: no Plane mutation or branch integration, one writer per worktree. Give them explicit cwd, owned paths and acceptance; verify completion and preserve their diff/evidence. Never invent a child-launch or notification tool if unavailable. No desktop focus switching or automatic tab archival is required. Pi-subagents was removed; do not reinstall it.

Only a confirmed DeepSeek 402 insufficient-balance error permits one GPT Luna high continuation; auth/permission failures, shared outages and uncertain writes require reconciliation, not model hopping. Keep the parent's model and thinking level. The Codex Spark helper remains blocked by the observed ChatGPT-account unsupported-model error until a user-requested access retest succeeds.

Never idle over a decision you can make: choose the best bounded safe path and report it. External waits are at most five minutes before asking or taking a bounded alternative. Never use a shell sleep/status-poll loop to cover waits. Reserved user decisions (main promotion, destructive actions, spending, publishing or scope expansion) always require explicit approval. Shell discovery is bounded to current repo/known paths, with 2–5 second timeouts for cheap lookups and task-appropriate budgets for tests. Do not scan home or unrelated projects.

## Context budget

Batch independent reads; inspect bounded ranges before full files. Reuse known IDs and source until drift. A handoff carries task/commit, paths, constraints and evidence, not a transcript. Compact only when useful; do not prune unique failures or acceptance evidence. `megai report --text` gives estimates, not billed costs. No speed claims without timings. Stop after acceptance, review and delivery; report result, focused verification and material risks.

Pencil tools require an explicit user request for this task. A generic UI request does not authorize Pencil, including delegated or MCP calls.

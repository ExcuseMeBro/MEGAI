---
name: megai
description: "MEGAI bridge for Oh My Pi — use native memory and code-intelligence MCP tools plus on-demand specialist CLIs."
---

# MEGAI for Oh My Pi

MEGAI wires agent-memory and codedb as native OMP MCP servers. Use their discovered MCP tools instead of shell wrappers for persistent memory and code intelligence.

## When to use

- Save, recall, or search durable context across sessions with agent-memory.
- Search code, locate symbols, inspect outlines, or analyze dependencies with codedb.
- Use `megai-task-flow` when non-trivial work must stay synchronized with Asana and `.todos/`.
- Run specialist CLIs only when the task needs their domain.
- Use `agent-worktree-lifecycle` to fan independent implementation slices out concurrently in registered isolated worktrees from `dev`, integrate verified task branches into `dev`, publish `dev`, open/reuse the `dev` → `main` PR/MR, and clean merged worktrees safely.

## Core tools

### agent-memory

Use the connected agent-memory MCP tools for saving observations, recalling prior decisions, searching sessions, and inspecting memory state. The daemon defaults to `http://127.0.0.1:3111`; run `megai start agent-memory` if the server cannot connect.

### codedb

Use the connected codedb MCP tools for project trees, full-text search, symbol lookup, outlines, dependency analysis, bundles, and snapshots. `megai omp` prepares the current project before launching OMP; run `megai reindex` when the index must be rebuilt.

### smart-router

Use direct LSP, index, search, and exact reads first. Use `smart-router` only when the target is genuinely unknown or repository-wide evidence is required; one empty/conflicting result may escalate once to Luna or Terra.

### minimax-worker

Use `minimax-worker` or `minimax-fast-worker` for implementation, code self-review, and focused tests. OMP already ships the native `minimax-code` catalog and provider transport; MEGAI does not duplicate it. Use GPT specialties only after one focused failure or when the user explicitly asks for architecture, security, deep debugging, or independent review. Ignore provider-share targets while executing.

## Fast execution contract

Inspect the exact seam, implement, self-review the changed code, run focused tests, ship when required, then stop. UI checks are code-only by default; the user owns visual/manual review. Never start automatic planning, review, final-gate, browser, full-suite, queue-drain, or `/loop` work.

## Specialist CLIs

- `dembrandt` — website design extraction.
- `ix` — system maps, traces, and impact analysis.
- `argent` — app and device testing.
- `repowise` — code health, risk, and generated wiki.
- `numasec` — authorized security work only.

Check each CLI's help or status command before use. Do not keep specialist MCP servers active in every session when their CLI is sufficient.

## Paseo agent tabs

When OMP runs inside Paseo, placement depends on write authority:

- Read-only discovery, planning, and review agents are opt-in or failure-driven. In an agent-scoped Paseo session, launch a required read-only worker as a tab in the caller's workspace by calling `create_agent` without `workspaceId`.
- In a top-level context, require exactly one workspace whose `cwd` equals the current `cwd`, then pass that workspace ID to `create_agent` for read-only workers. Ask once on zero or multiple matches.
- Every writing worker MUST receive a visible Paseo-managed worktree workspace. Call `create_workspace` with `isolation: "worktree"`, `mode: "branch-off"`, `baseBranch: "dev"`, and a unique `task/<slug>` branch; then call `create_agent` with that returned `workspaceId`.
- Never launch concurrent writers in the parent workspace. Cross-workspace workers remain attached to the orchestrator's Subagents track and are not detached automatically.
- OMP native `task` isolation is reserved for execution outside Paseo. When Paseo is available, every writer uses a visible Paseo-managed worktree workspace.

At start, use `megai dev` for a clean primary checkout. The parent is the sole integration owner and assigns non-overlapping files. At ship, require clean committed task branches, preview if needed, then run `megai finish --verified --target dev`; complete Asana and `.todos` only after `dev` is pushed, the `dev` → `main` PR/MR exists, and registered-worktree cleanup succeeds. Then call Paseo `archive_workspace` for each successfully merged worker workspace. Never archive the primary `dev` workspace or dirty/unmerged/failed work. Human review or protected CI merges the PR/MR; never auto-merge `main`.

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
- Use `agent-worktree-lifecycle` to integrate verified task worktrees into `dev`, push `dev`, reuse one open `dev` → `main` request, clean merged worktrees, and promote main only after explicit user approval.

## Core tools

### agent-memory

Use the connected agent-memory MCP tools for saving observations, recalling prior decisions, searching sessions, and inspecting memory state. The daemon defaults to `http://127.0.0.1:3111`; run `megai start agent-memory` if the server cannot connect.

### codedb

Use the connected codedb MCP tools for project trees, full-text search, symbol lookup, outlines, dependency analysis, bundles, and snapshots. `megai omp` prepares the current project before launching OMP; run `megai reindex` when the index must be rebuilt.

### smart-router

Use direct LSP, index, search, and exact reads first. Use MiniMax `smart-router` only for read-only search, read, find, symbols, references, callers, and repository-wide evidence; one unresolved lookup may escalate once to Luna or Terra.

### GPT workers

Use `gpt-core-worker` for product/system logic and `gpt-fast-worker` for small edits and focused tests. GPT owns every write, self-review, test change, migration, and refactor. MiniMax never receives write authority or a task worktree.

## Fast execution contract

Inspect with direct tools or MiniMax read-only discovery, then GPT implements, self-reviews, and runs focused tests. Ship when required, then stop. UI checks remain code-only by default; the user owns visual/manual review. Never start automatic gate, full-suite, queue-drain, or `/loop` work.

## Specialist CLIs

- `dembrandt` — website design extraction.
- `ix` — system maps, traces, and impact analysis.
- `argent` — explicit `/argent` app/device review only; never automatic.
- `repowise` — code health, risk, and generated wiki.
- `numasec` — authorized security work only.

Check specialist CLIs only after their activation condition is satisfied. Argent requires `/argent` in the current user message; normal review/test/verify wording is insufficient.

## Paseo agent tabs

When OMP runs inside Paseo, placement depends on write authority:

- Read-only discovery, planning, and review agents are opt-in or failure-driven. In an agent-scoped Paseo session, launch a required read-only worker as a tab in the caller's workspace by calling `create_agent` without `workspaceId`.
- In a top-level context, require exactly one workspace whose `cwd` equals the current `cwd`, then pass that workspace ID to `create_agent` for read-only workers. Ask once on zero or multiple matches.
- Every writing worker MUST receive a visible Paseo-managed worktree workspace. Call `create_workspace` with `isolation: "worktree"`, `mode: "branch-off"`, `baseBranch: "dev"`, and a unique `task/<slug>` branch; then call `create_agent` with that returned `workspaceId`.
- Never launch concurrent writers in the parent workspace. Cross-workspace workers remain attached to the orchestrator's Subagents track and are not detached automatically.
- OMP native `task` isolation is reserved for execution outside Paseo. When Paseo is available, every writer uses a visible Paseo-managed worktree workspace.

At start, use `megai dev` for a clean primary checkout. At ship, run `megai finish --verified --target dev`; complete Asana and `.todos` after `dev` is pushed, one promotion request exists, and registered-worktree cleanup succeeds. Archive only successfully merged worker workspaces. Then ask whether to promote main; run `megai promote --approved` only after an explicit affirmative reply. Never infer approval, enable deferred auto-merge, or archive primary/dirty/unmerged/failed work.

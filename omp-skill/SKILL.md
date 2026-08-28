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

Use the single `smart-router` task agent for non-trivial file location, cross-file search, caller/reference tracing, and read-heavy repository exploration. It handles routine discovery on MiniMax Code M3, escalates an empty/conflicting lookup to its trusted Luna scout, and delegates architecture/data-flow/impact reasoning to Terra. The parent must not duplicate returned reads; it keeps integration and final verification.

### minimax-worker

Use the managed `minimax-worker` for bounded routine implementation after the trusted parent classifies the task. OMP already ships the native `minimax-code` catalog and provider-specific transport/streaming compatibility; MEGAI does not duplicate it. The provider remains unavailable until a rotated `MINIMAX_CODE_API_KEY` is configured outside source. Target roughly 60% MiniMax for exploration/implementation/tests and 40% GPT for planning, architecture, hard debugging, critical review, sensitive domains, and final acceptance. Never weaken HIGH/CRITICAL GPT gates to meet the ratio.

## Specialist CLIs

- `dembrandt` — website design extraction.
- `ix` — system maps, traces, and impact analysis.
- `argent` — app and device testing.
- `repowise` — code health, risk, and generated wiki.
- `numasec` — authorized security work only.

Check each CLI's help or status command before use. Do not keep specialist MCP servers active in every session when their CLI is sufficient.

## Paseo agent tabs

When OMP runs inside Paseo, a request for another agent, subagent, reviewer, parallel worker, or new tab means another session in the current workspace. Use `create_agent` in the caller's workspace; do not create a workspace first. `create_workspace` is reserved for an explicit request for a new workspace, worktree, isolated branch, or PR checkout.

At start, use `megai dev` for a clean primary checkout. For two or more independent implementation slices, use one task batch with `isolated: true` on every writing item; one writer owns each non-overlapping file set, while the parent is the sole integration owner. Branch every isolated task from the same `dev` baseline and keep OMP isolation in branch-merge mode. At ship, require clean committed task branches, preview if needed, then run `megai finish --verified --target dev`; complete Asana and `.todos` only after `dev` is pushed, the `dev` → `main` PR/MR exists, and registered-worktree cleanup succeeds. Then call Paseo `archive_workspace` for each successfully merged worker workspace. Never archive the primary `dev` workspace or dirty/unmerged/failed work. Human review or protected CI merges the PR/MR; never auto-merge `main`.

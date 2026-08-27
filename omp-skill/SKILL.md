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

## Core tools

### agent-memory

Use the connected agent-memory MCP tools for saving observations, recalling prior decisions, searching sessions, and inspecting memory state. The daemon defaults to `http://127.0.0.1:3111`; run `megai start agent-memory` if the server cannot connect.

### codedb

Use the connected codedb MCP tools for project trees, full-text search, symbol lookup, outlines, dependency analysis, bundles, and snapshots. `megai omp` prepares the current project before launching OMP; run `megai reindex` when the index must be rebuilt.

## Specialist CLIs

- `dembrandt` — website design extraction.
- `ix` — system maps, traces, and impact analysis.
- `argent` — app and device testing.
- `repowise` — code health, risk, and generated wiki.
- `numasec` — authorized security work only.

Check each CLI's help or status command before use. Do not keep specialist MCP servers active in every session when their CLI is sufficient.

## Paseo agent tabs

When OMP runs inside Paseo, a request for another agent, subagent, reviewer, parallel worker, or new tab means another session in the current workspace. Use `create_agent` in the caller's workspace; do not create a workspace first. `create_workspace` is reserved for an explicit request for a new workspace, worktree, isolated branch, or PR checkout.

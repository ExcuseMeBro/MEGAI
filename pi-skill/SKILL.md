---
name: megai
description: MEGAI slim code lookup, explicit persistent memory, task-appropriate skills, and non-mutating Python verification.
managed-by: megai
---

# MEGAI slim

## Find and change code

Use `rg` for exact symbols/text and native reads/edits. When location or wording is unknown, use local `zg query "intent"` or `zg query --fts "symbol"`, then read the relevant ranges. Ground impact claims in code/references, not search snippets alone. Review the diff and verify observable task acceptance; fewer tools do not justify weaker tests, thinking, trust or review.

`megai reindex` explicitly initializes/rebuilds the local zvec index. Startup never prewarms it. Remote embedding requires separate explicit authorization; preserve existing index configuration/data.

## Persistent memory

Start only when needed: `megai start agent-memory`. Use `megai-memory recall "decision"` for relevant prior decisions and `megai-memory save "decision"` only when persistence is requested. Keep secrets and personal data out of memory. HTTP calls have bounded connection/total timeouts; unavailable memory is not authority to invent context.

## Task-specific skills and verification

Use the requested Matt Pocock engineering skill or plugin87 UI/UX skill only when the task matches; load the body on demand, not entire kits or review chains. UX work retains accessibility semantics and task-relevant tests. For security/data-integrity risks or consequential cross-module changes, get fresh independent review. Visual/app testing is explicit-only.

For task-changed Python files, run `ruff check --no-fix --no-fix-only --force-exclude --no-cache -- <files>`. When repository formatting matches Ruff, also run `ruff format --check --force-exclude --no-cache -- <files>`. Keep project configuration and unrelated files untouched; never write `pyproject.toml` for this check. Never pass `--fix`; `--no-fix-only` also protects projects with `fix-only = true`. No automatic fixes or broad cleanup.

`rtk` is a command-output helper, not a quality gate. Use raw output for failing diagnostics or whenever compression might hide acceptance evidence. Follow repository test commands and preserve their exit status.

The parent uses `megai-task-flow` for Plane-only boundaries and `agent-worktree-lifecycle` for isolated writes and agreed branch delivery. Preserve provider/model/thinking/auth, user configuration and existing data. Report measured evidence and gaps; resource counts alone do not prove speed or quality.

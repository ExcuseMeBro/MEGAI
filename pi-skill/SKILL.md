---
name: megai
description: Default slim coding workflow with codedb structural lookup, zvec intent search, RTK discovery output, Caveman chat, and acceptance-first verification.
managed-by: megai
---

# MEGAI slim

## Default execution contract

Before edits, state the requested outcome, observable acceptance checks and stop condition. Load `caveman` once for full concise chat in the user's language, unless the user opts out. Persisted artifacts remain normal prose; preserve uncertainty, warnings and required task checkpoints.

Use the defaults below when their purpose matches the task. Do not run all tools on every task, repeat known lookups or build indexes merely to prove activation. Task acceptance and code quality outrank compression: keep security, accessibility, compatibility, error handling, required tests and independent review. Preserve provider/model/thinking choices. Report a missing tool or stale index honestly and use a stated native fallback.

## Find and change code

Codedb is default core structural lookup: use `megai-codedb symbol NAME`, `megai-codedb outline FILE`, and `megai-codedb tree PATH` when relevant. Index only when the task needs it (`megai-codedb index PATH`); never prewarm on startup. Preserve existing index data. Use `rg` for exact text or unsupported-language fallback and native reads/edits. When location or wording is unknown, use local `zg query "intent"` or `zg query --fts "symbol"`, then read the relevant ranges. Ground impact claims in code/references, not search snippets alone. Review the diff and verify observable task acceptance; fewer tools do not justify weaker tests, thinking, trust or review.

`megai reindex` explicitly initializes/rebuilds the local zvec index. Startup never prewarms it. Remote embedding requires separate explicit authorization; preserve existing index configuration/data.

## Persistent memory

When prior decisions may affect the task, start the configured local service with `megai start agent-memory`, then use `megai-memory recall "decision"`. This relevant recall is a default workflow step, without a separate enablement request; skip it when no prior context is needed. Startup remains lazy, not a service launched with every harness. Respect existing process/port ownership and report a start failure rather than killing an unrelated process.

Use `megai-memory save "decision"` only when the user requests persistence; default activation never authorizes automatic saving. Keep secrets and personal data out of memory. HTTP calls have bounded connection/total timeouts; unavailable memory is not authority to invent context.

## Task-specific skills and verification

Select and load the matching Matt Pocock engineering skill by default for implementation, diagnosis, design or verification. For UI work, select the matching plugin87 UI/UX skill, including accessibility guidance. No separate enablement request is needed; load only the matching bodies on demand, not entire kits or review chains. UX work retains accessibility semantics and task-relevant tests. For security/data-integrity risks or consequential cross-module changes, get fresh independent review. Visual/app testing is explicit-only.

For task-changed Python files, run Ruff by default: `ruff check --no-fix --no-fix-only --force-exclude --no-cache -- <files>`. When repository formatting matches Ruff, also run `ruff format --check --force-exclude --no-cache -- <files>`. Keep project configuration and unrelated files untouched; never write `pyproject.toml` for this check. Never pass `--fix`; `--no-fix-only` also protects projects with `fix-only = true`. No automatic fixes or broad cleanup.

## RTK by default; raw acceptance evidence

For supported discovery output, prefer `rtk git status`, `rtk git log -5`, and `rtk ls` over their verbose equivalents. This is the default agent command policy across harnesses, not shell-wide interception or a tool-call rewrite hook. Unsupported commands, scripts, shell pipelines and quoted/compound commands remain native; do not rewrite their semantics to use RTK.

Run repository tests, lint, typecheck and build commands exactly as specified, with raw output and their original exit status. Inspect full native `git diff` for review. Never accept a task from an RTK summary alone; capture the raw failure from the original run rather than automatically rerunning a potentially mutating command. Use compression only when it cannot conceal acceptance evidence. Fewer output characters or installed tools alone do not establish better speed or code quality.

The parent uses `megai-task-flow` for Plane-only boundaries and `agent-worktree-lifecycle` for isolated writes and agreed branch delivery. Preserve provider/model/thinking/auth, user configuration and existing data. Report measured evidence and gaps; resource counts alone do not prove speed or quality.

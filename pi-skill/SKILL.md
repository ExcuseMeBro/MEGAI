---
name: megai
description: MEGAI slim GPT-only Pi delegation, code lookup, explicit persistent memory, task-appropriate skills, and non-mutating Python verification.
managed-by: megai
---

# MEGAI slim

When the retained core `caveman` skill is enabled, default to its full chat style unless the user requests normal mode. Preserve the user's language, technical meaning, uncertainty and safety warnings; persisted artifacts, tests and authorization gates remain unchanged. Caveman companions and workflow bundles are not part of this core policy.

## GPT-only Pi delegation

Parents, subagents and reviewers use the Pi harness with this role map:

| Role | Pi model ID | Thinking |
| --- | --- | --- |
| Parent/orchestrator | `openai-codex/gpt-6-astra` | high |
| Discovery/research | `openai-codex/gpt-5.6-luna` | medium |
| Scoped implementation | `openai-codex/gpt-5.6-luna` | high |
| Independent review, complex debugging or fallback | `openai-codex/gpt-5.6-sol` | high |

Use direct parent tools for bounded work; delegate only when isolation or independent evidence earns the overhead. Children never delegate, mutate Plane or integrate branches. Writers use separate managed worktrees under `agent-worktree-lifecycle`; a delegated writer replaces parent writing rather than duplicating it.

Create visible Paseo children explicitly, for example `paseo run --background --provider pi --model openai-codex/gpt-5.6-luna --thinking high`, or `create_agent` with `provider: "pi/openai-codex/gpt-5.6-luna"` and `settings: {thinkingOptionId: "high"}`. Select the role's exact model/thinking, not an inherited default. The `openai-codex/` namespace is a model provider inside Pi, not permission to use the Codex harness.

Use a neutral preflight prompt when creation immediately starts a run. Verify the returned harness is `pi` and the model/thinking match the requested role before sending task context; inspect agent metadata if creation omits these fields. On mismatch, cancel the child and report the blocker. If Pi, the selected GPT model or verifiable identity is unavailable, use direct parent tools only when safe or stop; no non-GPT or non-Pi fallback. Never send secrets or private context to an unverified route.

Give each child only its scope, authority, relevant evidence and acceptance checks. Use completion notifications rather than polling. Allow at most one diagnosed transient retry or one focused correction; if still blocked, escalate once to Sol/high or report the blocker, without a model-switch loop. Security/data-integrity risks require fresh independent Sol/high review. Preserve required tests and authorization gates regardless of model.

This is the delegation policy, not a provider-catalog rewrite or runtime sandbox. Do not change credentials, provider endpoints, user settings or install another harness to satisfy it. These are operational choices, not a universal model-quality or performance claim.

## Find and change code

Codedb is default core structural lookup: use `megai-codedb symbol NAME`, `megai-codedb outline FILE`, and `megai-codedb tree PATH` when relevant. Index only when the task needs it (`megai-codedb index PATH`); never prewarm on startup. Preserve existing index data. Use `rg` for exact text or unsupported-language fallback and native reads/edits. When location or wording is unknown, use local `zg query "intent"` or `zg query --fts "symbol"`, then read the relevant ranges. Ground impact claims in code/references, not search snippets alone. Review the diff and verify observable task acceptance; fewer tools do not justify weaker tests, thinking, trust or review.

`megai reindex` explicitly initializes/rebuilds the local zvec index. Startup never prewarms it. Remote embedding requires separate explicit authorization; preserve existing index configuration/data.

## Persistent memory

Start only when needed: `megai start agent-memory`. Use `megai-memory recall "decision"` for relevant prior decisions and `megai-memory save "decision"` only when persistence is requested. Keep secrets and personal data out of memory. HTTP calls have bounded connection/total timeouts; unavailable memory is not authority to invent context.

## Task-specific skills and verification

Use the requested Matt Pocock engineering skill or plugin87 UI/UX skill only when the task matches; load the body on demand, not entire kits or review chains. UX work retains accessibility semantics and task-relevant tests. For security/data-integrity risks or consequential cross-module changes, get fresh independent review. Visual/app testing is explicit-only.

For task-changed Python files, run `ruff check --no-fix --no-fix-only --force-exclude --no-cache -- <files>`. When repository formatting matches Ruff, also run `ruff format --check --force-exclude --no-cache -- <files>`. Keep project configuration and unrelated files untouched; never write `pyproject.toml` for this check. Never pass `--fix`; `--no-fix-only` also protects projects with `fix-only = true`. No automatic fixes or broad cleanup.

`rtk` is a command-output helper, not a quality gate. Use raw output for failing diagnostics or whenever compression might hide acceptance evidence. Follow repository test commands and preserve their exit status.

The parent uses `megai-task-flow` for Plane-only boundaries and `agent-worktree-lifecycle` for isolated writes and agreed branch delivery. Preserve provider/model/thinking/auth, user configuration and existing data. Report measured evidence and gaps; resource counts alone do not prove speed or quality.

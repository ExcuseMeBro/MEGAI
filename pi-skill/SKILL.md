---
name: megai
description: Default Pi-only coding workflow with local Headroom compression and memory, tgrep text discovery, codedb structural lookup, zvec intent search, and acceptance-first verification.
managed-by: megai
---

# MEGAI slim

## Default execution contract

Before edits, state the requested outcome, observable acceptance checks and stop condition. Headroom supplies concise output guidance in the user's language without reducing thinking. Respect explicit detail and normal-mode requests. Persisted artifacts remain normal prose; preserve uncertainty, warnings and required task checkpoints.

Use the defaults below when their purpose matches the task. Do not run all tools on every task, repeat known lookups or build indexes merely to prove activation. Task acceptance and code quality outrank compression: keep security, accessibility, compatibility, error handling, required tests and independent review. Preserve provider/model/thinking choices. Report a missing tool or stale index honestly and use a stated native fallback.

## Pi-only delegation

Parents, reviewers, scouts and workers all run through the **Pi harness**. This overrides any task skill's generic harness examples. Use direct tools for bounded work; if delegation is necessary, use visible Paseo agents. Create isolated writer workspaces first; read-only children may share the caller workspace.

Select the harness explicitly: CLI `paseo run --background --provider pi --model openai-codex/<model> --thinking <medium-or-high>`, or Paseo `create_agent` with `provider: "pi/openai-codex/<model>"` and explicit thinking. Keep the approved task-appropriate model. Confirm the returned harness is `pi` and the model/thinking match before sending proprietary task context. On mismatch, interrupt the new child and report it; do not continue or relabel it. There is no non-Pi fallback: if Pi cannot run, use direct parent tools when safe or stop with a blocker.

`openai-codex/...` is a model-provider namespace **inside Pi**, not permission to select Paseo's `codex` harness or spawn the Codex CLI. Do not launch other harnesses through bash, native subagents, scripts or skill examples. Children never delegate, mutate Plane or integrate branches. Use `agent-worktree-lifecycle` for checkout and delivery rules.

## Find and change code

Tgrep is the default for literal/regex discovery. Before text search, read [tgrep.md](tgrep.md) for on-demand indexing, readiness and freshness rules. Use `rg` when the index is partial, freshness is uncertain, or native semantics are required. This is agent policy, not a shell alias or interception of tests/tools.

Codedb is default core structural lookup: use `megai-codedb symbol NAME`, `megai-codedb outline FILE`, and `megai-codedb tree PATH` when relevant. Index only when the task needs it (`megai-codedb index PATH`); never prewarm on startup. Preserve existing index data. Use tgrep for text discovery and native reads/edits; use the documented `rg` fallback when needed. When location or wording is unknown, use local `zg query "intent"` or `zg query --fts "symbol"`, then read the relevant ranges. Ground impact claims in code/references, not search snippets alone. Review the diff and verify observable task acceptance; fewer tools do not justify weaker tests, thinking, trust or review.

`megai reindex` explicitly initializes/rebuilds the local zvec index. Startup never prewarms it. Remote embedding requires separate explicit authorization; preserve existing index configuration/data.

## Persistent memory

When prior decisions may affect the task, use `headroom_memory` with action `recall`, or `megai headroom recall "decision"`. This relevant recall is a default workflow step, without a separate enablement request; skip it when no prior context is needed. Memory is local, persistent and scoped to the repository, shared with its Git worktrees. No daemon or remote embedding runs.

Use `headroom_memory` with action `save`, or `megai headroom save "decision"`, only when the user requests persistence; default activation never authorizes automatic saving. Keep secrets and personal data out of memory. Unavailable memory is not authority to invent context. Runtime calls are bounded; report failures and use current repository evidence.

## Task-specific skills and verification

Select and load the matching Matt Pocock engineering skill by default for implementation, diagnosis, design or verification. For UI work, select the matching plugin87 UI/UX skill, including accessibility guidance. No separate enablement request is needed; load only the matching bodies on demand, not entire kits or review chains. UX work retains accessibility semantics and task-relevant tests. For security/data-integrity risks or consequential cross-module changes, get fresh independent review. Visual/app testing is explicit-only.

For task-changed Python files, run Ruff by default: `ruff check --no-fix --no-fix-only --force-exclude --no-cache -- <files>`. When repository formatting matches Ruff, also run `ruff format --check --force-exclude --no-cache -- <files>`. Keep project configuration and unrelated files untouched; never write `pyproject.toml` for this check. Never pass `--fix`; `--no-fix-only` also protects projects with `fix-only = true`. No automatic fixes or broad cleanup.

## Headroom compression; raw acceptance evidence

Use native commands. The Pi Headroom extension compresses eligible successful discovery output on demand before the model receives it, while preserving original session messages. File reads, edits, writes, test/build/lint output, error results and full diffs remain raw. Compression failure visibly falls back to the original; auth, provider, model and thinking stay unchanged.

Use `headroom_retrieve` and paginate with `next_offset` whenever exact content or omitted detail matters. Local compression originals expire after seven days; persistent memories do not. Native session/source remains authoritative. `MEGAI_HEADROOM=0` disables automatic compression and terse guidance; `/headroom-verbosity 0` or `normal mode` disables terse guidance only.

Run repository tests, lint, typecheck and build commands exactly as specified, with raw output and their original exit status. Inspect full native `git diff` for review. Never accept a task from a compressed summary alone; capture the raw failure from the original run rather than automatically rerunning a potentially mutating command. Use compression only when it cannot conceal acceptance evidence. Fewer output characters or installed tools alone do not establish better speed or code quality.

The parent uses `megai-task-flow` for Plane-only boundaries and `agent-worktree-lifecycle` for isolated writes and agreed branch delivery. Preserve provider/model/thinking/auth, user configuration and existing data. Report measured evidence and gaps; resource counts alone do not prove speed or quality.

---
name: megai
description: "MEGAI core for Pi: code lookup, explicit persistent memory, and non-mutating Python checks with Ruff."
---

# MEGAI core for Pi

Use native read/edit/write/bash and the repository's own tests. Locate relevant symbols before reading files; avoid repeated scans and unchanged documentation reads.

## Code lookup

Use `rg` for exact text. When available, `megai-codedb symbol NAME`, `megai-codedb outline FILE`, and `megai-codedb tree PATH` provide structural lookup. Unsupported languages or missing definitions fall back to native tools.

For semantic discovery use `zg query "question"` or the lazy `zvec_grep` MCP. `zg status --check-ready` verifies readiness; a stale or absent index is not a successful search. Do not build an index for a tiny task when `rg` suffices. Build one only when the task needs it, with the local embedding model; remote embeddings require explicit approval.

`megai pi` skips automatic memory/index startup. `MEGAI_PI_FULL=1 megai pi` restores core preparation; graphify remains separately opt-in. Existing indexes/data are retained.

## Persistent memory — explicit only

Use `megai-memory recall "query"` or `megai-memory save "observation"` only for requested cross-session memory. If unavailable, report it; do not start a daemon for ordinary coding. `megai start agent-memory` starts the local service when needed.

## Ruff — Python validation

Prefer the project's pinned tool and existing lint/test commands. Check only task-changed, existing `.py`/`.pyi` files; honor exclusions and skip generated/vendor/cache files. Never perform project-wide cleanup; never write `pyproject.toml`, `ruff.toml`, or `.ruff.toml` to make a check pass.

```bash
ruff check --no-fix --no-fix-only --force-exclude --no-cache -- <changed files>
```

Both disabling flags are required: project `fix = true` or `fix-only = true` can otherwise cause writes. `--no-cache` avoids creating Ruff cache files.

Only when the project already uses Ruff formatting or requests it:

```bash
ruff format --check --force-exclude --no-cache -- <changed files>
```

Never pass `--fix` or run bare formatting from this skill. Report findings, preserve source bytes and run the task's tests. If Ruff is unavailable, report the missing check rather than installing tools during validation.

External specialist tools are not startup dependencies. App/device review requires explicit user authorization. Task tracking, worktree safety, review requirements and main-approval boundaries remain mandatory.

---
name: megai
description: "MEGAI bridge for Pi — memory, hybrid workspace search, code intelligence, code health, read-only Python validation with Ruff, and explicit /argent-only app testing."
---

# MEGAI for Pi

This skill exposes agent-memory and codedb through CLI bridges on PATH and zvec-grep through a global Pi MCP entry. Argent is stricter than other specialists: run it only when the current user message explicitly invokes `/argent`.

## When to use

- User asks to remember / save / recall context across sessions
- User asks to search code or documents by meaning, find symbols, list files, or view dependencies
- User mentions "memory", "context", "codebase map", "find function X"
- User asks to extract a website's design tokens, palette, typography, spacing, brand identity, or WCAG findings
- User asks to explain architecture, trace a flow, or analyze change impact: combine structural lookups with targeted file reads; verify inferred connections in code.
- User asks about code health, refactoring targets, commit risk, generated docs, or architectural decisions
- User asks to test, inspect, automate, record, profile, or reproduce behavior in an iOS, Android, TV, Electron, or Chromium app

## Tools

### `megai-memory` — persistent memory (agent-memory.dev)

| Sub | Usage |
| ----- | ------- |
| `save <text>` | Store an observation |
| `recall <query>` | Smart-search memories |
| `sessions` | List session IDs |
| `stats` | Memory store stats |

### `zvec_grep_search` — semantic and hybrid workspace search

Use zvec-grep first when the wording or location is unknown, or when the answer requires fuzzy, semantic, or cross-file discovery. Use native `rg` for known exact text and `megai-codedb` for definitions, outlines, callers, and dependency structure. MEGAI creates the local index with `local/potion-code-16m-v2` on first project activation.

### `megai-codedb` — structural code intelligence (justrach/codedb)

| Sub | Usage |
| ----- | ------- |
| `tree [path]` | File tree |
| `search <pattern>` | Full-text search |
| `symbol <name>` | Find symbol definitions |
| `outline <file>` | Symbols inside a file |
| `find <name>` | Locate file/symbol |

### Dembrandt — website design extraction

Run Dembrandt only for website-design extraction:

```bash
dembrandt example.com --design-md
```

### Local code workflow

Use codedb for structure, zvec-grep for semantic/hybrid discovery, and `rg` for exact text or as a fallback. Read only the relevant ranges with native file tools, edit with exact replacements, then verify the diff and affected behavior. Keep native read/edit tools available; no paid toolchain or replacement daemon is required.

### Ruff — Python lint and format validation (non-mutating)

Run Ruff only for non-mutating Python validation. Prefer the project's pinned tool/config when one exists; never run project-wide cleanup and never write `pyproject.toml`, `ruff.toml`, or `.ruff.toml`. Target only `.py`/`.pyi` files the current task changed, and skip excluded/generated files (anything `ruff` would skip via its own config plus vendored, generated, and cache directories).

A project may set `[tool.ruff] fix = true` or `fix-only = true`; the canonical non-mutating check therefore pins both flags off and forces excludes:

```bash
ruff check --no-fix --no-fix-only --force-exclude --no-cache -- <changed .py/.pyi files>
```

`--no-fix-only` is mandatory: with project `fix-only = true`, `ruff check --no-fix --force-exclude --no-cache -- <files>` still rewrites the file. `--no-cache` keeps results reproducible across runs.

Run the format check only when the project's formatting style fits Ruff conventions (the user's project docs/config ask for it, or the repo already uses Ruff for formatting). Use the same non-mutating shape, with `--check`:

```bash
ruff format --check --force-exclude --no-cache -- <changed .py/.pyi files>
```

Never pass `--fix` or run `ruff format` without `--check` from this skill: surface findings as guidance instead. Preserve the task's own tests; do not add Ruff tests or hooks.

If `ruff` is not installed locally, skip the check rather than installing or modifying the environment.

### Argent — agent-driven app testing

Run Argent only after explicit `/argent`. Normal review, test, UI, device, or verification requests do not authorize it. Then inspect available tools and server state with:

```bash
argent tools
argent server status
```

### RepoWise — code health and generated wiki

Run RepoWise only for code-health, risk, or generated-wiki tasks:

```bash
repowise health
repowise risk main..HEAD
repowise serve
```

## Examples

```bash
megai-memory recall "auth middleware decisions"
megai-memory save "User prefers TIMESTAMPTZ for all datetime columns"
zg query "where authentication is validated"
megai-codedb search "TODO"
megai-codedb symbol handleLogin
megai-codedb tree src/
rg -n 'auth-service' src/
```

## Gotchas

- **agent-memory daemon must be running.** The CLI bridge talks to `http://127.0.0.1:<port>` (default 3111). Run `megai start agent-memory` if recall returns connection refused.
- **zvec-grep needs a workspace index.** Run `megai` in the repository root or `zg index --embedding local/potion-code-16m-v2`. Remote Embedding is never authorized automatically.
- **codedb is stdio-first.** This bridge uses its CLI mode, not MCP. Some advanced features (bundle, snapshot) are MCP-only and not exposed here yet.
- **Dembrandt needs a browser.** Run `dembrandt install-browser` if extraction reports that Chromium is unavailable.
- **Argent needs platform SDKs.** Apple targets require Xcode; Android targets require `adb`; Fire TV/Vega requires the Vega SDK. Electron and Chromium use CDP.
- **RepoWise is on demand.** In the chosen Git repository, run `repowise init --yes --no-prose --no-claude-md` before its first health/wiki query. MEGAI does not start specialist indexes by default.
- **Automatic indexing happens through MEGAI.** Launch with `megai pi` so codedb and zvec-grep indexes are prepared before Pi starts.
- **Ruff validation is non-mutating and scoped.** Run only on task-changed `.py`/`.pyi` files with `--no-fix --no-fix-only --force-exclude --no-cache`. Project config may set `fix = true` or `fix-only = true`; both flags are required to suppress auto-fix. Never write `pyproject.toml` or run `--fix` from this skill.

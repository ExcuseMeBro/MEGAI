---
name: megai
description: "MEGAI bridge for Pi — access persistent agent memory and code intelligence. Use when the user asks to recall context, search past sessions, save memories, or query code structure (symbols, files, dependencies)."
---

# MEGAI for Pi

Pi has no native MCP. This skill exposes MEGAI tools (agent-memory + codedb) through shell extensions.

## When to use

- User asks to remember / save / recall context across sessions
- User asks to search code, find symbols, list files, view dependencies
- User mentions "memory", "context", "codebase map", "find function X"

## Tools

### `megai-memory` — persistent memory (agent-memory.dev)

| Sub | Usage |
|-----|-------|
| `save <text>` | Store an observation |
| `recall <query>` | Smart-search memories |
| `sessions` | List session IDs |
| `stats` | Memory store stats |

### `megai-codedb` — code intelligence (justrach/codedb)

| Sub | Usage |
|-----|-------|
| `tree [path]` | File tree |
| `search <pattern>` | Full-text search |
| `symbol <name>` | Find symbol definitions |
| `outline <file>` | Symbols inside a file |
| `find <name>` | Locate file/symbol |

## Examples

```bash
megai-memory recall "auth middleware decisions"
megai-memory save "User prefers TIMESTAMPTZ for all datetime columns"
megai-codedb search "TODO"
megai-codedb symbol handleLogin
megai-codedb tree src/
```

## Gotchas

- **agent-memory daemon must be running.** Extension talks to `http://127.0.0.1:<port>` (default 3111). Run `megai start agent-memory` if recall returns connection refused.
- **codedb is stdio-first.** This bridge uses its CLI mode, not MCP. Some advanced features (bundle, snapshot) are MCP-only and not exposed here yet.
- **No automatic indexing.** Pi opens a project but codedb needs `codedb index <path>` first time per repo. Run it once before searching.

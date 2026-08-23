---
name: megai
description: "MEGAI bridge for Pi — access persistent memory, code intelligence, system maps, code health, generated wikis, website design extraction, and agent-driven app testing."
---

# MEGAI for Pi

This skill exposes agent-memory and codedb through shell extensions, Dembrandt, Argent, and RepoWise through Pi MCP Adapter, and Ix through its CLI.

## When to use

- User asks to remember / save / recall context across sessions
- User asks to search code, find symbols, list files, view dependencies
- User mentions "memory", "context", "codebase map", "find function X"
- User asks to extract a website's design tokens, palette, typography, spacing, brand identity, or WCAG findings
- User asks to map architecture, explain a component, trace a flow, or analyze change impact
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

### `megai-codedb` — code intelligence (justrach/codedb)

| Sub | Usage |
| ----- | ------- |
| `tree [path]` | File tree |
| `search <pattern>` | Full-text search |
| `symbol <name>` | Find symbol definitions |
| `outline <file>` | Symbols inside a file |
| `find <name>` | Locate file/symbol |

### Dembrandt — website design extraction

Use the `mcp` proxy to find and call Dembrandt tools such as `get_design_tokens`, `get_color_palette`, `get_typography`, and `get_brand_identity`. For direct CLI use:

```bash
dembrandt example.com --design-md
```

### Ix — persistent system map

| Command | Usage |
| --------- | ------- |
| `ix map .` | Build or refresh the project map |
| `ix explain <target>` | Explain a component or subsystem |
| `ix trace <flow>` | Trace an execution flow |
| `ix impact <target>` | Analyze change blast radius |

### Argent — agent-driven app testing

Use the `mcp` proxy to find and call Argent tools for device control, gestures, screenshots, recording/replay, visual regression, logs, network inspection, and profiling. The CLI can inspect available tools and server state:

```bash
argent tools
argent server status
```

### RepoWise — code health and generated wiki

Use the `mcp` proxy for task-shaped RepoWise tools such as `get_overview`, `get_context`, `get_risk`, and `get_why`. Direct CLI commands:

```bash
repowise health
repowise risk main..HEAD
repowise serve
```

## Examples

```bash
megai-memory recall "auth middleware decisions"
megai-memory save "User prefers TIMESTAMPTZ for all datetime columns"
megai-codedb search "TODO"
megai-codedb symbol handleLogin
megai-codedb tree src/
ix impact auth-service
```

## Gotchas

- **agent-memory daemon must be running.** Extension talks to `http://127.0.0.1:<port>` (default 3111). Run `megai start agent-memory` if recall returns connection refused.
- **codedb is stdio-first.** This bridge uses its CLI mode, not MCP. Some advanced features (bundle, snapshot) are MCP-only and not exposed here yet.
- **Dembrandt needs a browser.** Run `dembrandt install-browser` if extraction reports that Chromium is unavailable.
- **Ix needs its local backend.** Run `ix status`; re-run `megai install` if ports 8090/8529 are unavailable.
- **Argent needs platform SDKs.** Apple targets require Xcode; Android targets require `adb`; Fire TV/Vega requires the Vega SDK. Electron and Chromium use CDP.
- **RepoWise needs a completed local index.** Check `.repowise/state.json` or `megai logs repowise` after first activation.
- **No automatic indexing.** Pi opens a project but codedb needs `codedb index <path>` first time per repo. Run it once before searching.

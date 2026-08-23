<!-- logo -->
<pre align="center">
███╗   ███╗███████╗ ██████╗  █████╗ ██╗
████╗ ████║██╔════╝██╔════╝ ██╔══██╗██║
██╔████╔██║█████╗  ██║  ███╗███████║██║
██║╚██╔╝██║██╔══╝  ██║   ██║██╔══██║██║
██║ ╚═╝ ██║███████╗╚██████╔╝██║  ██║██║
╚═╝     ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝

  THE ZERO-CONFIG AI AGENT STACK
</pre>

<p align="center">
  <a href="https://github.com/ExcuseMeBro/MEGAI/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/install-one--line-brightgreen.svg" alt="One-line install">
  <img src="https://img.shields.io/badge/harnesses-Claude%20Code%20%7C%20Codex%20%7C%20Pi-8A2BE2.svg" alt="Harnesses">
  <img src="https://img.shields.io/badge/tools-14-orange.svg" alt="Tools">
</p>

<p align="center">
  <b>One command. Fourteen tools. Three agent harnesses. Zero config.</b><br>
  Memory · code intelligence · indexing · token compression · knowledge graphs · task flow · design extraction · app testing — wired in and ready.
</p>

# MEGAI

Zero-config one-line installer for the AI agent stack: **agent-memory** + **codedb** + **cocoindex** + **caveman** + **rtk** + **graphify** + **task-flow** + **ui-craft** + **ux-ui-agent-skills** + **Dembrandt** + **Ix** + **RepoWise** + **Argent** + **Matt Pocock's skills**, auto-wired into **Claude Code**, **Codex**, and **Pi**.

```bash
curl -fsSL https://raw.githubusercontent.com/ExcuseMeBro/MEGAI/main/install.sh | bash
```

After install:

```bash
megai status
megai doctor
```

---

## What you get

| Tool | Role |
| ------ | ------ |
| [agent-memory](https://www.agent-memory.dev/) | Persistent memory MCP server (53 tools, port 3111) |
| [codedb](https://github.com/justrach/codedb) | Code intelligence MCP server (16 tools, Zig binary) |
| [cocoindex](https://cocoindex.io) | Incremental indexing pipeline (Python) |
| [caveman](https://github.com/JuliusBrussee/caveman) | Token-compression skill (~65% savings, auto-activates in cc/codex/pi) |
| [rtk](https://github.com/rtk-ai/rtk) | Rust Token Killer — CLI output proxy (~60–90% savings, hooks into cc) |
| [graphify](https://graphify.net) | Knowledge-graph skill for codebases (Tree-sitter + NetworkX + Leiden). `/graphify .` inside cc/codex/pi |
| task-flow | Priority-driven `.todos` board + full-ADLC protocol for Claude Code; Pi also mirrors project tasks and status to Asana |
| [ui-craft](https://skills.smoothui.dev) | Design-system skill + MCP gates + review agents for AI harnesses. Anti-slop UI rules, design memory, and per-project tokens. `/ui-craft` inside cc/codex/cursor/gemini/opencode |
| [ux-ui-agent-skills](https://github.com/plugin87/ux-ui-agent-skills) | 17 global design skills plus tokens, components, WCAG references, framework adapters, and 138 design-system profiles |
| [Dembrandt](https://github.com/dembrandt/dembrandt) | Extracts live websites into design tokens, palettes, typography, WCAG findings, reports, and `DESIGN.md`; available as CLI and MCP |
| [Ix](https://github.com/ix-infrastructure/Ix) | Persistent system map and codebase memory: map architecture, explain components, trace flows, and analyze change impact |
| [RepoWise](https://github.com/repowise-dev/repowise) | Local code intelligence: dependency graph, generated wiki, git history, architectural decisions, code health, risk analysis, and ten MCP tools |
| [Argent](https://github.com/software-mansion/argent) | Agent-driven testing for iOS, Android, TV, Electron, and Chromium apps: device control, recording, visual regression, logs, network inspection, and profiling via CLI and MCP |
| [Matt Pocock's skills](https://github.com/mattpocock/skills) | 22 promoted engineering/productivity skills: grilling, specs, tickets, TDD, review, domain modeling, and more |

**Wired into:**

- **Claude Code** — agent-memory, codedb, Dembrandt, Argent, and RepoWise MCP servers added to `~/.claude.json`; Ix's official `ix-memory` plugin installed; `rtk` PreToolUse hook registered; `caveman` + `graphify` skills auto-detected; `task-flow` skill + `.todos` board hook + board statusline installed; `ui-craft` skill + commands + MCP gates + design-memory written to `~/.claude/`
- **Codex** — agent-memory, codedb, Dembrandt, Argent, and RepoWise MCP block added to `~/.codex/config.toml` (markered, idempotent); Ix's official plugin, hooks, and MCP installed; `caveman` + `graphify` register themselves; `ui-craft` writes its skill + gates into the Codex config
- **Pi** — MEGAI and dual-store task-flow skills plus bash extensions are installed to `~/.pi/agent/`; task-flow keeps Asana and `.todos` synchronized. Dembrandt, Argent, and RepoWise are added to Pi MCP Adapter's global config; Ix, Argent, and RepoWise guidance is included in the MEGAI skill; the first authenticated model is saved as the global default when no valid default exists; `caveman` + `graphify` self-install; `ui-craft` registers where Pi supports it. Provider credentials cannot be bundled: on first use, run `pi` and `/login` once; Pi stores them globally in `~/.pi/agent/auth.json`.
- **All three** — `ux-ui-agent-skills` installs 17 global design capabilities with their shared references and scripts; its conflicting `prototype` skill is exposed as `ux-ui-prototype`. Matt Pocock's 22 promoted skills are installed globally via `skills.sh`; run `/setup-matt-pocock-skills` once in each project before using those engineering flows.

MEGAI also installs this recommended Pi package stack globally (user scope):

- `@vigolium/piolium`
- `pi-mcp-adapter`
- `pi-web-access`
- `pi-subagents`
- `bigpowers`
- `@dietrichgebert/ponytail`
- `pi-lens`
- `@narumitw/pi-statusline`

Existing package entries are preserved and skipped on repeat installs.

---

## task-flow — `.todos` board + ADLC

Every project gets a self-managing task board. Claude uses `.todos` directly. Pi mirrors the same execution flow to the matching Asana project and links tasks by GID. Both run each task through the full **ADLC** (AI Development Life Cycle) — no stage skipped.

**Board lives in the project** as plain markdown you can edit by hand:

```
<your-project>/.todos/
  todo.md         # 📋 pending     (file = status)
  inprogress.md   # 🚧 active
  done.md         # ✅ completed
  monitoring.md   # 📊 auto-generated dashboard (counts by status/priority/stage)
```

For Claude Code, `.todos/` is the single source of truth. In Pi, Asana is the coordination source and `.todos/` is the local execution mirror; an embedded Asana GID keeps each task linked without duplication.

Each line is a task with an **emoji priority** (and optional ADLC-stage emoji):

```
- [ ] 🔴 🔨 Fix the production crash      # urgent, in the generate stage
- [ ] 🟠 Add CSV export                    # high
- [ ] 🟡 Clean up the logs                 # medium
```

Priority: 🔴 urgent · 🟠 high · 🟡 medium · 🟢 low.  Stage: 📝 spec · 📐 plan · 🔨 generate · 🧪 verify · 🔍 review · 🚀 ship.

`monitoring.md` regenerates automatically on every board change — a live table of task counts by status, priority, and ADLC stage.

**Add tasks fast with `/ta`:**

```
/ta fix the login redirect bug !!!
/ta refactor the auth module
```

`/ta` appends the task to `.todos/todo.md` (creating the board if missing), parsing any `!!`/`!!!`/`!!!!` priority marker.

**Priority markers** (anywhere in your prompt or on the line): `!` low · `!!` medium · `!!!` high · `!!!!` urgent. Urgent **preempts** the running task; everything else waits its turn.

**ADLC stages:** `spec → plan → generate (test-first) → verify → review → ship`. The active task's stage shows live in the statusline as `◐ n/6 <stage>`.

**How it behaves:**

- **On every prompt** the request is analyzed and the task is written to `.todos/todo.md` **first**, then executed through the ADLC — the board entry always precedes the work. (Pure questions / trivial one-liners are answered directly.)
- **On every new session** a SessionStart hook checks for `.todos/`, creates it if missing (inside a real project), and feeds the current board into the session so Claude resumes the in-progress task automatically.
- Claude re-reads the board every turn — edit the files yourself anytime and Claude picks up the changes and continues.
- New tasks arriving mid-work are **queued, not dropped**; the in-progress task keeps going.
- After a task finishes, Claude **drains the queue** by priority. For hands-off draining while you're away, run `/loop`.

What the installer wires into Claude Code:

| Piece | Where | Purpose |
| ------- | ------- | --------- |
| `task-flow` skill | `~/.claude/skills/task-flow/` | the protocol (auto-invoked for multi-step work) |
| `/ta` command | `~/.claude/commands/ta.md` + `~/.claude/bin/taskflow-add.sh` | `/ta <text>` appends a task straight into `.todos/todo.md` |
| prompt hook | `~/.claude/hooks/taskflow-prompt.sh` | UserPromptSubmit: analyze the prompt → write the task first → run the ADLC |
| session hook | `~/.claude/hooks/taskflow-session.js` | SessionStart: ensures/creates `.todos/` and resumes the board |
| monitor hook | `~/.claude/hooks/taskflow-monitor.js` | PostToolUse: regenerates `monitoring.md` whenever the board changes |
| board statusline | `~/.claude/statusline-taskflow.sh` | renders the `.todos` board with emoji (set only if you have no statusline) |
| always-on rule | `~/.claude/CLAUDE.md` | markered block enabling the protocol globally |

All four are idempotent and reverted by `megai uninstall`. An existing `statusLine` is never overwritten.

---

## CLI

```
# default — activate stack for the folder you're in
megai                   # banner + start daemons + index + quick guide

# launch an agent CLI with the full stack already initialised
megai cc                # ensure wired -> start agent-memory -> codedb index -> graphify (bg) -> exec `claude`
megai codex             # same, then exec `codex`
megai pi                # same, then exec `pi`
megai graph [path]      # build a graphify knowledge graph -> graphify-out/

# manage
megai install           # re-run installer (idempotent)
megai status            # tool versions, ports, status
megai doctor            # diagnose missing deps and broken configs
megai start agent-memory
megai stop  agent-memory
megai update            # update all tools
megai wire <cc|codex|pi|path>  # only re-write MCP config / shell PATH (no launch)
megai logs agent-memory
megai uninstall
```

---

## ui-craft — design system for your agent

Stops AI-generated UIs from looking generic. `ui-craft` installs an anti-slop design skill, MCP gates, review agents, and a per-project **design memory** into every detected harness — so any agent you run already knows your tokens, patterns, and decisions.

```bash
ui-craft install --yes      # wire into detected harnesses (run by `megai install`)
ui-craft doctor             # health check
ui-craft backup             # snapshot harness configs before changes
ui-craft rollback           # restore the latest snapshot
```

Inside Claude Code / Codex / Cursor / Gemini / OpenCode you get the `ui-craft` skill plus focused presets — `minimal`, `editorial`, `dense-dashboard` — and per-pass commands (`/craft`, `/polish`, `/audit`, `/harden`, …). Design memory lives in `<project>/.ui-craft/` (`brief.md`, `tokens.md`, `patterns.md`, `decisions.md`) and is read by the agent on every UI task.

---

## ux-ui-agent-skills — global design knowledge

MEGAI installs the full [plugin87 kit](https://github.com/plugin87/ux-ui-agent-skills) under `~/.megai/ux-ui-agent-skills/` and links its 17 skills into Claude Code, Codex, and Pi user scopes. Shared tokens, component specs, accessibility references, framework adapters, scripts, and design-system profiles stay available from every linked skill.

The upstream `prototype` name overlaps Matt Pocock's engineering skill, so MEGAI preserves both by exposing the UI/UX version as `/ux-ui-prototype`.

---

## Dembrandt — website to design tokens

```bash
dembrandt example.com --design-md
dembrandt example.com --wcag --save-output
```

The installer adds the Dembrandt MCP server to Claude Code, Codex, and Pi, so agents can extract palettes, typography, spacing, component styles, and brand identity directly.

---

## Ix — persistent system map

```bash
ix map .
ix explain auth-service
ix trace user_login_flow
ix impact database.schema
```

Ix uses a local Docker backend on ports `8090` and `8529`. Set `IX_SKIP_BACKEND=1` before installation only if you want the CLI without the backend.

---

## RepoWise — code health, wiki, and MCP

```bash
repowise health
repowise risk main..HEAD
repowise serve
```

MEGAI starts a free, keyless `repowise init --no-prose --no-claude-md` index in the background the first time a Git repository is activated. The dashboard runs on `localhost:3000`; the API uses port `7337`.

---

## Argent — agent-driven app testing

```bash
argent tools
argent server status
```

Agents can drive iOS and Android devices, TV platforms, Electron apps, and Chromium through Argent's MCP server. Platform testing still requires the native SDK: Xcode for Apple targets, Android SDK Platform Tools for Android, and Vega SDK for Fire TV/Vega.

---

## Requirements

- macOS or Linux (Windows: use WSL)
- `curl`
- The installer brings in: `jq`, Node.js 20.12+, `python3`, `pipx`, `uv`, `ripgrep`, Docker, and Docker Compose

---

## File layout (post-install)

```
~/.megai/
  bin/megai
  lib/*.sh
  pi-skill/{SKILL.md,extensions/}
  task-flow/{skills/,hooks/,bin/,commands/,CLAUDE.snippet.md}
  ux-ui-agent-skills/
  state.json
  logs/
  backups/
```

---

## Uninstall

```bash
megai uninstall
```

Removes `~/.megai/` and reverts megai-managed MCP entries (including Dembrandt and Argent) in `~/.claude.json`, `~/.codex/config.toml`, and `~/.pi/agent/`; removes the task-flow and ux-ui-agent-skills links; and uninstalls the `ui-craft` components.

Ix, RepoWise, and their local index data are intentionally kept to prevent data loss. Remove Ix separately with `curl -fsSL https://ix-infra.com/uninstall.sh | sh`; remove RepoWise with `uv tool uninstall repowise` and delete a project's `.repowise/` only when its index is no longer needed.

---

## License

MIT

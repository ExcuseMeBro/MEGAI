<!-- logo -->
<pre align="center">
███╗   ███╗███████╗ ██████╗  █████╗ ██╗
████╗ ████║██╔════╝██╔════╝ ██╔══██╗██║
██╔████╔██║█████╗  ██║  ███╗███████║██║
██║╚██╔╝██║██╔══╝  ██║   ██║██╔══██║██║
██║ ╚═╝ ██║███████╗╚██████╔╝██║  ██║██║
╚═╝     ╚═╝╚═════╝╚██████╔╝╚═╝  ╚═╝╚═╝

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
  <b>🚀 One command · 🧰 Fourteen tools · 🤖 Three agent harnesses · ⚙️ Zero manual wiring</b><br>
  Memory · code intelligence · indexing · token compression · system maps · task flow · UI/UX · app testing
</p>

# 🧠 MEGAI

MEGAI is a one-line installer and manager for a complete AI coding-agent stack. It installs, configures, updates, and connects **14 tools** to **Claude Code**, **OpenAI Codex**, and **Pi** while preserving existing user configuration.

```bash
curl -fsSL https://raw.githubusercontent.com/ExcuseMeBro/MEGAI/main/install.sh | bash
```

Then verify the stack:

```bash
megai status
megai doctor
```

## 🗺️ Contents

- [⚡ Quick start](#-quick-start)
- [✨ What MEGAI solves](#-what-megai-solves)
- [🧰 Included stack](#-included-stack)
- [🤖 Agent integrations](#-agent-integrations)
- [⌨️ CLI reference](#️-cli-reference)
- [📋 task-flow and Asana](#-task-flow-and-asana)
- [🎨 Design and UI/UX stack](#-design-and-uiux-stack)
- [🗃️ Code intelligence and memory](#️-code-intelligence-and-memory)
- [🧪 App testing](#-app-testing)
- [📦 Pi package stack](#-pi-package-stack)
- [🏗️ How it works](#️-how-it-works)
- [📁 Installed files](#-installed-files)
- [🔄 Updating](#-updating)
- [🩺 Verification and troubleshooting](#-verification-and-troubleshooting)
- [🗑️ Uninstall](#️-uninstall)

---

## ⚡ Quick start

### 1. Install

```bash
curl -fsSL https://raw.githubusercontent.com/ExcuseMeBro/MEGAI/main/install.sh | bash
```

### 2. Reload your shell

```bash
source ~/.zshrc  # or open a new terminal
```

### 3. Activate a project

```bash
cd ~/path/to/project
megai
```

MEGAI starts or verifies agent-memory, indexes the repository, prepares the knowledge graph and RepoWise index, checks token-saving tools, and prints a project-specific guide.

### 4. Launch an agent

```bash
megai cc       # Claude Code
megai codex    # OpenAI Codex
megai pi       # Pi coding agent
```

Provider credentials are never bundled. Authenticate each agent normally on first use; for Pi, run `pi` and `/login` once.

---

## ✨ What MEGAI solves

Without MEGAI, every agent needs separate MCP entries, skills, hooks, plugins, paths, background services, and project indexes. MEGAI turns that setup into one idempotent pipeline.

- 🧠 **Persistent context** across sessions
- 🔎 **Fast code search and symbol intelligence**
- 🗺️ **Architecture maps and impact analysis**
- 📚 **Generated codebase knowledge and health reports**
- 🪨 **Lower agent output/token usage**
- 📋 **A visible `.todos` execution board with ADLC stages**
- 🔄 **Asana synchronization for Pi workflows**
- 🎨 **Design-system, accessibility, and UI quality skills**
- 🌐 **Website-to-design-token extraction**
- 🧪 **Mobile, TV, Electron, and browser testing**
- 🔌 **Global Claude Code, Codex, and Pi wiring**

MEGAI reuses existing installations and preserves unrelated user configuration on repeated runs.

---

## 🧰 Included stack

| | Tool | Purpose | Integration |
| --- | --- | --- | --- |
| 🧠 | [agent-memory](https://www.agent-memory.dev/) | Persistent cross-session memory | MCP + daemon, default port `3111` |
| 🔎 | [codedb](https://github.com/justrach/codedb) | Code search, symbols, outlines, and file intelligence | MCP + CLI |
| 🗂️ | [cocoindex](https://cocoindex.io) | Incremental indexing pipeline | CLI |
| 🪨 | [caveman](https://github.com/JuliusBrussee/caveman) | Compressed agent communication and workflow skills | Global skills/plugins |
| ⚡ | [rtk](https://github.com/rtk-ai/rtk) | Rust Token Killer for compact command output | CLI + Claude hook |
| 🕸️ | [graphify](https://graphify.net) | Tree-sitter knowledge graph and code relationships | CLI + global skill |
| 📋 | task-flow | `.todos` board, priority queue, ADLC, monitoring, Asana mirror | Claude hooks + Pi skill |
| 🎨 | [ui-craft](https://skills.smoothui.dev) | Anti-slop UI rules, design memory, review gates, presets | Global skills and commands |
| 🖌️ | [ux-ui-agent-skills](https://github.com/plugin87/ux-ui-agent-skills) | 17 UI/UX skills, WCAG references, tokens, components, adapters | Global skills |
| 🌐 | [Dembrandt](https://github.com/dembrandt/dembrandt) | Extract design tokens, typography, palette, brand, and WCAG data from websites | MCP + CLI |
| 🗺️ | [Ix](https://github.com/ix-infrastructure/Ix) | Persistent system map, architecture explanation, traces, impact analysis | CLI + plugins + MCP |
| 📚 | [RepoWise](https://github.com/repowise-dev/repowise) | Dependency graph, generated wiki, code health, risk, and history | MCP + CLI + background index |
| 🧪 | [Argent](https://github.com/software-mansion/argent) | Agent-driven mobile, TV, Electron, and Chromium testing | MCP + CLI |
| 🛠️ | [Matt Pocock's skills](https://github.com/mattpocock/skills) | Specs, TDD, diagnosis, review, domain modeling, architecture, and delivery flows | Global skills |

---

## 🤖 Agent integrations

### 🟠 Claude Code

MEGAI configures:

- MCP servers in `~/.claude.json`
- `agentmemory`, `codedb`, Dembrandt, Argent, and RepoWise
- Ix's `ix-memory` plugin
- `rtk` `PreToolUse` hook
- caveman and graphify skills
- task-flow skill, hooks, commands, monitoring, and optional statusline
- ui-craft commands, review agents, and design memory
- global Matt Pocock and UX/UI skills

Existing MCP servers, hooks, and statusline settings are preserved.

### 🔵 OpenAI Codex

MEGAI configures:

- a marked, idempotent MCP block in `~/.codex/config.toml`
- `agentmemory`, `codedb`, Dembrandt, Argent, and RepoWise
- Ix plugin, hooks, and MCP integration
- caveman, graphify, ui-craft, Matt Pocock, and UX/UI skills

Only MEGAI-owned MCP tables are replaced or removed; unrelated Codex configuration remains intact.

### 🟣 Pi

MEGAI configures:

- global MEGAI skill at `~/.pi/agent/skills/megai.md`
- Asana-aware task-flow skill at `~/.pi/agent/skills/megai-task-flow/`
- memory and codedb shell extensions
- Dembrandt, Argent, and RepoWise through Pi MCP Adapter
- global UX/UI, caveman, graphify, and Matt Pocock skills
- the first authenticated model as the global default when no valid default exists

Pi keeps provider authentication in `~/.pi/agent/auth.json`; MEGAI never writes credentials.

---

## ⌨️ CLI reference

```text
megai                         Activate the stack for the current project
megai cc                      Launch Claude Code with the stack ready
megai codex                   Launch Codex with the stack ready
megai pi                      Launch Pi with the stack ready
megai graph [path]            Build a graphify knowledge graph

megai install                 Re-run the installed MEGAI pipeline
megai update                  Update managed tools and re-wire agents
megai status                  Show tool versions, ports, and status
megai doctor                  Diagnose dependencies and integrations
megai reindex                 Force a codedb re-index for this project

megai start agent-memory      Start the memory daemon
megai stop agent-memory       Stop the memory daemon
megai logs agent-memory       Follow the memory log
megai logs repowise           Follow this project's RepoWise init log

megai wire cc                 Re-wire Claude Code only
megai wire codex              Re-wire Codex only
megai wire pi                 Re-wire Pi only
megai wire path               Re-wire shell PATH only

megai uninstall               Remove MEGAI-managed files and config
megai version                 Print the MEGAI version
megai help                    Show command help
```

---

## 📋 task-flow and Asana

Every project can use a plain-Markdown execution board:

```text
<project>/.todos/
├── todo.md          📋 queued
├── inprogress.md    🚧 active or in review
├── done.md          ✅ verified
└── monitoring.md    📊 generated dashboard
```

A task line carries priority and ADLC stage:

```markdown
- [ ] 🔴 🔨 Fix the production crash
- [ ] 🟠 🧪 Verify CSV export
- [ ] 🟡 📝 Specify log cleanup
```

### 🚦 Priority

| Marker | Priority |
| --- | --- |
| 🔴 or `!!!!` | Urgent |
| 🟠 or `!!!` | High |
| 🟡 or `!!` | Medium |
| 🟢 or `!` | Low |

### 🔁 ADLC stages

`📝 spec → 📐 plan → 🔨 generate → 🧪 verify → 🔍 review → 🚀 ship`

### 🔗 Pi + Asana mapping

For Pi, Asana is the coordination source of truth and `.todos` is the local execution mirror. Linked tasks store the Asana GID in an HTML comment to prevent duplicates.

| State | `.todos` | Asana section | Completed |
| --- | --- | --- | --- |
| Queued | `todo.md` | `Todo` | `false` |
| Active | `inprogress.md` | `In Progress` | `false` |
| Review | `inprogress.md` | `In Review` | `false` |
| Verified | `done.md` | `Done` | `true` |

### 🧩 Claude task-flow pieces

| Piece | Location | Purpose |
| --- | --- | --- |
| skill | `~/.claude/skills/task-flow/` | task protocol |
| `/ta` command | `~/.claude/commands/ta.md` | add a task quickly |
| prompt hook | `~/.claude/hooks/taskflow-prompt.sh` | classify prompts and queue work |
| session hook | `~/.claude/hooks/taskflow-session.js` | restore or create the board |
| monitor hook | `~/.claude/hooks/taskflow-monitor.js` | regenerate `monitoring.md` |
| move hook | `~/.claude/hooks/taskflow-move.js` | move tasks through stages |
| statusline | `~/.claude/statusline-taskflow.sh` | show board progress |
| global rule | `~/.claude/CLAUDE.md` | enable task-flow behavior |

Everything is idempotent. Existing Claude statuslines are not overwritten.

---

## 🎨 Design and UI/UX stack

### 🧱 ui-craft

`ui-craft` provides anti-generic UI guidance, design memory, MCP quality gates, review agents, and visual presets.

```bash
ui-craft install --yes
ui-craft doctor
ui-craft backup
ui-craft rollback
```

Project design memory lives in `<project>/.ui-craft/` and records briefs, tokens, patterns, and decisions.

### 🖌️ ux-ui-agent-skills

The full plugin87 kit is installed under `~/.megai/ux-ui-agent-skills/` and linked globally into Claude Code, Codex, and Pi.

It includes:

- 17 invocable skills
- WCAG 2.2 and ARIA guidance
- DTCG token architecture
- 50 component specifications
- framework adapters
- design QA scripts
- 138 design-system profiles

The upstream `prototype` name overlaps Matt Pocock's engineering skill, so the UI/UX version is exposed as `/ux-ui-prototype`.

### 🌐 Dembrandt

```bash
dembrandt example.com --design-md
dembrandt example.com --wcag --save-output
```

Dembrandt can extract palettes, typography, spacing, brand identity, tokens, and accessibility findings from live sites.

---

## 🗃️ Code intelligence and memory

### 🧠 Persistent memory

```bash
megai-memory save "Use TIMESTAMPTZ for all persisted dates"
megai-memory recall "datetime decisions"
megai-memory sessions
```

### 🔎 Code intelligence

```bash
megai-codedb search "authentication"
megai-codedb symbol handleLogin
megai-codedb outline src/auth.ts
megai-codedb tree src/
```

### 🕸️ Knowledge graph

```bash
megai graph .
megai graph ./docs
```

### 🗺️ Ix system map

```bash
ix map .
ix explain auth-service
ix trace user_login_flow
ix impact database.schema
```

Ix's local backend uses ports `8090` and `8529`. Set `IX_SKIP_BACKEND=1` before installation to install the CLI without starting the backend.

### 📚 RepoWise

```bash
repowise health
repowise risk main..HEAD
repowise serve
```

The first MEGAI activation in a Git repository starts a background, keyless RepoWise index. The dashboard defaults to `localhost:3000`; the API uses port `7337`.

---

## 🧪 App testing

Argent exposes device and browser automation through CLI and MCP:

```bash
argent tools
argent server status
```

Supported targets include:

- 📱 iOS and Android
- 📺 Apple TV, Android TV, and Fire TV/Vega
- 🖥️ Electron
- 🌐 Chromium through CDP
- 🎥 recording and replay
- 🖼️ screenshots and visual regression
- 📡 logs, network inspection, and profiling

Native targets still require their platform SDKs: Xcode for Apple, Android Platform Tools for Android, and Vega SDK for Fire TV/Vega.

---

## 📦 Pi package stack

MEGAI installs these Pi packages globally and preserves existing entries:

| Package | Role |
| --- | --- |
| `@vigolium/piolium` | Pi productivity tools |
| `pi-mcp-adapter` | MCP server support |
| `pi-web-access` | web search and content access |
| `pi-subagents` | managed subagent workflows |
| `bigpowers` | extended Pi capabilities |
| `@dietrichgebert/ponytail` | minimal-code workflow |
| `pi-lens` | LSP, diagnostics, symbols, and code intelligence |
| `@narumitw/pi-statusline` | statusline integration |

Repeated installs skip package entries that already exist.

---

## 🏗️ How it works

```text
                    ┌─────────────────────┐
                    │   curl install.sh   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  ~/.megai/lib/main  │
                    │  17-step pipeline   │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
┌─────────▼─────────┐ ┌────────▼────────┐ ┌────────▼────────┐
│   Claude Code     │ │      Codex      │ │       Pi        │
│ MCP/hooks/plugins │ │ MCP/hooks/skills│ │ MCP/skills/exts │
└───────────────────┘ └─────────────────┘ └─────────────────┘
```

The installer:

1. 🔍 Detects OS, architecture, and runtimes.
2. 📦 Installs or reuses each tool.
3. 🧾 Records paths, ports, and versions in `~/.megai/state.json`.
4. 🔌 Merges MEGAI-owned MCP entries into each harness.
5. 🧩 Installs global skills, hooks, plugins, and extensions.
6. 🛡️ Preserves unrelated user configuration and creates backups.
7. ✅ Repeats safely on future installs and updates.

---

## 📁 Installed files

```text
~/.megai/
├── bin/
│   ├── megai
│   ├── codedb
│   ├── cocoindex
│   ├── graphify
│   ├── ix
│   └── repowise
├── lib/                         installer and wiring scripts
├── pi-skill/                    Pi MEGAI skill and extensions
├── task-flow/                   skills, hooks, commands, and monitor
├── ux-ui-agent-skills/          global plugin87 source and wrappers
├── logs/
├── backups/
└── state.json
```

Agent-specific configuration remains in its normal user directory:

- 🟠 Claude Code: `~/.claude/` and `~/.claude.json`
- 🔵 Codex: `~/.codex/` and `~/.agents/skills/`
- 🟣 Pi: `~/.pi/agent/`

---

## 🔄 Updating

### Update MEGAI itself

Re-run the one-line installer to fetch the latest `main` branch and execute the current pipeline:

```bash
curl -fsSL https://raw.githubusercontent.com/ExcuseMeBro/MEGAI/main/install.sh | bash
```

### Update managed tools

```bash
megai update
```

This refreshes supported tools, global skills, integrations, and MCP wiring without replacing unrelated user configuration.

---

## 🩺 Verification and troubleshooting

### Check installation state

```bash
megai status
megai doctor
```

A healthy installation reports the core CLIs, agent configuration files, agent-memory daemon, Ix backend/plugins, global UX/UI skills, RepoWise, and Argent.

### Useful checks

```bash
megai start agent-memory       # restart persistent memory
megai reindex                  # rebuild codedb state for this project
megai wire pi                  # repair Pi MCP/skills/extensions
megai wire codex               # repair Codex MCP block
megai wire cc                  # repair Claude MCP entries
megai logs repowise            # inspect background RepoWise indexing
```

### Common requirements

- 🍎 macOS or 🐧 Linux; Windows users should use WSL
- `curl`
- Node.js `20.12+`
- Python 3 and `pipx`
- `jq`
- Docker and Docker Compose for the full Ix backend
- `uv` for RepoWise installation
- `ripgrep`

The installer resolves supported missing dependencies where possible and reports anything that still needs manual action.

---

## 🔐 Security and privacy

- 🔑 MEGAI does not bundle or commit provider credentials.
- 🧩 Skills and plugins run with agent permissions; review third-party skill sources before use.
- 💾 Configuration files are backed up before MEGAI changes them.
- 🧱 Only MEGAI-owned MCP entries and marked blocks are replaced or removed.
- 🏠 agent-memory, Ix, and RepoWise services run locally by default.

---

## 🗑️ Uninstall

```bash
megai uninstall
```

MEGAI removes its home directory and reverts MEGAI-managed MCP entries, task-flow pieces, UX/UI skill links, shell PATH entries, and ui-craft components.

To prevent data loss, Ix, RepoWise, and their local project indexes are retained. Remove them separately only when their data is no longer needed:

```bash
curl -fsSL https://ix-infra.com/uninstall.sh | sh
uv tool uninstall repowise
```

Delete a project's `.repowise/` directory manually if you also want to remove its generated index.

---

## 📄 License

MEGAI is released under the [MIT License](LICENSE).

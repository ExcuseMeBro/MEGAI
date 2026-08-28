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
  <img src="https://img.shields.io/badge/harnesses-Claude%20Code%20%7C%20Codex%20%7C%20Pi%20%7C%20OMP-8A2BE2.svg" alt="Harnesses">
  <img src="https://img.shields.io/badge/tools-15-orange.svg" alt="Tools">
</p>

<p align="center">
  <b>🚀 One command · 🧰 Fifteen tools · 🤖 Four agent harnesses · ⚙️ Zero manual wiring</b><br>
  Memory · code intelligence · indexing · token compression · system maps · task flow · UI/UX · app testing · security operations
</p>

# 🧠 MEGAI

MEGAI is a one-line installer and manager for a complete AI coding-agent stack. It installs, configures, updates, and connects **15 tools** to **Claude Code**, **OpenAI Codex**, **Pi**, and **Oh My Pi (OMP)** while preserving existing user configuration.

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
- [🛡️ Security operations](#️-security-operations)
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
megai omp      # Oh My Pi
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
- 🛡️ **Scoped AppSec and pentest operations with evidence-backed findings**
- 🔌 **Global Claude Code, Codex, Pi, and OMP wiring**

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
| 📋 | task-flow | `.todos` board, priority queue, ADLC, monitoring, Asana mirror | Claude hooks + global skills |
| 🌿 | agent-worktree-lifecycle | Default work to `dev`; push and open/reuse `dev` → `main` PR/MR; clean merged worktrees | Global policy + `megai dev`/`finish` |
| 🧭 | smart-development-orchestrator | Token-aware MiniMax/GPT complexity routing, Paseo fanout, and hybrid tab/worktree placement | Global skill + OMP agents |
| ⚙️ | MiniMax Code M3 OMP worker | Routine exploration/implementation tier targeting roughly 60% of inference tokens | Native OMP provider + managed agent |
| 🎨 | [ui-craft](https://skills.smoothui.dev) | Anti-slop UI rules, design memory, review gates, presets | Global skills and commands |
| 🖌️ | [ux-ui-agent-skills](https://github.com/plugin87/ux-ui-agent-skills) | 17 UI/UX skills, WCAG references, tokens, components, adapters | Global skills |
| 🌐 | [Dembrandt](https://github.com/dembrandt/dembrandt) | Extract design tokens, typography, palette, brand, and WCAG data from websites | On-demand CLI |
| 🗺️ | [Ix](https://github.com/ix-infrastructure/Ix) | Persistent system map, architecture explanation, traces, impact analysis | CLI + plugins + MCP |
| 📚 | [RepoWise](https://github.com/repowise-dev/repowise) | Dependency graph, generated wiki, code health, risk, and history | On-demand CLI + background index |
| 🧪 | [Argent](https://github.com/software-mansion/argent) | Agent-driven mobile, TV, Electron, and Chromium testing | On-demand CLI |
| 🛡️ | [Numasec](https://github.com/FrancescoStabile/numasec) | Authorized AppSec/pentest operations, evidence, replay, and reports | CLI + global handoff skill |
| 🛠️ | [Matt Pocock's skills](https://github.com/mattpocock/skills) | Specs, TDD, diagnosis, review, domain modeling, architecture, and delivery flows | Global skills |

---

## 🤖 Agent integrations

### 🟠 Claude Code

MEGAI configures:

- lean default MCP surface in `~/.claude.json`: `agentmemory` and `codedb`
- Dembrandt, Argent, and RepoWise CLIs available on demand
- Ix's `ix-memory` plugin
- `rtk` `PreToolUse` hook
- caveman and graphify skills
- task-flow skill, hooks, commands, monitoring, optional statusline, and safe `dev` merge/worktree cleanup policy
- ui-craft commands, review agents, and design memory
- global Matt Pocock and UX/UI skills

Existing MCP servers, hooks, and statusline settings are preserved.

### 🔵 OpenAI Codex

MEGAI configures:

- a lean, marked MCP block in `~/.codex/config.toml` with `agentmemory` and `codedb`
- Dembrandt, Argent, and RepoWise CLIs available on demand
- Ix plugin, hooks, and MCP integration
- caveman, graphify, ui-craft, Matt Pocock, UX/UI, and safe worktree-lifecycle skills

Only MEGAI-owned MCP tables are replaced or removed; unrelated Codex configuration remains intact.

### 🟣 Pi

MEGAI configures:

- global MEGAI skill at `~/.pi/agent/skills/megai.md`
- Asana-aware task-flow and safe worktree-lifecycle skills under `~/.pi/agent/skills/`
- memory and codedb shell extensions
- Dembrandt, Argent, and RepoWise CLIs available on demand instead of permanent MCP entries
- global UX/UI, caveman, graphify, and Matt Pocock skills
- the first authenticated model as the global default when no valid default exists

Pi keeps provider authentication in `~/.pi/agent/auth.json`; MEGAI never writes credentials.

### ⚪ Oh My Pi (OMP)

MEGAI configures:

- native MCP entries for `agentmemory` and `codedb` in the active OMP profile
- native MEGAI, Asana-aware task-flow, safe worktree-lifecycle, and smart-development-orchestrator skills under the active profile's `skills/` directory
- MiniMax-first `smart-router`, trusted Luna lookup scout, Terra architecture worker, and routine `minimax-worker` under the active profile's `agents/` directory
- OMP's native MiniMax catalog and provider-specific transport compatibility; MEGAI never rewrites user `models.yml`
- preservation of unrelated OMP servers, model providers, allowlists, denylists, credentials, agents, and user settings
- hybrid Paseo placement: read-only subagents stay as tabs in the current workspace; every concurrent writer receives a separate managed worktree workspace, which is archived only after its verified merge, dev push, PR/MR creation, and worktree cleanup succeed
- Dembrandt, Argent, RepoWise, Numasec, and global skills through OMP's existing CLI and skill discovery surfaces

OMP provider authentication remains in OMP's own credential store; MEGAI never writes provider credentials.

MiniMax Code M3 runs through OMP's native `minimax-code` provider, never Pi. A key pasted into chat or logs is compromised and must be revoked before use. Configure the rotated Token Plan key through OMP auth or `MINIMAX_CODE_API_KEY` outside source; MEGAI never stores credentials.

`megai omp` always loads `~/.megai/omp-config/high-speed.yml` for Codex Code Mode `auto`, provider concurrency (`openai-codex: 2`, `minimax-code: 4`), six-agent fanout, async batch execution, and branch-merge isolation. It adds `balanced-minimax.yml` only when the selected OMP profile reports authenticated `MiniMax-M3` availability; without MiniMax auth, the trusted existing default remains unchanged.

The authenticated balanced overlay maps routine roles (`default`, `task`) to MiniMax Code M3 `medium`, `smol` to `low`, and `tiny`/`commit` to the supported `minimal` effort. GPT-5.6 Sol owns `plan`, `slow`, `advisor`, and `vision`; Luna/Terra remain trusted discovery/review roles. For Paseo-launched OMP sessions, add both overlay paths to `PI_CONFIG_FILES` only after MiniMax Code auth. The 60/40 split is an advisory observed-token target, never a reason to weaken HIGH/CRITICAL GPT gates. No free OpenCode models participate.

---

## ⌨️ CLI reference

```text
megai                         Activate the stack for the current project
megai cc                      Launch Claude Code with the stack ready
megai codex                   Launch Codex with the stack ready
megai pi                      Launch Pi with the stack ready
megai omp                     Launch Oh My Pi with the stack ready
megai omp --profile work      Launch OMP and wire the named profile
megai security [args]         Launch Numasec (authorized targets only)
megai graph [path]            Build a graphify knowledge graph
megai dev                     Switch a clean primary main/master checkout to dev
megai finish --dry-run --target dev
megai finish --verified --target dev
                              Push verified dev, open/reuse dev-to-main PR/MR, clean merged worktree

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
megai wire omp                Re-wire Oh My Pi only
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

### 🔗 Boundary-only Asana mapping

Asana synchronizes only at task boundaries; `.todos` owns the six local ADLC stages. Linked tasks store the Asana GID in an HTML comment to prevent duplicate searches.

| Boundary | `.todos` | Asana section | Completed |
| --- | --- | --- | --- |
| Start | `inprogress.md` | `In Progress` | `false` |
| Finish | `done.md` | `Done` | `true` |

Routine stage changes, `In Review` moves, milestone comments, and repeated board reads are skipped. An Asana comment is reserved for a real external blocker.

### 🌿 Agent branch ship gate

Primary development defaults to `dev` (`megai dev` switches a clean `main`/`master` checkout). Isolated agent branches start from `dev`. At 🚀 ship, `megai finish --verified --target dev` merges task work when needed, pushes `dev`, and creates or reuses an open `dev` → `main` GitHub PR or GitLab merge request before the Asana finish boundary. It never auto-merges `main`, deletes remote refs, or deletes primary/dirty/unmerged repositories. Missing branches/origin, failed verification, conflicts, forge authentication, push, or PR/MR creation stop completion.

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

## 🛡️ Security operations

Numasec runs as an isolated interactive security specialist while MEGAI remains the project and task orchestrator:

```bash
cd ~/path/to/authorized-target
megai security
```

Start with `/doctor`, `/opsec strict`, and a narrowly scoped runbook. Use Numasec only for systems you own, labs/CTFs, or targets where you have explicit testing permission. Its `numasec-security` handoff skill is linked globally for Claude Code, Codex, and Pi; generated reports or share artifacts can return to MEGAI for remediation.

---

## 📦 Pi package stack

MEGAI keeps Pi's default startup lean:

| Default package | Role |
| --- | --- |
| `pi-mcp-adapter` | lazy MCP support with cached direct tools |
| `@narumitw/pi-statusline` | statusline integration |

Optional extensions are available through the full profile:

```bash
MEGAI_PI_FULL=1 megai install
```

The full profile also enables `@vigolium/piolium`, `pi-web-access`, `pi-subagents`, `bigpowers`, `@dietrichgebert/ponytail`, and `pi-lens`. Without `MEGAI_PI_FULL=1`, repeated installs remove only those MEGAI-owned optional entries from Pi's startup list; unrelated user packages are preserved.

---

## 🏗️ How it works

```text
                    ┌─────────────────────┐
                    │   curl install.sh   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  ~/.megai/lib/main  │
                    │  18-step pipeline   │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
┌─────────▼─────────┐ ┌────────▼────────┐ ┌────────▼────────┐
│   Claude Code     │ │   Codex / Pi    │ │      OMP        │
│ MCP/hooks/plugins │ │ MCP/skills/exts │ │ MCP/skills      │
└───────────────────┘ └─────────────────┘ └─────────────────┘
```

The installer:

1. 🔍 Detects OS, architecture, and runtimes.
2. 📦 Installs or reuses each tool.
3. 🧾 Records paths, ports, and versions in `~/.megai/state.json`.
4. 🔌 Wires the core MCP pair into Claude Code, Codex, and OMP, while Pi uses lightweight shell extensions.
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
├── omp-skill/                   OMP-native MEGAI skill
├── task-flow/                   skills, hooks, commands, and monitor
├── skills/numasec-security/     authorized security handoff guidance
├── skills/agent-worktree-lifecycle/  dev-default, dev-to-main PR, safe cleanup
├── skills/smart-development-orchestrator/  Luna/Terra and multi-provider routing policy
├── omp-agents/                   MiniMax router/worker plus Luna and Terra trusted scouts
├── omp-config/                   reusable high-speed OMP overlay
├── ux-ui-agent-skills/          global plugin87 source and wrappers
├── logs/
├── backups/
└── state.json
```

Agent-specific configuration remains in its normal user directory:

- 🟠 Claude Code: `~/.claude/` and `~/.claude.json`
- 🔵 Codex: `~/.codex/` and `~/.agents/skills/`
- 🟣 Pi: `~/.pi/agent/`
- ⚪ OMP: `~/.omp/agent/`

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

A healthy installation reports the core CLIs, agent configuration files, agent-memory daemon, Ix backend/plugins, global UX/UI and Numasec skills, RepoWise, Argent, and Numasec.

### Useful checks

```bash
megai start agent-memory       # restart persistent memory
megai reindex                  # rebuild codedb state for this project
megai wire pi                  # repair Pi skills/extensions and clean legacy MCP entries
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
- 🛡️ Numasec execution is opt-in and must stay within an explicitly authorized target scope.

---

## 🗑️ Uninstall

```bash
megai uninstall
```

MEGAI removes its home directory and reverts MEGAI-managed MCP entries, task-flow pieces, UX/UI and Numasec skill links, shell PATH entries, and ui-craft components. The Numasec CLI is retained to avoid deleting an independently usable security tool.

To prevent data loss, Ix, RepoWise, and their local project indexes are retained. Remove them separately only when their data is no longer needed:

```bash
curl -fsSL https://ix-infra.com/uninstall.sh | sh
uv tool uninstall repowise
```

Delete a project's `.repowise/` directory manually if you also want to remove its generated index.

---

## 📄 License

MEGAI is released under the [MIT License](LICENSE).

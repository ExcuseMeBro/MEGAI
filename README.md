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
  <img src="https://img.shields.io/badge/stack-core%20%2B%20optional-orange.svg" alt="Core and optional integrations">
</p>

<p align="center">
  <b>🚀 One command · 🧰 Core tools + optional specs · 🤖 Four agent harnesses · ⚙️ Managed wiring</b><br>
  Memory · code intelligence · indexing · bounded orchestration · task flow · OpenSpec · UI/UX · app testing · security operations
</p>

# 🧠 MEGAI

MEGAI is a one-line installer and manager for a complete AI coding-agent stack. It installs, configures, updates, and connects **coding tools and optional spec workflows** to **Claude Code**, **OpenAI Codex**, **Pi**, and **Oh My Pi (OMP)** while preserving existing user configuration.

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
- [🧭 Bounded Pi/Paseo orchestration](#-bounded-pipaseo-orchestration)
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

MEGAI starts or verifies agent-memory, builds codedb structural and zvec-grep hybrid indexes, prepares the knowledge graph and RepoWise index, checks token-saving tools, and prints a project-specific guide.

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
- 🔄 **Parent-owned Asana boundaries with user-owned completion**
- 📝 **Optional OpenSpec requirements and acceptance scenarios for complex changes**
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
| 🗂️ | [zvec-grep](https://github.com/zvec-ai/zvec-grep) | Local hybrid workspace search: BM25, vectors, and managed ripgrep | CLI + global Pi MCP |
| 🪨 | [caveman](https://github.com/JuliusBrussee/caveman) | Optional compressed communication/workflow skills (`MEGAI_CAVEMAN=1`) | Global skills/plugins, not a core dependency |
| ⚡ | [rtk](https://github.com/rtk-ai/rtk) | Rust Token Killer for compact command output | CLI + Claude hook |
| 🕸️ | [graphify](https://graphify.net) | Tree-sitter knowledge graph and code relationships | CLI + global skill |
| 📋 | task-flow | `.todos` board, priority queue, ADLC, monitoring, Asana mirror | Claude hooks + global skills |
| 🌿 | agent-worktree-lifecycle | Task worktrees → `dev`; one open promotion PR; user-approved `main` merge | Global policy + `megai dev`/`finish`/`promote` |
| 🧭 | smart-development-orchestrator | GPT writer routing, MiniMax read-only discovery, Paseo worktree delivery | Global skill + OMP agents |
| ⚙️ | GPT-core + MiniMax-discovery routing | GPT owns every write; MiniMax only searches, reads, and finds code | OMP roles + managed agents |
| 🎨 | [ui-craft](https://skills.smoothui.dev) | Anti-slop UI rules, design memory, review gates, presets | Global skills and commands |
| 🖌️ | [ux-ui-agent-skills](https://github.com/plugin87/ux-ui-agent-skills) | 17 UI/UX skills, WCAG references, tokens, components, adapters | Global skills |
| 🌐 | [Dembrandt](https://github.com/dembrandt/dembrandt) | Extract design tokens, typography, palette, brand, and WCAG data from websites | On-demand CLI |
| 📚 | [RepoWise](https://github.com/repowise-dev/repowise) | Dependency graph, generated wiki, code health, risk, and history | On-demand CLI + background index |
| 🧪 | [Argent](https://github.com/software-mansion/argent) | Explicit `/argent` mobile, TV, Electron, and Chromium review | Slash command + on-demand CLI |
| 🛡️ | [Numasec](https://github.com/FrancescoStabile/numasec) | Authorized AppSec/pentest operations, evidence, replay, and reports | CLI + global handoff skill |
| 🛠️ | [Matt Pocock's skills](https://github.com/mattpocock/skills) | Specs, TDD, diagnosis, review, domain modeling, architecture, and delivery flows | Global skills |
| 📝 | [OpenSpec](https://github.com/Fission-AI/OpenSpec) | Durable requirements, scenarios and one detailed checklist for complex changes | **Optional** pinned CLI + one global Pi skill |

---

## 🤖 Agent integrations

### 🟠 Claude Code

MEGAI configures:

- lean default MCP surface in `~/.claude.json`: `agentmemory` and `codedb`
- Dembrandt, Argent, and RepoWise CLIs available on demand
- `rtk` `PreToolUse` hook
- graphify skills; Caveman only when explicitly installed
- task-flow skill, hooks, commands, monitoring, optional statusline, and safe `dev` merge/worktree cleanup policy
- ui-craft commands, review agents, and design memory
- global Matt Pocock and UX/UI skills

Existing MCP servers, hooks, and statusline settings are preserved.

### 🔵 OpenAI Codex

MEGAI configures:

- a lean, marked MCP block in `~/.codex/config.toml` with `agentmemory` and `codedb`
- Dembrandt, Argent, and RepoWise CLIs available on demand
- graphify, ui-craft, Matt Pocock, UX/UI, and safe worktree-lifecycle skills; Caveman is optional

Only MEGAI-owned MCP tables are replaced or removed; unrelated Codex configuration remains intact.

### 🟣 Pi

MEGAI configures:

- global MEGAI skill at `~/.pi/agent/skills/megai.md`
- Asana-aware task-flow and safe worktree-lifecycle skills under `~/.pi/agent/skills/`
- `megai-memory` and `megai-codedb` CLI bridges in `~/.megai/bin` (not shell files masquerading as Pi extensions)
- a global `zvec_grep` MCP entry in `~/.pi/agent/mcp.json` for semantic and hybrid workspace retrieval
- Dembrandt, Argent, and RepoWise CLIs available on demand instead of permanent MCP entries
- global UX/UI, graphify, and Matt Pocock skills; redundant Caveman/Cavecrew and legacy OMP-routing skills excluded from global Pi discovery
- the first authenticated model as the global default when no valid default exists

Pi keeps provider authentication in `~/.pi/agent/auth.json`; MEGAI never writes credentials.

#### Optional OpenSpec for complex changes

```bash
bash "$HOME/.megai/lib/install_openspec.sh"  # tested OpenSpec 1.12.0 + one global Pi skill
# In a new/reloaded Pi session:
# /skill:megai-openspec <change request>
```

[OpenSpec](https://github.com/Fission-AI/OpenSpec) supplies durable requirements for multi-module features, public API/data migrations, consequential security changes, and explicit spec requests. Small known-seam fixes keep the normal fast path. Installation is opt-in (not part of `megai install`) and does not initialize other repositories. Node >=20.19.0 is required; mismatched existing CLI versions and user-owned skills are preserved with a clear failure instead of being replaced.

The parent keeps Asana as status authority and one `.todos` summary linked to the change; OpenSpec `tasks.md` is the only detailed checklist. MEGAI uses the upstream `spec-driven` schema with a single global Pi bridge, not another generated OPSX prompt/skill bundle. Existing project configuration is preserved. Run real tests as well as strict spec validation: OpenSpec planning completeness and advisory verification are not implementation proof. Agent handoff remains `In Review`, `completed=false`; archive and main promotion require separate explicit user approval.

The installer disables OpenSpec telemetry and npm lifecycle scripts. Managed Pi destinations are recorded in state, including custom `PI_CODING_AGENT_DIR` installs; removal verifies each symlink's ownership even if that environment variable is no longer set. The workflow stops if the installed CLI differs from the tested version. To unlink only the managed Pi bridge, run `bash "$HOME/.megai/lib/install_openspec.sh" --remove`; CLI, privacy settings and project specs remain. `megai uninstall` also removes the managed link. Source policy: [`skills/megai-openspec/SKILL.md`](skills/megai-openspec/SKILL.md).

### ⚪ Oh My Pi (OMP)

MEGAI configures:

- native MCP entries for `agentmemory` and `codedb` in the active OMP profile
- native MEGAI, Asana-aware task-flow, safe worktree-lifecycle, and smart-development-orchestrator skills under the active profile's `skills/` directory
- MiniMax read-only `smart-router`, trusted Luna/Terra scouts, and GPT `gpt-core-worker`/`gpt-fast-worker` implementations under the active profile's `agents/` directory
- OMP's native MiniMax catalog and provider-specific transport compatibility; MEGAI never rewrites user `models.yml`
- preservation of unrelated OMP servers, model providers, allowlists, denylists, credentials, agents, and user settings
- hybrid Paseo placement: each writer receives a managed worktree from `dev`, then is archived after verified dev merge/push, one open promotion request, and worktree cleanup
- Dembrandt, Argent, RepoWise, Numasec, and global skills through OMP's existing CLI and skill discovery surfaces

OMP provider authentication remains in OMP's own credential store; MEGAI never writes provider credentials.

MiniMax Code runs only through OMP's native provider and is restricted to read-only M2.1 Lightning discovery. Configure its key through OMP auth or `MINIMAX_CODE_API_KEY` outside source; MEGAI never stores credentials.

`megai omp` always loads `high-speed.yml` with provider concurrency `openai-codex: 2`, `minimax-code: 2`. It adds `balanced-minimax.yml` only when MiniMax M2.1 Lightning and the required GPT portfolio are available.

The overlay maps every write-capable role to GPT. Terra medium owns default/core implementation; GPT-5.4 Mini owns small edits and focused tests; GPT-5.5 owns migrations/debugging; GPT-5.4 owns compatibility; Spark owns tiny mechanical changes. MiniMax owns only read-only search/read/find/symbol/reference discovery.

The active portfolio:

| Model | Authority |
| --- | --- |
| MiniMax M2.1 Lightning | Read-only repository search, read, find, symbols, references, callers, patterns |
| GPT-5.6 Terra medium | Default/core implementation and self-review |
| GPT-5.6 Terra high | High-risk implementation, architecture, explicit deep review |
| GPT-5.4 Mini | Fast bounded edits and focused tests |
| GPT-5.5 | Migrations and hard debugging |
| GPT-5.4 | Compatibility and long-context implementation |
| GPT-5.3 Codex Spark | Tiny mechanical trusted changes |
| GPT-5.6 Sol | Explicit critical reasoning |
| GPT-5.6 Luna | One-step trusted discovery fallback |

Only MiniMax discovery may fall back once to Luna. GPT write roles never fall back to MiniMax. There is no fixed 50/50 token quota: the enforceable split is MiniMax read-only, GPT write-only.

Default execution is one bounded sequence: inspect, implement, self-review, focused tests, deliver to `dev`, then stop. `finish` reuses one promotion request; `promote --approved` merges it only after explicit user approval. Git and workspace operations remain deterministic.

Model settings apply to new sessions and task resolutions. If any writer badge shows MiniMax, stop it immediately and relaunch once on `gpt-core-worker` or `gpt-fast-worker`.

Runaway protection is enabled: subagents have a 16-request soft budget, a five-minute hard runtime, four concurrent background jobs, and a two-call identical-tool loop threshold. Goal auto-continuation, queue draining, autonomous `/loop`, sampled review, browser/visual QA, and automatic full-suite runs are disabled.

UI verification is code-only by default: structure, states, accessibility semantics, token/style consistency, diagnostics, and focused component tests. The user owns visual/manual review unless a task explicitly requests browser, simulator, screenshot, design, or accessibility auditing.

Paseo-visible workspaces require Paseo orchestration tools: native OMP `task` isolation creates internal worktrees but not Paseo workspace rows. Inside Paseo, each writer is launched with `create_workspace(isolation: "worktree", mode: "branch-off", baseBranch: "dev", branchName: "task/<slug>")`, then `create_agent(workspaceId: ...)`. Read-only workers stay as tabs in the orchestrator workspace. Native OMP isolation is used only outside Paseo.

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
                              Merge/push dev, reuse one open request, clean task worktree
megai promote --dry-run       Preview the reviewed dev-to-main promotion
megai promote --approved      Merge only after explicit user approval

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
├── done.md          ✅ user-confirmed complete
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

### 🔁 Execution

The fast path is `implement → code self-review → focused test → ship when required`. The six `.todos` ADLC emojis remain bookkeeping labels only; they do not trigger separate agents or model/tool passes.

### 🔗 Boundary-only Asana mapping

The Asana-aware `megai-task-flow` skill used by Pi and OMP synchronizes only at boundaries. The parent starts a linked task before project edits; questions and read-only investigation need no task. Resolve the project by an exact Git-root folder-name match and ask if absent or ambiguous. Children inherit the task and never mutate Asana or `.todos`.

| Boundary | `.todos` | Asana section | Completed |
| --- | --- | --- | --- |
| Start | `inprogress.md` | `In Progress` | `false` |
| Verified agent handoff | `inprogress.md`, unchecked and labelled In Review | `In Review` | `false` |
| User marks Done; reconcile | `done.md` | `Done` | `true` |

Only the user may mark Done. Store the GID in an HTML comment and reuse it for follow-ups; an active task needs no per-edit skill reload or repeated start mutation. A follow-up after handoff returns the same task to In Progress. Skip routine stage sync, milestone comments and unchanged board rereads; the queue never auto-drains. Standalone Claude board hooks are a separate integration and remain subject to repository/user policy.

### 🌿 Agent branch delivery and promotion

Primary development defaults to `dev`; isolated task branches start from `dev`. `megai finish --verified --target dev` merges task work, pushes `dev`, reuses the one open `dev` → `main` request, and cleans only the merged task worktree/branch. Agent work then moves to `In Review`, still incomplete in Asana. The agent asks whether to promote main and runs `megai promote --approved` only after an explicit affirmative reply. Promotion verifies the reviewed head and clean forge state, merges the request, synchronizes `main`, and preserves `dev`.

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

### 🔎 Hybrid search and code intelligence

The free local code workflow is **codedb + zvec-grep + native read/edit**, with **rg** for exact text and fallback. Use zvec-grep when wording or location is unknown, then codedb for structural navigation. Read the relevant ranges, make exact edits, and verify the diff and affected behavior. Architecture/impact explanations must be grounded in those lookups and code reads; no additional map daemon or paid toolchain is required.

```bash
zg query "where authentication is validated"
zg query --fts "AuthService"
zg query --rg -n "TODO" src/
megai-codedb symbol handleLogin
megai-codedb outline src/auth.ts
megai-codedb tree src/
```

The first MEGAI activation builds `.zvec-grep/` with the local `potion-code-16m-v2` embedding model. Override it with `MEGAI_ZVEC_EMBEDDING`; MEGAI never authorizes remote Embedding automatically.

### 🕸️ Knowledge graph

```bash
megai graph .
megai graph ./docs
```

### 📚 RepoWise

```bash
repowise health
repowise risk main..HEAD
repowise serve
```

The first MEGAI activation in a Git repository starts a background, keyless RepoWise index. The dashboard defaults to `localhost:3000`; the API uses port `7337`.

---

## 🧪 App testing

Argent is disabled during normal implementation, review, verification, UI checks, and delivery. Invoke it explicitly:

```text
/argent [target or scenario]
```

That single turn may inspect `argent tools` and `argent server status`, then run the narrowest requested app/device review. It makes no code edits and stops after reporting observed findings.

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

## 🧭 Bounded Pi/Paseo orchestration

[`prompts/paseo-orchestrator.md`](prompts/paseo-orchestrator.md) is the shared execution-policy reference. It separates delegated leaf tasks from the parent role instead of telling every agent to orchestrate.

| Task shape | Default execution |
| --- | --- |
| Small known-seam fix | Parent/direct tools; acceptance, diff review and focused test |
| Unknown seam | One read-only scout when isolated discovery saves work |
| Independent evidence | Start with at most two parallel readers; expand only for an unresolved question |
| Scoped implementation | One writer per checkout; parallel writers need separate managed worktrees |
| Security/data-integrity or consequential cross-module change | Independent fresh-context review plus actual verification |

Use fresh child context, relevant paths/scenarios, explicit authority and compact evidence. Reuse a child for its refinement; prefer async completion notifications over polling. Inside Paseo, create visible Paseo children rather than hidden native Pi subprocesses. Concrete model routing remains user/project policy, not a hard-coded installer default.

The reference prompt was reduced from 6,360 to 4,123 characters (35.2%) while retaining trust and verification rules. That measures prompt size, **not runtime speed or quality**. The installer does not overwrite `~/.paseo/config.json` or user `AGENTS.md`; adopting the reference is an explicit local configuration change. New sessions load changed instructions; already-running sessions can retain earlier context.

The current local rollout also uses a temporary five-real-task journal at `~/.megai/measurements/pi-five-task-pilot.md`: boundary time, attributable parent/child tokens, observed waiting, correction cycles, acceptance evidence and regressions. Missing data stays unknown; unlike task types and policy-changing rollouts are not treated as comparable baselines. This journal is local, not installed by the default pipeline or committed with session data, and makes no automatic model/test changes.

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

### Performance without weakening task quality

- Core startup retains memory, codedb and local zvec-grep. Codedb warms its index with its supported `<root> tree` command, not a nonexistent `index` subcommand.
- Graphify and RepoWise indexing is **on demand**: `megai graph` or `repowise init --yes --no-prose --no-claude-md`. To explicitly restore both startup jobs, use `MEGAI_SPECIALIST_INDEXES=1 megai pi`. Existing graphs/indexes are preserved.
- Caveman installation is opt-in with `MEGAI_CAVEMAN=1 megai install`. Pi wiring excludes global `caveman*`, `cavecrew`, and `smart-development-orchestrator` skills; it does not delete shared skill files or add Ponytail. Use `pi config` to change skill selection. Project-local copies are separate resources and need separate review.
- Shell bridges are installed on PATH; `symbol` maps to codedb `find`, and memory HTTP requests have a 3-second connection / 15-second total limit. Memory still needs its local daemon (`megai start agent-memory`).
- Models, thinking, authentication, trust, tests and review requirements are not performance shortcuts. Native standalone Pi delegation remains available when its optional package is enabled; Paseo sessions use Paseo delegation.

Run `bash tests/pi-runtime.sh`, `bash tests/pi-task-flow.sh`, and `bash tests/pi-performance.sh`. See [the scoped audit](docs/audits/pi-quality-performance.md) for evidence and limitations. Fewer prompt characters or background launches are not a measured end-to-end speedup. Existing sessions need `/reload` or a new session to load changed skills; compaction alone is not a configuration reload.

### Optional parent/worker model composition

The [parent-only routing reference](skills/model-composition/routing.md) keeps **Astra/high** as the user-facing decision owner, uses **MiniMax M3/high** for bounded routine implementation (**low** for discovery), **Luna/high** for high-risk implementation/fallback, and **Sol/high** for complex debugging and risk-based independent review. Tiny work stays direct; this is not a mandatory four-model chain.

Opt in by pointing parent instructions to `$MEGAI_HOME/skills/model-composition/routing.md` and selecting `openai-codex/gpt-6-astra` / `high` as the parent default. The reference ships with MEGAI's existing skill assets but is not auto-loaded as another skill or automatically enabled for other installations. No credentials or provider endpoints are installed. M3 requires the existing direct MiniMax provider and public or explicitly approved non-sensitive context; uncertain/private workloads keep the established GPT route. Repository restrictions always win.

`python3 tests/model-composition.py` checks policy structure, not model intelligence. The optional `--live` check validates this local rollout's parent defaults, instruction pointer and source parity without contacting providers. Availability was checked in the local catalog; authenticated M3 execution, comparable task TPS and acceptance/correction performance still need real-work evidence. Do not label this a benchmark-proven "ideal" composition.

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
│   Claude Code     │ │   Codex / Pi    │ │      OMP        │
│ MCP/hooks/plugins │ │ MCP/skills/exts │ │ MCP/skills      │
└───────────────────┘ └─────────────────┘ └─────────────────┘
```

The installer:

1. 🔍 Detects OS, architecture, and runtimes.
2. 📦 Installs or reuses each tool.
3. 🧾 Records paths, ports, and versions in `~/.megai/state.json`.
4. 🔌 Wires the core MCP pair into Claude Code, Codex, and OMP; Pi uses lightweight memory/codedb extensions plus a global zvec-grep MCP entry.
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
│   ├── zg
│   ├── graphify
│   └── repowise
├── lib/                         installer and wiring scripts
├── pi-skill/                    Pi MEGAI skill and extensions
├── omp-skill/                   OMP-native MEGAI skill
├── task-flow/                   skills, hooks, commands, and monitor
├── skills/numasec-security/     authorized security handoff guidance
├── skills/megai-openspec/       optional parent-owned Pi spec workflow
├── skills/agent-worktree-lifecycle/  dev delivery, one promotion request, approved main merge
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

This refreshes supported tools, global skills, integrations, and MCP wiring without replacing unrelated user configuration. OpenSpec remains separately opt-in and pinned: after fetching new MEGAI source, rerun its optional installer to refresh the bridge. Neither `megai update` nor the normal install pipeline automatically upgrades the OpenSpec CLI.

---

## 🩺 Verification and troubleshooting

### Check installation state

```bash
megai status
megai doctor
```

A healthy installation reports the core CLIs, agent configuration files, agent-memory daemon, global UX/UI and Numasec skills, RepoWise, Argent, and Numasec.

### Useful checks

```bash
megai start agent-memory       # restart persistent memory
megai reindex                  # rebuild codedb and zvec-grep indexes for this project
zg status --check-ready        # verify the current workspace hybrid index
megai wire pi                  # repair Pi skills/extensions and global zvec-grep MCP entry
megai wire codex               # repair Codex MCP block
megai wire cc                  # repair Claude MCP entries
megai logs repowise            # inspect background RepoWise indexing
```

### Focused OpenSpec and orchestration checks

From the MEGAI source checkout:

```bash
bash tests/openspec-integration.sh  # offline installer lifecycle and preservation
bash tests/openspec-policy.sh       # static boundaries and negative mutations
bash tests/openspec-contract.sh     # real installed OpenSpec 1.12.0 contract
bash tests/pi-task-flow.sh          # Asana handoff and Pi wiring regressions
bash tests/orchestration-policy.sh  # shared prompt guardrails
```

The real-CLI test uses temporary project/config directories with telemetry disabled. It verifies injected guidance, rejects malformed requirements, and demonstrates that planning completion does not mean implementation tasks passed. These checks validate integration contracts; they do not guarantee future model compliance or replace task-specific tests.

### Common requirements

- 🍎 macOS or 🐧 Linux; Windows users should use WSL
- `curl`
- Node.js `22+`
- Python 3 and `pipx`
- `jq`
- `uv` for RepoWise installation
- `ripgrep`

The installer resolves supported missing dependencies where possible and reports anything that still needs manual action.

---

## 🔐 Security and privacy

- 🔑 MEGAI does not bundle or commit provider credentials.
- 🧩 Skills and plugins run with agent permissions; review third-party skill sources before use.
- 💾 Configuration files are backed up before MEGAI changes them.
- 🧱 Only MEGAI-owned MCP entries and marked blocks are replaced or removed.
- 🏠 agent-memory, zvec-grep, and RepoWise services and indexes run locally by default; zvec-grep remote Embedding requires separate explicit authorization.
- 🛡️ Numasec execution is opt-in and must stay within an explicitly authorized target scope.
- 📝 OpenSpec installation is pinned, disables npm lifecycle scripts and upstream telemetry, and initializes no repositories automatically. Specs and evidence stay in the chosen repository; archive is not a test or release authorization.

---

## Retiring a legacy Ix installation

Ix is no longer installed, updated, checked or recommended by MEGAI. Upgrading does not silently delete its independently installed runtime or graph data. On a previously installed host:

1. Close old agent sessions so cached plugins/hooks cannot continue running. Back up any customized plugin assets before uninstalling them.
2. Remove only the Ix plugins using the installed clients (skip absent clients/plugins):
   ```bash
   claude plugin uninstall ix-memory@ix-claude-plugin --scope user --keep-data
   codex plugin remove ix-memory@ix-codex-plugin
   ```
3. Preview and apply the bundled legacy-registration cleanup (Python 3.11+):
   ```bash
   python3 "$HOME/.megai/lib/retire_ix.py"
   python3 "$HOME/.megai/lib/retire_ix.py" --apply
   ```
   It backs up changed files under `~/.megai/backups/ix-retirement/` with a restore manifest, removes exact known global Ix Codex hook commands/MCP/local marketplace entries and Claude plugin registrations, and retires recognized MEGAI installer/shim/state leftovers. Unrelated hooks, MCP servers and configuration are preserved. Custom entries and symlinked configs require manual review; malformed configs stop the operation before writes. Keep these private backups outside MEGAI before running `megai uninstall` if you need them later.
4. Inspect `~/.ix/backend/docker-compose.yml` and the containers' Compose labels first. If they identify only your Ix backend, stop/remove that stack with `docker compose -f "$HOME/.ix/backend/docker-compose.yml" down` **without `-v`**. Never remove a shared Compose project by name alone. Archive `~/.ix`, its verified launcher, and remaining Ix-only plugin/hooks/MCP assets after detaching them; do not delete shared `.codex/hooks` or `.codex/mcp` directories. The helper intentionally does not stop Docker, delete runtime files, or scan other projects. Check for additional launchers with `type -a ix`; if Homebrew's installed `ix` formula identifies `https://github.com/ix-infrastructure/Ix`, remove that formula with `HOMEBREW_NO_AUTOREMOVE=1 HOMEBREW_NO_AUTO_UPDATE=1 brew uninstall ix`. Do not remove an unrelated tool merely because it has the same name; retain shared Node dependencies.
5. Reopen agents with the updated MEGAI skill (`megai wire pi` / `megai wire omp`), inspect customized/project-local Ix hooks separately, and check `command -v ix`, `codedb --version`, `zg --version`, `rg --version` and `megai doctor`. The first command should no longer find an active Ix launcher after runtime retirement. Graph volumes remain available for recovery.

`python3 tests/ix-retirement.py`, `bash tests/mcp-wiring.sh` and `bash tests/zvec-grep-integration.sh` verify retirement and preserved search wiring in sandboxes. To undo a helper run, restore only the listed original files/symlinks from its manifest after reconciling any later edits; restore the archived runtime separately if needed.

## 🗑️ Uninstall

```bash
megai uninstall
```

MEGAI removes its home directory and reverts MEGAI-managed MCP entries, task-flow pieces, UX/UI, Numasec and registered OpenSpec skill links, shell PATH entries, and ui-craft components. The Numasec and OpenSpec CLIs are retained to avoid deleting independently usable tools; OpenSpec project artifacts and privacy settings are also retained.

To prevent data loss, zvec-grep, RepoWise, and their local project indexes are retained. Remove them separately only when their data is no longer needed:

```bash
npm uninstall -g @zvec/zvec-grep
uv tool uninstall repowise
```

Delete a project's `.zvec-grep/` or `.repowise/` directory manually if you also want to remove its generated index.

---

## 📄 License

MEGAI is released under the [MIT License](LICENSE).

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
  Memory · code intelligence · indexing · bounded orchestration · task flow · UI/UX · app testing
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
- [📋 task-flow and Plane](#-task-flow-and-plane)
- [🎨 Design and UI/UX stack](#-design-and-uiux-stack)
- [🗃️ Code intelligence and memory](#️-code-intelligence-and-memory)
- [🧪 App testing](#-app-testing)
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

MEGAI starts or verifies agent-memory, builds codedb structural and zvec-grep hybrid indexes, optionally prepares the knowledge graph, checks token-saving tools, and prints a project-specific guide.

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
- 🔄 **Parent-owned Plane boundaries with user-owned completion**
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
| 📋 | task-flow | `.todos` board, priority queue, ADLC, monitoring, Plane mirror | Claude hooks + global skills |
| 🌿 | agent-worktree-lifecycle | Task worktrees → `dev`; one open promotion PR; user-approved `main` merge | Global policy + `megai dev`/`finish`/`promote` |
| 🧭 | smart-development-orchestrator | GPT writer routing, MiniMax read-only discovery, Paseo worktree delivery | Global skill + OMP agents |
| ⚙️ | GPT-core + MiniMax-discovery routing | GPT owns every write; MiniMax only searches, reads, and finds code | OMP roles + managed agents |
| 🖌️ | [ux-ui-agent-skills](https://github.com/plugin87/ux-ui-agent-skills) | 17 UI/UX skills, WCAG references, tokens, components, adapters | Global skills |
| 🧪 | [Argent](https://github.com/software-mansion/argent) | Explicit `/argent` mobile, TV, Electron, and Chromium review | Slash command + on-demand CLI |
| 🐍 | [Ruff](https://docs.astral.sh/ruff/) | Extremely fast Python linter and formatter | Reused on PATH or installed via `uv tool` / `pipx` |
| 🛠️ | [Matt Pocock's skills](https://github.com/mattpocock/skills) | Specs, TDD, diagnosis, review, domain modeling, architecture, and delivery flows | Global skills |

---

## 🤖 Agent integrations

### 🟠 Claude Code

MEGAI configures:

- lean default MCP surface in `~/.claude.json`: `agentmemory` and `codedb`
- Argent CLI available on demand
- `rtk` `PreToolUse` hook
- graphify skills; Caveman only when explicitly installed
- task-flow skill, hooks, commands, monitoring, optional statusline, and safe `dev` merge/worktree cleanup policy
- global Matt Pocock and UX/UI skills

Existing MCP servers, hooks, and statusline settings are preserved.

### 🔵 OpenAI Codex

MEGAI configures:

- a lean, marked MCP block in `~/.codex/config.toml` with `agentmemory` and `codedb`
- Argent CLI available on demand
- graphify, Matt Pocock, UX/UI, and safe worktree-lifecycle skills; Caveman is optional

Only MEGAI-owned MCP tables are replaced or removed; unrelated Codex configuration remains intact.

### 🟣 Pi

MEGAI configures:

- global MEGAI skill at `~/.pi/agent/skills/megai.md`
- Plane-aware task-flow and safe worktree-lifecycle skills under `~/.pi/agent/skills/`
- `megai-memory` and `megai-codedb` CLI bridges in `~/.megai/bin` (not shell files masquerading as Pi extensions)
- a global `zvec_grep` MCP entry in `~/.pi/agent/mcp.json` for semantic and hybrid workspace retrieval
- Argent CLI available on demand instead of a permanent MCP entry
- global UX/UI, graphify, and Matt Pocock skills; redundant Caveman/Cavecrew and legacy OMP-routing skills excluded from global Pi discovery
- the first authenticated model as the global default when no valid default exists

Pi keeps provider authentication in `~/.pi/agent/auth.json`; MEGAI never writes credentials.

#### Retired: OpenSpec

The optional installer and global OpenSpec skill are retired. Existing `openspec/` specifications, checklists and privacy settings remain. `bash "$HOME/.megai/lib/retire_openspec.sh"` removes only registered MEGAI-owned Pi links and state, including stale links from older installations; it cannot install or invoke OpenSpec. See [retirement verification and rollback](docs/audits/openspec-retirement.md).

### ⚪ Oh My Pi (OMP)

MEGAI configures:

- native MCP entries for `agentmemory` and `codedb` in the active OMP profile
- native MEGAI, Plane-aware task-flow, safe worktree-lifecycle, and smart-development-orchestrator skills under the active profile's `skills/` directory
- MiniMax read-only `smart-router`, trusted Luna/Terra scouts, and GPT `gpt-core-worker`/`gpt-fast-worker` implementations under the active profile's `agents/` directory
- OMP's native MiniMax catalog and provider-specific transport compatibility; MEGAI never rewrites user `models.yml`
- preservation of unrelated OMP servers, model providers, allowlists, denylists, credentials, agents, and user settings
- hybrid Paseo placement: each writer receives a managed worktree from `dev`, then is archived after verified dev merge/push, one open promotion request, and worktree cleanup
- Argent and global skills through OMP's existing CLI and skill discovery surfaces

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

## 📋 task-flow and Plane

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

### 🔗 Boundary-only Plane mapping

The Plane-aware `megai-task-flow` skill used by Pi and OMP synchronizes only at boundaries. The parent starts a linked work item before project edits; questions and read-only investigation need no task. Consume all paginated project and work-item pages and require exactly one match; retain the `(project UUID, work item UUID)` pair. Imported work matches `external_id` plus `external_source=asana-migration-v1`; preserve the original `<!-- asana:GID -->` marker verbatim until the Plane pair is confirmed.

| Boundary | `.todos` | Plane state group | Agent action |
| --- | --- | --- | --- |
| Start | `inprogress.md` | started `In Progress` | one start mutation |
| Verified agent handoff | `inprogress.md`, unchecked and labelled In Review | started `In Review` | one handoff mutation |
| User marks Done; reconcile | `done.md` | completed state | user only |

Only the user may mark Done. Store the identity pair in an HTML comment and reuse it for follow-ups; an active task needs no per-edit skill reload or repeated start mutation. Skip routine stage sync, milestone comments and unchanged board rereads; the queue never auto-drains. Standalone Claude board hooks are a separate integration and remain subject to repository/user policy.

### 🌿 Agent branch delivery and promotion

Primary development defaults to `dev`; isolated task branches start from `dev`. Tracked MEGAI handoff is mandatory-gated: after verification/self-review, record each worker's Paseo workspace ID/worktree/branch/reported tip and exact-tip+clean proof, then serially run `megai finish --verified --target dev` once from each current-task worker because `finish` handles one current worktree per invocation. The calls merge and push all safely mergeable current-task branches. Reconcile after any nonzero call because `dev` may have advanced. Perform a complete lookup proving exactly one open `dev` → `main` request—`finish`'s first result is not cardinality proof—then clean safely merged task worktrees/branches, archive each corresponding Paseo workspace, and pass the final current-task inventory gate. Missing push, request, cleanup, or archive blocks Plane `In Review`; orphan task-local branches require explicit ownership, merged-tip proof, and non-force `git branch -d` deletion. Preserve primary/orchestrator/dev/main and unrelated, dirty, unmerged, failed, or ambiguous work. The agent asks whether to promote main and runs `megai promote --approved` only after an explicit affirmative reply. Promotion verifies the reviewed head and clean forge state, merges the request, synchronizes `main`, and preserves `dev`.

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

ui-craft is retired: MEGAI no longer installs, updates, wires, checks or uninstalls it. Existing project `.ui-craft/` design notes remain private and preserved; unrelated UX/UI skills are unchanged. For existing installations, review the [retirement evidence and rollback guidance](docs/audits/ui-craft-retirement.md). Do not trust ui-craft 1.0.3's `uninstall --dry-run`: that release ignores the flag and performs removal.

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

### Retired: Dembrandt

MEGAI no longer installs, updates or recommends Dembrandt. Existing design outputs and shared browser caches are preserved. Only stale MEGAI-owned MCP registrations are cleaned up; user-owned entries remain. See [retirement verification and rollback](docs/audits/dembrandt-retirement.md).

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

### Retired: RepoWise

MEGAI no longer installs, updates, starts or recommends RepoWise. Existing `.repowise/` indexes and logs remain untouched. Compatibility cleanup still removes only old MEGAI-owned MCP registrations, preserving user-owned entries. See [retirement verification and rollback](docs/audits/repowise-retirement.md).

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

## Retired: Numasec

Numasec and the `megai security` launcher are retired. Existing reports, user settings and project files remain. `bash "$HOME/.megai/lib/retire_numasec.sh"` cleans only known MEGAI-owned skill links and its state entry; it cannot install or invoke Numasec. Security and authorization requirements still apply to all work. See [retirement verification and rollback](docs/audits/numasec-retirement.md).

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
| `pi-mcp-adapter` | lazy MCP proxy; individual tool schemas are opt-in |

Optional extensions are available through the full profile:

```bash
MEGAI_PI_FULL=1 megai install
```

The full profile also enables `@narumitw/pi-statusline`, `@vigolium/piolium`, `pi-web-access`, `pi-subagents`, `bigpowers`, `@dietrichgebert/ponytail`, and `pi-lens`. Without `MEGAI_PI_FULL=1`, repeated installs remove only those MEGAI-owned optional entries from Pi's startup list; unrelated user packages are preserved.

### Performance without weakening task quality

- `megai pi` starts lean: no automatic memory daemon, codedb/zvec prewarming, or specialist indexing. Worktree/branch safety and wiring remain. Use `MEGAI_PI_FULL=1 megai pi` only when core prewarming is useful; other harness launch behavior is unchanged.
- Retrieval tools remain available on demand: `rg`, `megai-codedb`, `zg`; explicit memory uses `megai start agent-memory`. Graphify remains on demand. Restoring its startup job requires both `MEGAI_PI_FULL=1 MEGAI_SPECIALIST_INDEXES=1 megai pi`. Existing data and indexes are preserved.
- Caveman installation is opt-in with `MEGAI_CAVEMAN=1 megai install`. Pi wiring excludes global `caveman*`, `cavecrew`, and `smart-development-orchestrator` skills; it does not delete shared skill files or add Ponytail. Use `pi config` to change skill selection. Project-local copies are separate resources and need separate review.
- Shell bridges are installed on PATH; `symbol` maps to codedb `find`, and memory HTTP requests have a 3-second connection / 15-second total limit. Memory still needs its local daemon (`megai start agent-memory`).
- Models, thinking, authentication, trust, tests and review requirements are not performance shortcuts. Native standalone Pi delegation remains available when its optional package is enabled; Paseo sessions use Paseo delegation.

Run `bash tests/pi-runtime.sh`, `bash tests/pi-task-flow.sh`, and `bash tests/pi-performance.sh`. See [the scoped audit](docs/audits/pi-quality-performance.md) for evidence and limitations. Fewer prompt characters or background launches are not a measured end-to-end speedup. Existing sessions need `/reload` or a new session to load changed skills; compaction alone is not a configuration reload.

### Lean GPT execution

The [parent-only routing reference](skills/model-composition/routing.md) uses **Astra/high** with direct tools for bounded tasks. Delegate only when it saves work: **Luna/medium** discovery, **Luna/high** implementation, **Sol/high** complex debugging or required independent review. No MiniMax route, automatic review chain or repeated parent/worker implementation. Preserve tests, trust, security review, tracker and main-approval boundaries.

The user-approved local profile removes native pi-subagents from startup, selects only core engineering/task skills, and disables optional Pencil/Headroom/codebase-memory MCP entries without deleting shared tools or data. It retains the lazy tracker and zvec proxy. Optional specialist skills remain on disk for explicit requests. This local selection is not imposed on other users by the installer; their unrelated package/skill preferences remain intact. Native delegation, if explicitly re-enabled, has strict GPT-only scopes. Paseo dispatch separately specifies its model/thinking.

`python3 tests/model-composition.py --live` verifies local GPT defaults, lean settings and policy parity, not model quality. See [the lean rollout evidence](docs/audits/lean-gpt-runtime.md). Reduced resource counts do not prove token savings, faster completion or unchanged quality. Use a **new Pi session** to shed old context and removed tool schemas; `/reload` refreshes resources but cannot erase the history of a long session.

---

## 🏗️ How it works

```text
                    ┌─────────────────────┐
                    │   curl install.sh   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  ~/.megai/lib/main  │
                    │  13-step pipeline   │
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
├── lib/                         installer and wiring scripts
├── pi-skill/                    Pi MEGAI skill and extensions
├── omp-skill/                   OMP-native MEGAI skill
├── task-flow/                   skills, hooks, commands, and monitor
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

Ruff is reused on PATH when present, otherwise installed via `uv tool install ruff` or `pipx install ruff`. The MEGAI Pi skill exposes non-mutating Python validation only — run on task-changed `.py`/`.pyi` files with `ruff check --no-fix --no-fix-only --force-exclude --no-cache -- <files>` and `ruff format --check --force-exclude --no-cache -- <files>` when the project's formatting fits Ruff conventions. No project-wide cleanup, no `--fix`, no config writes.

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

A healthy installation reports the core CLIs, agent configuration files, agent-memory daemon, global UX/UI skills and Argent.

### Useful checks

```bash
megai start agent-memory       # restart persistent memory
megai reindex                  # rebuild codedb and zvec-grep indexes for this project
zg status --check-ready        # verify the current workspace hybrid index
megai wire pi                  # repair Pi skills/extensions and global zvec-grep MCP entry
megai wire codex               # repair Codex MCP block
megai wire cc                  # repair Claude MCP entries
```

### Plane MCP and explicit tracker cutover

Configure the official Plane hosted MCP for Pi and Codex without putting the API token in
MCP JSON, shell arguments, or logs. Install the pinned bridge as a separate,
credential-free preflight; runtime never downloads packages. The private receipt verifies
Node, the lockfile and the complete installed dependency tree (including imported chunks).
Trusted root-owned, non-writable system Node executables are supported. Reinstall the bridge
after an intentional Node or dependency update to renew its receipt:

```bash
megai plane bridge install
megai plane setup --workspace SLUG \
  --token-file ~/.config/megai/credentials/plane-api-token \
  --client all --replace-asana
megai plane status --client all
megai plane remove --client all
megai plane restore --client all
```

The token file must be owner-readable only and is checked again at each request/bridge
launch. Setup is idempotent, stages every requested client before replacement, preserves
unrelated settings, and manages only MEGAI-owned Plane entries. `megai wire pi` and
`megai update` preserve an existing Plane setup without starting authentication. The
explicit `--replace-asana` flag removes local Asana entries only after private,
target-bound backups are created; setup remains additive without that flag. Restore is
connector-only: it restores the matching client/profile backup and leaves task-flow
policy/`AGENTS.md` backups untouched. It never changes remote Plane or historical Asana data.

The [historical one-off import checkpoint](docs/one-off-import-checkpoint.md) is retained
as unwired source, not an active Asana integration. Its verifier reports partial evidence,
not full migration parity; no live import runs during installation or branch consolidation.

### Focused retirement and orchestration checks

From the MEGAI source checkout:

```bash
bash tests/openspec-integration.sh  # offline retired-link cleanup and preservation
bash tests/pi-task-flow.sh          # Plane handoff and Pi wiring regressions
bash tests/plane-mcp.sh             # Pi/Codex connector lifecycle and rollback
bash tests/plane-cutover-regressions.sh # Runtime integrity and safe uninstall
bash tests/orchestration-policy.sh  # shared prompt guardrails
```

The retirement test uses temporary directories and requires no OpenSpec installation. It checks owned and foreign links, malformed state and preserved project specifications. These checks do not replace task-specific tests.

### Common requirements

- 🍎 macOS or 🐧 Linux; Windows users should use WSL
- `curl`
- Node.js `22+`
- Python 3 and `pipx`
- `jq`
- `uv` or `pipx` for isolated Python tool installation
- `ripgrep`

Ruff needs `uv` or `pipx` only when no working `ruff` is already on `PATH`; an existing Python-managed or system install is reused untouched.

The installer resolves supported missing dependencies where possible and reports anything that still needs manual action.

---

## 🔐 Security and privacy

- 🔑 MEGAI does not bundle or commit provider credentials.
- 🧩 Skills and plugins run with agent permissions; review third-party skill sources before use.
- 💾 Configuration files are backed up before MEGAI changes them.
- 🧱 Only MEGAI-owned MCP entries and marked blocks are replaced or removed.
- 🏠 agent-memory and zvec-grep services and indexes run locally by default; zvec-grep remote Embedding requires separate explicit authorization.

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

MEGAI removes its home directory and reverts MEGAI-managed MCP entries, task-flow pieces, UX/UI, legacy owned Numasec/OpenSpec links, and shell PATH entries. Independently installed CLIs, project artifacts and privacy settings are retained; legacy-link cleanup never installs OpenSpec.

To prevent data loss, zvec-grep and local project indexes are retained. ui-craft and RepoWise are retired, but their project data is not deleted. Remove retained tools separately only when no longer needed:

```bash
npm uninstall -g @zvec/zvec-grep
```

Delete a project's `.zvec-grep/` or `.repowise/` directory manually if you also want to remove its generated index.

---

## 📄 License

MEGAI is released under the [MIT License](LICENSE).

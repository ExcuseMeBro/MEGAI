# 🥧 Pi config: latest snapshot

> The live Pi setup, ready to restore on a new Mac with one command.
> **Pi 1.5.2** and **Pi-Bolt 1.2.1** share `~/.pi/agent`, so both get the same config.

| | |
|---|---|
| 🧠 Default model | `openai/gpt-6.1-sol` |
| 💭 Thinking | `xhigh` for gpt-6.1-sol, `high` for other models (`modelThinkingLevels`) |
| 🎨 UI work | `APPEND_SYSTEM.md` routes to one design skill, then `ai-design-check` |
| 🤖 Codex CLI | `codex/` → `~/.codex`: gpt-6.1-sol `xhigh`, no approvals, full-access sandbox, same quality and design rules |
| 🐍 Main tool | `ipython`, Unharnessed's persistent Python REPL |
| 🛡️ Safety | every ipython cell passes through `megai-action-boundary` |
| 🧩 Contents | 6 extensions · 76 skills · 3 prompts · 3 MCP servers |
| 🌱 History | none: each update replaces the single commit |

---

## 🚀 New Mac: one command

```sh
curl -fsSL https://raw.githubusercontent.com/ExcuseMeBro/MEGAI/pi/install.sh | bash
```

✅ **Needs:** macOS on Apple silicon and the Xcode Command Line Tools (`xcode-select --install`).
🙅 **Does not need:** sudo or Homebrew. Everything installs per user.

### 📦 What the script does

| | Step | Details |
|---|---|---|
| 🟢 | **Node 22** | From nodejs.org, checksum verified, into `~/.local/share/pi-node`. Skipped when a recent Node exists. |
| 🥧 | **Pi** | Official `pi.dev` installer. It always installs the latest version; the script warns if that differs from `versions.env`. |
| ⚡ | **Pi-Bolt** | Official `pi-bolt.opensec.in` installer, pinned to `PIBOLT_VERSION`. |
| ⚙️ | **Config** | `agent/` into `~/.pi/agent`, and `extras/config` into `~/.config`. |
| 📚 | **Pi packages** | `npm ci` from the lockfile: exact versions, with the same peer handling Pi uses. |
| 🔌 | **MCP servers** | agentmemory and figma-console from their lockfiles. brokan builds with `cargo install --locked` at a pinned revision; rustup is installed if needed. |
| 🐍 | **ipython kernel** | uv + Python 3.12, pinned `requirements.txt`, and `unharnessed-runtime` at a pinned Unharnessed commit. |
| 🧹 | **megai-task-resources** | Installed from MEGAI `dev`. |
| 🛣️ | **PATH** | Adds `~/.local/bin` to `~/.zprofile` if it is missing. |

🔁 **Safe to run again.**
- Existing config is backed up to `~/.pi/agent/backups/pre-restore-*`.
- Credentials, sessions and trust decisions are never touched.

⏭️ **Skip steps** by naming them in `PI_RESTORE_SKIP`, for example:

```sh
PI_RESTORE_SKIP=brokan,megai bash install.sh
```

Step names: `pi` · `pibolt` · `config` · `codex` · `packages` · `mcp` · `brokan` · `kernel` · `megai`.

### 🔑 Afterwards: logins (you do these)

The script prints this list at the end:

1. 🤖 Run `pi-bolt`, then `/login`, then choose **OpenAI** and sign in with ChatGPT.
2. 🌌 Sign in to the Antigravity accounts again from inside Pi.
3. 🎨 Figma MCP: `echo 'export FIGMA_ACCESS_TOKEN=figd_...' >> ~/.zshrc`
4. 🔐 OAuth MCP servers: `/mcp` inside Pi.
5. 📋 brokan: run `brokan service install`, and turn on board Sync in its Settings.
6. 🧠 agentmemory starts its engine on first use. Memories are not copied over.
7. 🤖 Codex CLI: `codex login`. Its config runs with no approvals and no sandbox, so use it in git repos.

---

## 🗂️ What is inside

```
agent/                 → ~/.pi/agent
├── settings.json      model, tools, packages, skill & prompt allowlists
├── AGENTS.md          global agent instructions
├── APPEND_SYSTEM.md   system prompt addendum
├── defaults/          ORCHESTRATOR.md, AGENTS.md, verify.mjs
├── extensions/        🛡️ megai-action-boundary · 🔁 megai-keep-going · ✂️ megai-lean-prompt
│                      📏 megai-project-size · 🔎 tgrep · 🐍 ipython
├── prompts/           mdev · prdev · rwbrowser
├── skills/            76 skills
├── mcp.json           brokan · agentmemory · figma-console
├── npm/               package.json + package-lock.json
└── uh-kernel/         requirements.txt + SOURCE (kernel recipe)
extras/
├── agentmemory-package/   lockfile for the agentmemory MCP
├── figma-console-mcp/     lockfile for the Figma MCP
└── config/billion-context/billion-context.json   subagents off, no auto-update
codex/                 → ~/.codex: config.toml (tokens as ${VAR}), AGENTS.md, keep-going Stop hook
versions.env           pinned versions and revisions
install.sh             🚀 restore
export.sh              📸 snapshot
```

### 🐍 About the ipython default

`settings.json` sets `"defaultTools": ["read", "codemode"]`:

- ❌ The built-in `bash`, `edit` and `write` tools are off.
- 🐍 The `ipython` extension tool does that work: files, shell through `bash()`, and data.
- 📖 `read` stays, so Pi keeps listing skills.
- 🧩 Extension tools stay on: tgrep, web, memory and image.

Why: on 34 Aider polyglot Python exercises, ipython solved 28/34 against 27/34, with **34% fewer tokens** and 20% fewer turns.

### 🔒 What is *not* here, on purpose

| | Excluded |
|---|---|
| 🔑 | `auth.json`, `antigravity-accounts.json`, `mcp-auth.json` (credentials) |
| 💬 | `sessions/` (conversations), `trust.json` |
| 🗃️ | `models-store.json`, `backups/`, `install/`, `bin/`, caches |
| 🧠 | `~/.agentmemory` data, `~/.pi/helpers` (project scripts), the old `~/.config/pi-agy-lean` profile |

In `mcp.json`:
- Secret env values are stored as `${VAR}` placeholders.
- `__HOME__` and `__NODE__` are filled in at install time.
- `deviceId` is removed from `settings.json`.

---

## 📸 Updating the snapshot (on the source Mac)

```sh
./export.sh    # regenerates agent/, extras/ and versions.env from the live setup
```

🚨 `export.sh` **refuses to finish** if any credential value from the live auth files ends up in the snapshot. Once it passes, commit and push as a single commit.

---

## ✅ How it was verified

The script was run into an **empty `$HOME`** with a minimal PATH and Homebrew hidden, as on a brand-new Mac:

- 🥧 Pi 1.5.2 and ⚡ Pi-Bolt 1.2.1 installed and ran.
- 📄 Config files are **byte-identical** to the source. The only exceptions are the node path and the Figma token placeholder.
- 📚 The Pi package and Figma npm trees are identical. agentmemory gets 3 extra optional wasm fallback packages, which are harmless.
- 🐍 The kernel's packages are identical.
- 🧪 Pi-Bolt ran a real `ipython` cell, and its tool list matched the source Mac.
- ⚠️ The brokan Rust build was **not** run in the test because host memory was low. Its pinned revision and `Cargo.lock` were confirmed on GitHub.

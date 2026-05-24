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

# MEGAI

Zero-config one-line installer for the AI agent stack: **Fusion** + **agent-memory** + **codedb** + **cocoindex** + **caveman** + **rtk** + **graphify**, auto-wired into **Claude Code**, **Codex**, and **Pi**.

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
|------|------|
| [Fusion](https://runfusion.ai) | Multi-node agent orchestrator (`fn` CLI) |
| [agent-memory](https://www.agent-memory.dev/) | Persistent memory MCP server (53 tools, port 3111) |
| [codedb](https://github.com/justrach/codedb) | Code intelligence MCP server (16 tools, Zig binary) |
| [cocoindex](https://cocoindex.io) | Incremental indexing pipeline (Python) |
| [caveman](https://github.com/JuliusBrussee/caveman) | Token-compression skill (~65% savings, auto-activates in cc/codex/pi) |
| [rtk](https://github.com/rtk-ai/rtk) | Rust Token Killer — CLI output proxy (~60–90% savings, hooks into cc) |
| [graphify](https://graphify.net) | Knowledge-graph skill for codebases (Tree-sitter + NetworkX + Leiden). `/graphify .` inside cc/codex/pi |

## Using Fusion (the orchestrator UI)

`megai cc` (or `codex` / `pi` / `fusion`) starts `fn dashboard` in the background, parses its URL from the log, prints it, and opens your default browser. Disable auto-open with `MEGAI_NO_BROWSER=1 megai cc`.

```bash
megai cc                  # boots Fusion + opens browser + launches Claude Code
megai fusion              # Fusion only (tails the log; dashboard keeps running)
megai stop fusion         # kill the dashboard
megai logs fusion         # tail
```

Inside Fusion, the day-to-day commands are:

```bash
fn project add  <name> <path>     # register the folder
fn task create  "fix flaky test"  # create a task
fn task import  owner/repo        # import GitHub issues as tasks
fn mission create                 # build a hierarchical plan from tasks
```

Fusion executes each task in an isolated git worktree and plans / writes / reviews with the agent you launched (`claude`, `codex`, `pi`).

**Wired into:**

- **Claude Code** — MCP servers added to `~/.claude.json`; `rtk` PreToolUse hook registered; `caveman` skill auto-detected
- **Codex** — MCP block added to `~/.codex/config.toml` (markered, idempotent); `caveman` registers itself
- **Pi** — skill + bash extensions installed to `~/.pi/agent/` (Pi has no native MCP); `caveman` self-installs


---

## CLI

```
# default — activate stack for the folder you're in
megai                   # banner + start daemons + index + quick guide

# launch an agent CLI with Fusion dashboard in the background
megai cc                # ensure wired -> start agent-memory + Fusion -> exec `claude`
megai codex             # same, then exec `codex`
megai pi                # same, then exec `pi`
megai fusion            # Fusion dashboard alone
megai graph [path]      # build a graphify knowledge graph -> graphify-out/

# manage
megai install           # re-run installer (idempotent)
megai status            # tool versions, ports, status
megai doctor            # diagnose missing deps and broken configs
megai start agent-memory
megai stop  agent-memory|fusion
megai update            # update all tools
megai wire <cc|codex|pi>  # only re-write MCP config (no launch)
megai logs agent-memory|fusion
megai uninstall
```

---

## Requirements

- macOS or Linux (Windows: use WSL)
- `curl`
- The installer brings in: `jq`, `node` (via `fnm` if missing), `python3` + `pipx`

---

## File layout (post-install)

```
~/.megai/
  bin/megai
  lib/*.sh
  pi-skill/{SKILL.md,extensions/}
  state.json
  logs/
  backups/
```

---

## Uninstall

```bash
megai uninstall
```

Removes `~/.megai/` and reverts megai-managed MCP blocks in `~/.claude.json`, `~/.codex/config.toml`, and `~/.pi/agent/`.

---

## License

MIT

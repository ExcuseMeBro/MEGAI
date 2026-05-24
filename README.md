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

Zero-config one-line installer for the AI agent stack: **Fusion** + **agent-memory** + **codedb** + **cocoindex** + **caveman** + **rtk**, auto-wired into **Claude Code**, **Codex**, and **Pi**.

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

**Wired into:**

- **Claude Code** — MCP servers added to `~/.claude.json`; `rtk` PreToolUse hook registered; `caveman` skill auto-detected
- **Codex** — MCP block added to `~/.codex/config.toml` (markered, idempotent); `caveman` registers itself
- **Pi** — skill + bash extensions installed to `~/.pi/agent/` (Pi has no native MCP); `caveman` self-installs

> Graphify is excluded from v1 (no public release).

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

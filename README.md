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

Zero-config one-line installer for the AI agent stack: **agent-memory** + **codedb** + **cocoindex** + **caveman** + **rtk** + **graphify**, auto-wired into **Claude Code**, **Codex**, and **Pi**.

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
| [agent-memory](https://www.agent-memory.dev/) | Persistent memory MCP server (53 tools, port 3111) |
| [codedb](https://github.com/justrach/codedb) | Code intelligence MCP server (16 tools, Zig binary) |
| [cocoindex](https://cocoindex.io) | Incremental indexing pipeline (Python) |
| [caveman](https://github.com/JuliusBrussee/caveman) | Token-compression skill (~65% savings, auto-activates in cc/codex/pi) |
| [rtk](https://github.com/rtk-ai/rtk) | Rust Token Killer — CLI output proxy (~60–90% savings, hooks into cc) |
| [graphify](https://graphify.net) | Knowledge-graph skill for codebases (Tree-sitter + NetworkX + Leiden). `/graphify .` inside cc/codex/pi |

**Wired into:**

- **Claude Code** — MCP servers added to `~/.claude.json`; `rtk` PreToolUse hook registered; `caveman` + `graphify` skills auto-detected
- **Codex** — MCP block added to `~/.codex/config.toml` (markered, idempotent); `caveman` + `graphify` register themselves
- **Pi** — skill + bash extensions installed to `~/.pi/agent/` (Pi has no native MCP); `caveman` + `graphify` self-install


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

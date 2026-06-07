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

Zero-config one-line installer for the AI agent stack: **agent-memory** + **codedb** + **cocoindex** + **caveman** + **rtk** + **graphify** + **task-flow**, auto-wired into **Claude Code**, **Codex**, and **Pi**.

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
| task-flow | Priority-driven `.todos` board + full-ADLC protocol skill for Claude Code. Plan → split → queue → execute by priority, shown live in the statusline |

**Wired into:**

- **Claude Code** — MCP servers added to `~/.claude.json`; `rtk` PreToolUse hook registered; `caveman` + `graphify` skills auto-detected; `task-flow` skill + `.todos` board hook + board statusline installed
- **Codex** — MCP block added to `~/.codex/config.toml` (markered, idempotent); `caveman` + `graphify` register themselves
- **Pi** — skill + bash extensions installed to `~/.pi/agent/` (Pi has no native MCP); `caveman` + `graphify` self-install


---

## task-flow — `.todos` board + ADLC

Every project gets a self-managing task board. Claude plans first, splits work into small tasks, queues them by priority, and runs each through the full **ADLC** (AI Development Life Cycle) — no stage skipped.

**Board lives in the project** as plain markdown you can edit by hand:

```
<your-project>/.todos/
  todo.md         # pending      (file = status)
  inprogress.md   # active
  done.md         # completed
```

The `.todos/` files are the **single source of truth** — there is no other task store, so the board, the statusline, and Claude stay in perfect sync.

Each line is a task; priority and ADLC stage are optional prefixes:

```
- [ ] !!!! (generate) Fix the production crash      # urgent, mid-ADLC
- [ ] !!  (spec) Add CSV export                      # medium
- [ ] just clean up the logs                         # no marker = medium
```

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
|-------|-------|---------|
| `task-flow` skill | `~/.claude/skills/task-flow/` | the protocol (auto-invoked for multi-step work) |
| `/ta` command | `~/.claude/commands/ta.md` + `~/.claude/bin/taskflow-add.sh` | `/ta <text>` appends a task straight into `.todos/todo.md` |
| prompt hook | `~/.claude/hooks/taskflow-prompt.sh` | UserPromptSubmit: analyze the prompt → write the task first → run the ADLC |
| session hook | `~/.claude/hooks/taskflow-session.js` | SessionStart: ensures/creates `.todos/` and resumes the board |
| board statusline | `~/.claude/statusline-taskflow.sh` | renders the `.todos` board (set only if you have no statusline) |
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
  task-flow/{skills/,hooks/,bin/,commands/,CLAUDE.snippet.md}
  state.json
  logs/
  backups/
```

---

## Uninstall

```bash
megai uninstall
```

Removes `~/.megai/` and reverts megai-managed blocks in `~/.claude.json`, `~/.codex/config.toml`, `~/.pi/agent/`, and the `task-flow` skill/hook/statusline + CLAUDE.md rule in `~/.claude/`.

---

## License

MIT

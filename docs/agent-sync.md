# Agent sync: Pi → Claude Code and Codex

`megai-agent-sync` makes Claude Code and Codex follow the same working setup as
Pi. Pi's `~/.pi/agent` is the single source; the other two are generated from it.
Change rules, skills, prompts or MCP servers in Pi, then run the sync again.

```bash
python3 scripts/install_agent_sync.py --sync   # install from this repo and sync
megai-agent-sync --check                        # list pending changes, write nothing
megai-agent-sync                                # apply
```

The installer copies `scripts/agent_sync.py` to `~/.local/bin/megai-agent-sync`
and `scripts/agent-hooks/test-guard.mjs` to `~/.local/share/megai-agent-hooks/`.
Both commands are idempotent; a second run prints `in sync`.

## What is synced

| Pi source | Claude Code | Codex |
| --- | --- | --- |
| `AGENTS.md` + `APPEND_SYSTEM.md` | `~/.claude/CLAUDE.md` (generated) | `~/.codex/AGENTS.md` (generated), `project_doc_max_bytes = 65536` |
| skills enabled in `settings.json` | symlinks in `~/.claude/skills` | symlinks in `~/.codex/skills` |
| `prompts/*.md` | `~/.claude/commands/*.md` (`$ARGUMENTS`) | `~/.codex/skills/<name>/SKILL.md` |
| `mcp.json` servers | added with `claude mcp add-json -s user` | appended to `config.toml` |
| `megai-test-guard` extension | `PreToolUse` hook (`Bash`) | `PreToolUse` hook, trusted |
| `megai-keep-going` core | — (Pi applies it to GPT only) | refreshed `~/.codex/hooks/keep-going-core.mjs` |

Details:

- The generated instruction files start with a short preface that maps Pi-only
  mechanics (`codemode`, Pi extensions, `!!`, `tgrep`) for the other agent. The
  `megai:task-resources` block stays intact, so `scripts/install_task_resources.py`
  keeps working on all three files. Do not edit the generated files; edits are
  overwritten.
- Skills are live symlinks, not copies. An existing real skill directory is
  replaced only when it is identical to Pi's or an older subset of it; a divergent
  copy is kept and reported. Links to skills Pi no longer enables are removed;
  other links are left alone.
- Codex 0.171 no longer reads `~/.codex/prompts`, so Pi prompts become skills whose
  description says they run only when the user invokes `/name`.
- Existing MCP servers are never changed. Pi's MCP servers are removed from
  Claude's `deniedMcpServers`; other denials are kept. Claude defers MCP tools,
  like Pi's `exposure: deferred`.
- The hook adapter imports `~/.pi/agent/extensions/megai-test-guard/guard.mjs`
  live. It blocks a `git push` to dev whose range weakens tests (unless a commit
  carries `Test-Change:`) or exceeds `MEGAI_DIFF_LIMIT`. Errors fail open.
- Codex runs a hook only after its hash is trusted (`[hooks.state."<key>"]
  trusted_hash` in `config.toml`). The sync reads the current hashes from
  `codex app-server` (`hooks/list`) and trusts only the MEGAI hooks it manages.

Model, provider and thinking settings are never changed. Pi-only extensions
(Factory, lean-prompt, budget-guard, tgrep, codemode) have no counterpart and are
not synced. A missing `claude` or `codex` CLI skips only the steps that need it.

## Receipts and rollback

Before any write, the previous files are copied to
`~/.pi/agent/local-change-receipts/agent-sync-<timestamp>/` (`before/` for files,
`moved/` for replaced skill directories, `manifest.json` with hashes). Restore by
copying them back; `--check` never writes a receipt.

## Tests

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tests/agent_sync.py
```

The tests use a temporary `HOME` with fake `claude` and `codex` CLIs and a local
bare Git remote; the real home, Claude and Codex are never touched.

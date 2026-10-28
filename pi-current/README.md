# Current Pi configuration — `for-ustama`

Point-in-time, shareable snapshot of the **user-level Pi-Bolt** setup on 2026-10-28. This directory is not an automatic installer. It does not change the active Pi runtime. The previous MEGAI repository source tree, including its old project-level `.pi/` files and OMP artifacts, is not part of this clean-history branch because it is not the current user-level Pi installation. The separate `/Users/bro/PROJECTS/.pi/project.json` belongs to a multi-repository workspace, not the current user-level Pi configuration.

## Included

- `agent/AGENTS.md`: current global agent instructions (the repository's older `pi-defaults/` may differ).
- `agent/settings.json`, `agent/models.json`: selected provider/model/thinking, package, prompt and skill selectors, theme, explicit model definitions. `models.json` currently has an empty providers map.
- `agent/mcp.template.json`: currently configured MCP servers/exposure/tool selectors, **with Authorization headers replaced by `<SET_LOCALLY>` and home paths marked `$HOME`**. This is a template, not a directly runnable credential file; substitute paths and configure private credentials locally.
- `agent/prompts/`: current command prompts, including `/splane`. `agent/extensions/tgrep/index.ts`: local extension source.
- `agent/npm/package.json` and `agent/npm/package-lock.json`: installed Pi package declarations and npm resolution; the local AgentMemory checkout is a separate path in `settings.json`, not a published package snapshot.
- `skills-inventory.json`: filenames and SHA-256 hashes of every locally installed skill tree at capture time. Third-party skill bodies and the local AgentMemory distribution are deliberately **not** republished here; settings retains the exact enabled-skill list. The installed npm packages are likewise not vendored.

## Excluded deliberately

`auth.json`, `antigravity-accounts.json`, `mcp-auth.json`, raw `mcp.json`, `models-store.json` (provider cache), `trust.json`, sessions, prompts' runtime logs, missions, receipts, backups, cache, private data, installed npm `node_modules`, third-party skill bodies and runtime state. Historical MEGAI source, legacy OMP skills/agents/config, benchmark artifacts and old Pi defaults are absent from this branch and its new root history. None are needed to describe the non-secret setup, and several contain credentials or private project/session data. Do not commit them. The snapshot is **not** a complete transferable credential or offline-install backup.

Refresh on the owner's machine with `python3 pi-current/snapshot.py`, inspect every changed file, and run a secret scan before committing. The script copies a closed allowlist and redacts all MCP headers; it cannot certify arbitrary newly added paths as safe. For a new machine, install packages from the lockfile, obtain the skill trees and AgentMemory separately under their respective licenses, replace user-specific paths in the settings and MCP template, supply credentials locally, then verify in a fresh isolated Pi process. Do not overwrite a running user's config or session.

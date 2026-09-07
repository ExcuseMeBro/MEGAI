# Lean GPT runtime rollout

Scope: user-requested rollback of routine MiniMax routing and removal of unnecessary Pi startup resources. No deletion of shared skill/tool installations, credentials, project data, indexes or session history. Other harness launch paths and user project overrides remain intact.

## Evidence and decisions

The preceding Ruff task needed one worker correction after the parent reproduced PATH shadowing and false-ready version detection despite passing initial tests. This is evidence of rework, not a controlled GPT/M3 comparison. Per-task token attribution and a comparable runtime baseline are unavailable; no universal model ranking or savings claim follows.

- Parent: Astra/high and direct tools for bounded tasks. Necessary workers: Luna medium discovery/high implementation. Sol high only for complex debugging and required independent review. Native fallback scopes are GPT-only; MiniMax defaults/allow entries removed. No providers or credentials changed.
- Native pi-subagents removed from local startup (package files retained). Matt Pocock package narrowed to writing-for-agents. Global auto-discovered skills excluded with `!*`, then ten exact core paths enabled; shared specialist sources remain manually available. Project overrides can still add resources.
- Local optional Pencil, Headroom and codebase-memory MCP entries disabled. The actual adapter configuration resolver confirms these disabled even when inherited from shared/project files. Plane and zvec remain lazy, proxy-only and unchanged. MEGAI's redundant project MCP entries removed from source.
- Normal Pi package installation now includes only the MCP adapter; statusline joins the opt-in full package set. Unrelated user packages remain preserved.
- `megai pi` skips automatic memory and index startup but preserves wiring, branch/worktree safety and project bookkeeping. `MEGAI_PI_FULL=1` restores core preparation; specialist jobs additionally require the existing specialist opt-in. Other harness startup behavior is unchanged. No processes belonging to other sessions were stopped.
- Existing MEGAI Pi skill reduced to native/structural/semantic lookup, explicit memory and safe Ruff checks. Required tests, security/data-integrity review and tracker/approval boundaries remain.

## Measured resource change

Offline resolution used the installed Pi package/skill loaders with installation/network disabled; it loaded no extensions or models.

| Metric | Before | After |
| --- | ---: | ---: |
| Discovered active skills in MEGAI | 63 | 11 |
| Skill-list prompt characters | 19,669 | 3,932 |
| Skill collision diagnostics | 0 | 0 |
| Enabled extension entrypoints | 2 | 1 |

These are resource counts, **not total system-prompt tokens, cost savings, end-to-end latency or quality measurements**. The remaining extension is pi-mcp-adapter. Kept skills: task-flow, worktree lifecycle, MEGAI core, codebase-design, diagnosing-bugs, lean-build, migration, safe-refactor, surgical-patch, verify-and-stop, writing-for-agents.

## Verification and rollback

- Package/default-launch regression tests failed before the source changes, then passed. Runtime fixtures assert lean Pi has no memory/index dispatch, full Pi restores it and non-Pi behavior is preserved.
- Model policy/live checks pass; nine independent M3-routing, scope, review and resource regressions are rejected by the live checker in isolated fixtures.
- Pi runtime, package defaults, task-flow and Ruff integration tests pass, including the real non-mutating Ruff fixture. Python lint and diff checks pass. Self-reviewed directly; no additional agents launched for this rollout.
- Exact preservation checks cover unrelated Pi settings, the tracker instruction section and original MCP settings/server definitions. Installed runtime/policy/skill assets match the candidate source.
- Private local backup: `~/.megai/backups/lean-gpt-c4i_u2g1/`. It includes settings, instructions, MCP config, managed files and before/after resource manifests. Restore only task-owned differences after reconciling later edits, never overwrite newer tracker configuration wholesale.

A new Pi session is necessary to shed old history, stale tracker instructions and removed tool schemas. `/reload` refreshes resources but cannot erase a long conversation. Record available wall time, reported token/cache usage, correction count and acceptance on subsequent real tasks; missing evidence stays unknown. No additional synthetic tasks or automatic model switches are justified.

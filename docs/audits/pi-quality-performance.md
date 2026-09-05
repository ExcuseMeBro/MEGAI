# MEGAI / Pi quality and performance audit — 2026-09-05

Scope: current local Pi discovery, documented CLI bridges, and MEGAI install/project-startup paths. Not a security certification or a benchmark of every model, extension, UI flow, or provider.

## Findings and actions

| Evidence | Action | Quality preservation |
| --- | --- | --- |
| Actual Pi resource loader found 78 skills and 22 name-collision diagnostics. Caveman/Cavecrew overlap concise-output/exploration rules; the legacy smart-development skill prescribes OMP/MiniMax instead of the current Pi routing. | Exclude these global skill families. Quarantine 14 legacy project Caveman directories and six byte-identical project workflow copies; remove two duplicate Pi resource references. | Shared skill files retained, core engineering/design/security/worktree skills still discoverable. No Ponytail replacement or new provider. |
| `command -v megai-memory` and `command -v megai-codedb` failed. Pi supports JS/TS extensions, not the installed shell links. | Put owned shell bridges in `~/.megai/bin`; remove only matching legacy extension symlinks. | Custom CLI replacements survive install/remove. Memory, structural lookup and native tools remain available. |
| Real codedb CLI rejects `symbol` and `index`; its grammar is `codedb [root] <command>`. | Map wrapper `symbol` to `find`, pass tree root before command, and warm/cache via `<root> tree`. | Real definition lookup resolves `hook_command` to `lib/retire_ix.py:30`; failed warmup cannot claim an indexed timestamp. |
| `prepare_stack` unconditionally called both graphify and RepoWise background initialization. | Default startup skips specialist indexing. Explicit commands or `MEGAI_SPECIALIST_INDEXES=1` retain it. | Core codedb/zvec indexing remains; existing graph/index data is not deleted. |
| Every Caveman installer invocation forced wiring again. | Require `MEGAI_CAVEMAN=1`; preserve existing installation otherwise. | Optional installation remains tested. No shared plugin/config deletion. |
| Memory HTTP requests had no deadline. | 3-second connect / 15-second total deadline, with no automatic write retries. | Errors remain visible; a daemon is still required. |

## Verification

- Regression gate `bash tests/pi-runtime.sh` failed against the original wiring and passes after the fix. It exercises actual CLI wiring, argument preservation (including spaces), supported backend grammar, warmup/cache state, default versus opt-in startup dispatch, HTTP deadline flags, optional Caveman wiring, repeated installation, invalid settings preservation, custom Pi directories and user-owned link preservation.
- `bash tests/pi-task-flow.sh`, `bash tests/pi-performance.sh`, and `bash tests/orchestration-policy.sh` passed. Bash syntax and `git diff --check` passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 tests/ix-retirement.py`: nine tests passed on both the baseline and independently reviewed candidate. Ix remains retired.
- Independent Sol/high review found a compatibility regression for Pi's supported legacy `skills` object and an inaccurate resumed-startup status message. Parent reproduced the legacy failure, matched Pi's migration semantics (custom directories and top-level command preference precedence), and added regressions for both findings. Final closure is parent-verified, not a claimed second independent review.
- Live resource loader: **78 → 63 skills**, **27,833 → 19,630 skill-prompt characters**, **22 → 0 collision diagnostics**. Required engineering, design, security, Asana/worktree and delegation skills remain discoverable. This measures skill metadata, not the full system prompt or token count.
- Live codedb definition lookup returned the expected Python file/line in one observed **0.038-second** call. This is a smoke check, not a latency distribution. The installed parser reports shell files as `unknown`; use native `rg` for unsupported languages or missing definitions rather than interpreting exit 0 as a successful lookup.
- Local model/provider, thinking, packages, subagent settings, compaction, retries and project-trust settings were compared before/after and remained unchanged. Native Pi subagents remain enabled for standalone fallback; Paseo delegation policy is unchanged.

## Limits and rollback

No end-to-end task speedup or unchanged model-output quality has been established by these checks. Codedb refreshes on reads; zvec manifest existence is only readiness metadata, not independently verified freshness. After relevant source changes, use explicit `megai reindex` and validate retrieval against current files rather than assuming cached data is current. The fixes remove concrete failed commands, conflicting instructions and unrequested background launches; they do not make an "everything is ideal" claim. The memory daemon was not listening during the audit: bridge dispatch/deadlines are tested, but production memory save/recall needs a separate service check (`megai start agent-memory`). No unrelated processes were killed, no graph/memory/session data was deleted, and no provider credentials were changed.

Local backups live under `~/.megai/backups/pi-audit-*/`: original Pi settings, installed files and quarantined project skills. Restore only the corresponding files/paths after checking for subsequent user edits; do not overwrite an entire newer configuration blindly. Pi wiring also snapshots settings before skill-selection changes. Unwiring preserves user-scope skill selection; use `pi config` to re-enable it. Global filters do not remove independently selected project skills.

Existing sessions need `/reload` or a new session for changed resources. Compaction summarizes history; it does not reload configuration. Repository delivery and any subsequent main promotion follow the normal explicit-approval policy.

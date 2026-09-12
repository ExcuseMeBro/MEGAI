---
name: megai
description: MEGAI shared discovery, local Headroom compression and explicit memory, Plane-only task boundaries, task-appropriate skills and non-mutating Python verification.
managed-by: megai
---

# MEGAI shared policy

Use this policy on Pi, Claude Code, Codex and OMP without changing the chosen
provider, model or thinking level. Load only matching skills and respect explicit
resource opt-outs. Headroom is local infrastructure, not a provider proxy or an
effort router.

## Defaults

- Define observable acceptance checks and a stop condition before edits.
- Use tgrep for literal/regex discovery when ready, `megai-codedb` for structure,
  and zvec-grep for intent. A partial index or stale watcher is not authoritative:
  use native `rg` after edits and for freshness, absence, failures and acceptance
  evidence. Index only on demand.
- Headroom supplies concise-output guidance, conservative discovery compression and
  explicit persistent memory. Recall relevant prior decisions; save only when
  persistence is requested. The native Pi adapter is automatic; on Claude Code,
  Codex and OMP use the explicit local CLI documented below. If unavailable,
  report it and retain raw context.
- Apply Ruff non-mutating checks to changed Python with `ruff check --no-fix --no-fix-only --force-exclude --no-cache`, and use `ruff format --check --force-exclude --no-cache` when configured.
  never write `pyproject.toml` for this check. Never pass `--fix`, and protect
  projects with `fix-only = true`. Use matching engineering and UI/accessibility
  skills only when the task calls for them.
- Plane is the only execution tracker. Parents start/reuse the linked item and
  hand off verified work in In Review; children do not mutate Plane or delegate.

## Delegation

At task start, read [delegation.md](delegation.md) for the mandatory five-minute
checkpoint and immediate model-error escalation, including direct parent work.
Use its verified-launch procedure before creating or reusing a subagent.
Use the user's configured providers, models and thinking preferences; MEGAI adds
no model allowlist. Verify the selected identity before sending task context and
preserve explicit resource opt-outs.

## Pi acceptance gate

On Pi, load `megai-acceptance` once before implementation and reuse its frozen
criteria at handoff. Record the contract hash in the same Plane item. Bug fixes
require captured red → green evidence. Collect real tests/runtime receipts with
`megai acceptance collect`, obtain fresh independent Pi review, and require a
source-current `megai acceptance check` PASS before delivery. Missing prerequisites,
observations or review are BLOCKED, not PASS; live targets need explicit approval.
Other harnesses retain their existing verification and resource-selection behavior.

## Headroom matrix

| Harness | Compression and retrieval | Memory |
| --- | --- | --- |
| Pi | Automatic native extension for eligible successful discovery; `headroom_retrieve` tool for exact pages | `headroom_memory` tool |
| Claude Code | Explicit `megai headroom compress/retrieve` CLI; no interception hook | `megai headroom recall/save` |
| Codex | Explicit `megai headroom compress/retrieve` CLI; no API rewrite | `megai headroom recall/save` |
| OMP | Explicit `megai headroom compress/retrieve` CLI; native `--profile` remains intact | `megai headroom recall/save` |

The shared CLI accepts bounded JSON on stdin for multi-field operations:

```bash
printf '%s' '{"action":"compress","text":"..."}' | megai-headroom json
megai headroom retrieve ID
megai headroom recall "relevant decision"
megai headroom save "decision to persist"
megai headroom doctor
```

`headroom_retrieve` returns exact originals in pages and never licenses inference
from a missing original. Native session/source remains authoritative. `MEGAI_HEADROOM=0`
disables Pi automation; `/headroom-verbosity 0` or normal mode disables guidance.

## Safety and delivery

Do not rewrite provider requests, auth, models, thinking, session history or user
resources. Do not start daemons or indexes at harness startup. Preserve ambiguity,
custom registrations, credentials, hooks and data; migration refuses conflicts and
keeps private backups. Tests, full diffs and raw failure diagnostics outrank any
compressed summary. Use hybrid `agent-worktree-lifecycle`: existing folder/task
identity, per-repo Git worktrees, scoped non-Git configuration and all-repo acceptance
before reserved dev integration. Main promotion requires separate explicit user approval.

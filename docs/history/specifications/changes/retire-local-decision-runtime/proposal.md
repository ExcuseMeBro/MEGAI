## Why

The repo ships a local checkpoint decision tool, its pinned runtime lock and a
compaction companion that replaced Pi's own compaction call. Native Pi judgment and
Pi's native compaction cover both jobs, so the runtime is dead weight: a multi-gigabyte
checkpoint download, a Python 3.11 venv, an installer gate that can block the whole
profile, a shadow-labeling workflow and 43 files of source, docs, tests and fixtures to
keep working. A frozen acceptance contract now requires the retired name and the
previous GPT alias spellings to appear nowhere in the tracked tree, while installs made
before this change must still be retired safely and without deleting operator data.

Plane project/work item: `59005e36-ecd4-46ed-bb42-f779858b20ce` / `585c95c8-d3be-4357-bff7-add7606b4049`.

## What Changes

- Delete every tracked artefact of the retired local decision runtime: its Pi extension,
  stdio bridge, compaction companion, legacy compatibility extension, runtime installer,
  hash lock, shadow CLI, fixtures, dedicated tests, its documentation page and the old
  OpenSpec change that introduced it. Git history keeps all of it; nothing is force-pushed.
- Remove the installer gate: `pi-defaults/install.py` and `lib/pi_model_policy.py` no
  longer verify, download or require a local runtime, and `pi-defaults/verify.mjs` no
  longer requires its tool. The Pi policy transaction stays a single fatal step.
- Retire installed assets on reinstall through one new module, exact-match only: the
  receipt-owned extension files and the saved tool state, the published source copies
  under `$MEGAI_HOME` and `$MEGAI_HOME/pi-profile` (recorded digests), and the owned
  pinned virtualenv, which is moved into the private backups area. An unowned file,
  symlink or unmarked directory fails closed and is never touched.
- Rewrite every active alias from the previous `gpt-5.6-*` spelling to
  `gpt-6-luna` / `gpt-6-sol` across templates, the economy preset, extension sources,
  tests, current documentation and OMP configuration. Preserve historical benchmark
  measurements, protocols, audits and archived policy examples byte-for-byte under
  the integrity-corrected acceptance contract; never attribute an earlier run to a
  model that did not produce it.
- Drop the tracked repository-local `.claude/settings.json` (Claude Code plugin
  enablement for this stack). Agent references to other harnesses stay limited to their
  own user-home configuration roots; historical or generic Claude references remain.
- Keep the OpenSpec workflow: this change carries proposal, design, spec deltas and
  tasks, and replaces the retired-tool-named change without rewriting Git history.
  Archive and main promotion stay separate user decisions.

## Capabilities

### New Capabilities

- `native-decisions`: Native Pi judgment for every workflow decision step, native Pi
  compaction with no substitute compactor, and no shipped or installable local decision
  runtime.
- `owned-asset-retirement`: Reinstall retires only assets the project can prove it wrote
  and preserves everything else.
- `model-alias-refresh`: Active GPT alias spellings match the current model generation.
- `local-install-assets`: The repository tracks no Claude Code plugin enablement.

### Modified Capabilities

None. `openspec/specs/` holds no main capability spec yet, so no existing spec needs
reconciliation; these deltas are the first capability specs for the retirement.

## Impact

Affected paths: `lib/pi_model_policy.py`, `lib/retire_legacy_sources.py`, the new
`lib/retire_local_decisions.py`, `pi-defaults/install.py`, `pi-defaults/verify.mjs`, the
policy documents (`pi-defaults/AGENTS.md`, `pi-defaults/skills/pi-workflow/SKILL.md`,
`pi-skill/ADAPTIVE.md`, `pi-skill/acceptance/SKILL.md`, `pi-skill/delegation.md`,
`skills/agent-worktree-lifecycle/SKILL.md`, `task-flow/skills/megai-task-flow/SKILL.md`,
`docs/pi-context-budget.md`), the deleted runtime files and their tests, the renamed
alias files, and `tests/pi_model_policy.py`, `tests/pi_defaults.py`,
`tests/pi_adaptive_policy.py`, `tests/pi_deepseek_preset.py`, `tests/slim_distribution.py`.

Non-goals: changing provider, model identity, thinking levels or routing policy;
touching the operator's live Pi profile, credentials, session history, decision ledger
or checkpoint cache; deleting the unrelated checkout the operator keeps elsewhere;
archive, push, `main` promotion or any Git-history rewrite. Rollback is reverting the
single commit; a retired runtime stays recoverable in `~/.megai/backups/`.

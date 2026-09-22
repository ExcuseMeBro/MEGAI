## Context

See `proposal.md` for motivation and `specs/local-laya-decisions/spec.md` for the behavior contract. The active Jev extension currently owns the typed tool, sift, tool-call gate/router, failed-tool guidance and shared request/logging code; a companion extension imports that code for compaction. Pi loads extension entrypoints through separate cache-disabled module instances, so preserving that split would create two local model processes. It performs one hosted HTTP request per judgment and its block thresholds were measured on Jev. Laya is the upstream open-source decision package (`pip install laya`, Apache-2.0) whose 421M-parameter English checkpoint takes meaningful time and memory to load, but answers in tens of milliseconds once loaded.

The repository already has ownership-aware installers, private MEGAI virtual environments, fail-open extension tests and session lifecycle hooks. Project policy forbids adding an independent daemon.

## Goals / Non-Goals

**Goals:**
- Preserve the typed decision contract while removing TypeSafe network and credential dependencies.
- Load Laya once per Pi session and share it across all decision-backed features.
- Migrate active names and installed assets cleanly, with reversible source/installation changes.
- Prove protocol behavior offline and observe one real local checkpoint decision before delivery.

**Non-Goals:**
- Rewriting historical Jev benchmark results.
- Claiming old Jev thresholds or accuracy transfer to Laya.
- Supporting non-Apple platforms through a second model backend.
- Integrating into `main`.

## Decisions

### Use one lazy stdio child, not a service or per-call CLI

The TypeScript extension will spawn a Python bridge only on the first decision. The bridge creates `laya.Router(max_loaded=2)` once, consumes newline-delimited JSON requests on stdin and emits one JSON response per line on stdout. The English and multilingual checkpoints load lazily on first use and both remain resident, so alternating languages never reload a model; `typed-decisions` is never selected. Requests are serialized by the extension, and each deadline covers queue wait, pipe wait and inference together. The same extension entrypoint registers compaction from a sibling module, so every decision-backed feature owns exactly one runtime instance. Stderr is bounded and used only for diagnostics. `session_shutdown` permanently rejects queued/new work for that extension instance, closes and terminates the child, and cannot resurrect it.

Alternatives rejected:
- A localhost HTTP daemon violates the no-new-daemon constraint and adds port/lifecycle ownership.
- Spawning a fresh Python process per request reloads the whole checkpoint and makes hooks unusable.
- A JavaScript model port would create a second inference implementation and new numerical-parity risk.

### Make `laya` the public tool with no `jev` alias

Active source directories, installed extension names, environment variables, ledger and policy text move to Laya naming. The installer explicitly retires MEGAI-owned `megai-jev` and `megai-jev-compaction` assets. Existing sessions must reload or restart; stored old tool calls remain transcript data but are not executable through an alias.

A compatibility alias was rejected because it leaves the old product name and makes it unclear whether data is local.

### Pin the Python package and two routed checkpoints

The installer creates `~/.megai/venv/laya`, marks it as MEGAI-owned, and installs upstream `laya==0.3.5` from PyPI with a committed hash lockfile on a pinned interpreter. Before activating extensions it verifies both router targets: English `convaiinnovations/laya` and the bundled `multilingual` subfolder. Laya 0.3.5 passes checkpoint-specific `allow_patterns` to Hugging Face, so this downloads only the two selected checkpoints rather than the full three-checkpoint bundle. `LAYA_DEVICE` may force `cpu`; `LAYA_PYTHON` selects an alternative compatible interpreter. The extension resolves the owned interpreter and the bridge next to its installed `index.ts`.

The bridge accepts an optional per-request `lang` and passes it to `Router.predict`; `LAYA_LANG` is only an operator default when the caller knows all undecorated state uses one language. This explicit hint is important for Uzbek and other Latin-script languages outside Laya's built-in detector. No default is set, so English workflow state still routes to the calibrated English checkpoint. `LAYA_MODEL` is intentionally removed: independently replacing one router member would make the verified two-model contract ambiguous.

The runtime identity follows the integration contract published at `brainfunctioncollapse.com/laya` and upstream `NandhaKishorM/laya`: `pip install laya`, `Router(max_loaded=2)`, English plus multilingual, and `router.predict(state, questions, lang=...)`. The third-party `laya-mlx` port and the specialized typed-decisions checkpoint are not used.

The initial install downloads package wheels and only the selected checkpoint files. Normal decisions make no network call once the Hugging Face cache contains both checkpoints.

### Keep the existing request/result schema

The TypeScript layer retains current limits and validation: one to eight questions, bounded state/instructions/criteria and normalized choice/score/noul criteria, plus an optional bounded BCP-47-style `lang` hint. The Python bridge returns Laya's native typed answer schema and routing metadata, which match the expected choice, expected-score and noul fields. This minimizes policy and caller changes.

### Fail open, and default blocking off

Tool execution returns `ok:false` for a missing runtime, startup failure, protocol failure, timeout or cancellation. Gate/router/repair/sift/compaction hooks keep their current fail-open behavior. Because the existing 0.65/0.70 thresholds came from Jev telemetry and Laya is less well calibrated, the Laya gate reports by default; `LAYA_GATE_BLOCK=1` explicitly enables first-call blocking. Thresholds remain configurable for a later measured Laya calibration.

### Keep input out of logs

The renamed Laya ledger stores record id, local model id, source, answer/probability fields, timing and errors. It does not store state, instructions or file text. The endpoint field becomes a local runtime identity rather than a host.

### Test through a fake stdio bridge, then one real smoke

Focused Node tests install the actual extension and point it at a deterministic fake bridge. They cover schema compatibility, process reuse, language hints, cancellation, timeout, crash/restart boundaries, logging, sift refusal rules, gate default/report and explicit block behavior, routing, repair and compaction. Installer tests assert ownership checks and retirement of Jev assets. Final acceptance runs English and Uzbek-hinted requests through one real bridge, observes English/multilingual routing plus valid `choice`/`score`/`noul` answers, and proves the child/process is reused on this Darwin arm64 machine.

## Risks / Trade-offs

- **Laya is less accurate and less calibrated than Jev on the measured 500-item comparison** → gate blocking is opt-in and workflow decisions remain advisory; record outcomes for future tuning.
- **First use of each language family builds a checkpoint** → the installer selectively caches and verifies English plus multilingual files; the bridge loads each model lazily once, and its two-slot router prevents alternating-language reloads.
- **Two resident models consume substantial unified memory per Pi session** → no typed-decisions model, no duplicate process, lazy loading, a hard two-model cap and deterministic shutdown; no background daemon.
- **A child crash can leave pending requests** → reject all pending calls and clear the process reference without replaying an uncertain request; a later call may start a fresh child only before session shutdown.
- **Platform and interpreter availability** → the installer pins an interpreter with prebuilt `torch` wheels, permits CPU fallback and fails before activation on an unsupported platform instead of silently falling back to a hosted provider.
- **Renaming breaks old prompts and resumed tool calls** → active policy and tests migrate together; old `jev` calls fail visibly rather than secretly using another backend.

## Migration Plan

1. Add and verify the owned, pinned Laya runtime without touching active Pi extensions.
2. After runtime verification succeeds, install one `megai-laya` extension with sibling `bridge.py` and `compaction.ts`, update active policy/skills, and retire only owned `megai-jev*` plus the obsolete owned `megai-laya-compaction` entrypoint in the same transaction.
3. Reload/restart Pi so the old in-memory extension exits and its session-scoped child cannot survive.
4. Run focused offline suites and one real local inference smoke.
5. Commit and push `origin/pi-laya`, reserve and integrate the exact accepted commit to `dev`, verify `origin/dev`, then apply and verify the profile in the local Pi harness. Do not touch `main`.

Rollback: reinstall the previous branch/profile commit. Its transaction restores the previous Jev extension bytes; the Laya virtual environment and Hugging Face cache can remain inert unless the user separately authorizes removal.

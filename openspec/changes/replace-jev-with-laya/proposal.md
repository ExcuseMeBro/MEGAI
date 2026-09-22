## Why

Local Pi currently sends every workflow judgment, file screen, gate check and compaction decision to TypeSafe Jev. The requested replacement keeps those typed decisions local, removes the API-key and hosted-data dependency, and gives the user an open Laya runtime on the dedicated `pi-laya` branch.

Plane project/work item: `59005e36-ecd4-46ed-bb42-f779858b20ce` / `db7c527f-c4c9-459f-ab9f-7bfd3730a2fd`.

## What Changes

- **BREAKING**: replace the public Pi `jev` tool with `laya`; no compatibility alias or TypeSafe API path remains active.
- Add a lazily started, session-scoped local Python bridge that keeps Laya's English and multilingual checkpoints resident in one two-slot router and serves `choice`, `score`, and `noul` requests over private stdio, with an optional explicit language hint.
- Replace Jev-backed `sift`, tool-call routing/gating, failed-tool guidance and fast compaction with Laya-backed equivalents.
- Make blocking gates opt-in until Laya-specific thresholds are measured; local inference failure remains fail-open for advisory paths.
- Install a pinned upstream `laya` runtime (hash-locked PyPI package inside a MEGAI-owned virtual environment) plus the English `convaiinnovations/laya` and bundled `multilingual` checkpoint, retire installed Jev assets, and update active Pi policy, ledgers, diagnostics, tests and docs from Jev to Laya.
- Preserve historical Jev benchmark/result artifacts as history; they are not active runtime inputs.

## Capabilities

### New Capabilities

- `local-laya-decisions`: Local Pi typed decisions, lifecycle-managed Laya inference, privacy boundaries, failure behavior and installation compatibility.

### Modified Capabilities

None; this repository has no existing main capability specs.

## Impact

Affected active code paths include `pi-skill/jev*` (replaced by `pi-skill/laya*`), `lib/pi_model_policy.py`, the installer/runtime bootstrap, active Pi workflow guidance, Laya decision ledgers and focused Pi extension tests. The runtime adds pinned `laya` Python dependencies (interpreter, `torch`/`transformers`) and two selectively downloaded checkpoints, retains at most those two models in one Apple-MPS/CPU process, uses no TypeSafe credential, pushes the accepted commit to `origin/pi-laya`, integrates that exact commit to `dev`, and applies the verified profile to the local Pi harness; `main` remains a non-goal. The runtime follows the integration contract published at `brainfunctioncollapse.com/laya` (`pip install laya`), not the third-party `laya-mlx` port.

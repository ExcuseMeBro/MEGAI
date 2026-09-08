# Reviewed changes integrated into Headroom slim

Plane identity: `59005e36-ecd4-46ed-bb42-f779858b20ce` / `61a1dd42-1835-4b85-884f-bf70eef72f31`.
The user superseded the retained-branch-only instruction and authorized delivery to `slim`.
No `dev`/`main` promotion or local installation is part of this delivery.

## Sources and conflict decisions

- Baseline `ec26b4f`: preserve Headroom, Pi-private skill installation, disabled non-Pi entrypoints/providers, transactional installation and existing user-data protections.
- Merge `f6a6d4f` from `task/tgrep-headroom`: the Headroom-compatible adaptation of the reviewed tgrep default. Keep native `rg` as the authoritative correctness/freshness fallback; no startup indexing or server.
- Apply GPT-only policy `1b5fe0c` as `32b7c21`: preserve the Astra/high parent, Luna medium/high discovery/implementation and Sol/high review/complex fallback map. Select and verify Pi/model/thinking before task context, with no non-GPT/non-Pi fallback.
- Resolve README and policy conflicts by retaining Headroom/tgrep guidance and adding the GPT map. Consolidate duplicated Pi-only/GPT-only skill sections rather than maintaining two dispatch contracts.
- Keep both sets of regression tests. Adapt GPT install/upgrade tests to `~/.pi/agent/skills`, explicitly asserting that shared or other-harness policies are not created. Keep ownership, custom-edit refusal and idempotence checks.
- Import the requested feature changes, not the full older `dev` ancestry: wholesale ancestry integration would mix the legacy multi-harness/Caveman/RTK/agent-memory profile into the dedicated Headroom slim distribution. The original source branches remain available for traceability; their tips need not all become Git ancestors of `slim`.
- GPT routing is installed agent policy, not a runtime model allowlist or provider-catalog rewrite. Existing Pi-only launcher/provider restrictions remain intact.

## Verification

Run in the isolated integration worktree before updating the target:

- `PYTHONDONTWRITEBYTECODE=1 python3 tests/slim_distribution.py`: 38 pass.
- `PYTHONDONTWRITEBYTECODE=1 python3 tests/tgrep_distribution.py`: 44 pass, including the inherited 38 distribution tests; only six additional tgrep-specific cases.
- `PYTHONDONTWRITEBYTECODE=1 python3 tests/headroom_wiring.py`: 11 pass.
- `HEADROOM_TEST_PYTHON="$HOME/.megai/venv/headroom/bin/python" HEADROOM_TEST_ASSETS="$HOME/.megai/headroom-assets" PYTHONDONTWRITEBYTECODE=1 python3 tests/headroom_runtime.py`: 11 pass.
- `bash tests/pi-performance.sh`: 2 pass; `bash tests/orchestration-policy.sh`: pass.
- Both `tests/headroom-extension.mjs` and `tests/headroom-live-extension.mjs` pass using the installed Pi package and isolated Headroom runtime. Actual Pi hooks, compression, exact retrieval and semantic memory are exercised with disposable test data; no provider calls.
- Ruff passes for `lib/slim_wiring.py`, `tests/slim_distribution.py`, and `tests/tgrep_distribution.py`. Changed shell syntax and native diff checks pass.

Independent review verdict and exact pushed target SHA are recorded on the same Plane item after review/delivery. This file does not claim that runtime defaults on the host have already been updated or that a benchmark proves universal model/tool performance gains.

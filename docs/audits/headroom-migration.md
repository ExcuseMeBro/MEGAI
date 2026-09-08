# Headroom migration acceptance — 2026-09-08

Plane: `79f35751-caf9-4ea0-bd7d-0dd3bfa007ae`. Delivery: persistent `slim` only.
Baseline: `dad2f40`; unrelated tgrep work stays with its separate owner.

## Contract and implementation

- Headroom AI 0.37.0, hash-locked wheels, managed Python 3.14; no auth proxy,
  provider/model/thinking rewrite, remote embedding, effort router or automatic memory extraction.
- Pi outgoing-context compression is limited to successful conservative discovery.
  Native session messages, source reads, patches, mutations and acceptance diagnostics stay raw.
- Original retrieval is repository-scoped, persistent across subprocesses, paginated,
  seven-day TTL, transactionally limited to 256 entries / 64 MiB. Capacity exhaustion
  retains raw output rather than evicting a live original.
- Headroom SQLiteMemoryStore commits text and its local ONNX embedding together.
  Content-derived IDs make an acknowledged-or-not save retry idempotent. No separate
  graph/vector index can become partially committed. Worktrees share repository memory.
- Model revision and content hashes are verified. Python and snapshot-loader launchers
  strip provider credentials and interpreter overrides before third-party execution.
- Source/wiring publication is journaled; downstream nonzero exits restore original bytes
  and executable permissions. Unrelated installed dependencies may remain inactive.
  Abrupt process/machine termination needs manual journal recovery.
- Actual Pi resource loading detects activation and honors real force-exclusions. The
  standalone verifier handles nested `dist/bundle/cli.js` layouts and loader-time timers.

## Verification

Run from the retained slim checkout, explicitly selecting installed runtimes:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tests/slim_distribution.py
PYTHONDONTWRITEBYTECODE=1 python3 tests/headroom_wiring.py
HEADROOM_TEST_PYTHON="$HOME/.megai/venv/headroom/bin/python" \
  HEADROOM_TEST_ASSETS="$HOME/.megai/headroom-assets" \
  PYTHONDONTWRITEBYTECODE=1 python3 tests/headroom_runtime.py
PI_PACKAGE_ROOT=<installed-pi-package> node tests/headroom-extension.mjs
HEADROOM_INSTALL_ROOT="$HOME/.megai" PI_PACKAGE_ROOT=<installed-pi-package> \
  node tests/headroom-live-extension.mjs
bash tests/pi-performance.sh
```

Results: distribution **36**, migration/wiring **11**, real runtime **11**, Pi startup
**2** pass. Both actual Pi loader suites pass, including the installed runtime's full
context → compression → exact retrieval and explicit save → semantic recall path.
These tests use disposable data, never provider/model calls. Credential canaries,
corrupt assets, interrupted saves, quota/restart behavior, project isolation, raw patch
fallback, explicit inactivity and three-phase rollback are covered. Changed Python
passes Ruff; shell syntax and native diff checks pass.

Independent Pi / openai-codex/gpt-5.6-sol / high review found eight initial issues;
all were fixed and closed. Follow-up review of actual CLI discovery/timer fixes: PASS.

## Local cutover evidence

- Pinned local runtime prepared and doctor passed before old execution was retired.
- Legacy API exports across all agent scopes returned zero sessions, memories, semantic
  and procedural records. No observation namespaces existed. Shutdown flushed an empty
  BM25 snapshot: entries/inverted/docTerms all empty, totalDocLength zero. No semantic
  records needed importing; audit/health data and all original files were preserved.
- Only the daemon matching MEGAI's PID, exact arguments, start time and owned child
  engine was stopped. Legacy ports 3111/3112/3113 closed. Receipts archived privately.
- Receipt-owned Caveman copies, memory bridge, legacy installer/source files and exact
  retired metadata were archived outside Pi discovery. No historical sessions were edited.
- Auth and settings hashes remained byte-identical; model-file absence was preserved.
  Other tools, provider/model/thinking selections and package selections were not changed.
- Scoped deployment (`install_transaction.py --wiring-only`) completed with exit 0;
  the fresh actual Pi loader reported Headroom active. Installed-runtime end-to-end test passed.

Private recovery/export evidence: `~/.megai/backups/headroom-cutover-gw9f2aa1/`.
Successful publication journal: `~/.megai/backups/headroom-transaction-hfpmk826/journal.jsonl`.
Earlier rejected attempts and manifests remain available; no failure was counted as success.
Do not publish the private backup contents: they include protected configuration.

## Limits

Start a new Pi process **and new session**. Old instructions in an existing conversation
and provider-side KV caches cannot be retroactively purged locally without destroying
history. Unreferenced Homebrew/npm binaries outside Pi's active scope were not uninstalled.
No workload token, billing, latency or model-quality improvement is claimed.

# Spend context where the decision needs it

Use this reference for broad discovery, a Matt skill stage or context pressure.
Reuse the task's existing paths and evidence. This is tool-selection guidance,
not a mandatory extra phase or an automatic dispatcher.

| Stage | Smallest useful input | Completion condition |
| --- | --- | --- |
| Locate code | General text/name → Codedb `search`; definition → `find`; API → `outline`; known range → native read. Repeated literal/regex on a stable indexed tree → tgrep; exact/freshness evidence → `rg`. | Exact current source and relevant callers located; no unexplained search failure. |
| `codebase-design` | Affected interfaces and caller ranges. | Required interfaces/dependencies read; rankings never define the impact boundary. |
| `diagnosing-bugs` | Exact failure/stack plus affected symbol and focused reproduction. | Reproduction and native evidence establish the cause; no score counts as proof. |
| `tdd` | Relevant test seam and changed source only; reuse diagnosis. | Required red/green assertions and raw command exit/results captured. |
| `code-review` | Fixed base, complete diff including WIP, task criteria, exact evidence paths and targeted dependencies. | Every changed file and criterion reviewed; no transcript replay. |
| Delivery/cleanup | Verified commit vector, fresh ownership/ref checks and current receipts. | Queue, permission, ancestry and cleanup checks satisfied; no model substitutes for them. |

## Codedb: general search and structure before content

Run in the owned task checkout, using the installed wrapper:

```sh
CODEDB_NO_TELEMETRY=1 megai-codedb search "payment retry"
CODEDB_NO_TELEMETRY=1 megai-codedb find processPayment
CODEDB_NO_TELEMETRY=1 megai-codedb outline src/payments.ts
```

`find`/`symbol` locate definitions, not a complete call graph. Use scoped native
`rg -n` to find callers and exact references. `search` is case-insensitive full-text
discovery and the first choice for ordinary repository text searches, not an exact/regex
absence check. Tgrep handles repeated compatible literal/regex discovery when
its indexing cost is worthwhile; do not repeat successful discovery through every tool.
`tree` is for an unfamiliar layout;
avoid printing the whole repository just to find one symbol. `index PATH` runs a
tree query to warm the native cache, not a guaranteed forced rebuild. Cache location
depends on the installed CLI; never assume `.codedb` proves freshness or overwrite
a tracked `codedb.snapshot`. If ownership/cache safety is uncertain, use native tools.
No startup indexing, daemon or repository upload. For direct CLI calls keep
`CODEDB_NO_TELEMETRY=1`. After edits or branch changes use native source/`rg` until
the current tree's index coverage is verified. Reuse successful paths, not stale text.

## Tgrep: repeated queries when indexing pays off

Tgrep is installed separately; it is not a startup service or mandatory extra pass.
Prefer it for repeated, selective literal/regex queries on a large stable task-owned
checkout. A ready index is useful only when its coverage/freshness is known. If no
index exists, build on demand only when several queries are expected and the saved
query time justifies construction; use native `rg` for small/one-off searches.

```sh
TASK_SEARCH_INDEX="$(mktemp -d "${TMPDIR:-/tmp}/megai-tgrep.XXXXXX")"
tgrep --index-path "$TASK_SEARCH_INDEX" index .  # owned checkout only, when justified
tgrep --index-path "$TASK_SEARCH_INDEX" -n -F "payment_retry_marker" .
tgrep --index-path "$TASK_SEARCH_INDEX" -n "payment_.*_marker" .
```

Reuse that one task-private index path; do not create it per query. Keeping the
index outside the source checkout avoids dirtying it or blocking workspace cleanup.
Readiness/status is only a hint, never freshness proof. Preserve pre-existing indexes
and tracked caches rather than overwriting them. No `serve`, background watcher or shared primary indexing for
this workflow. After edits, branch/ignore changes or warnings, use native `rg`
until a completed rebuild covers the current tree; if a server was independently
started, it also needs a confirmed restart. Status alone does not prove this.
Unsupported flags/semantics, index errors, failed searches, exhaustive impact and
absence checks use native `rg` with the intended flags. Never interpret an index
failure, excluded file or truncated result as no match. Maintain exact exit/stderr.

`python3 -B tests/pi_search_benchmark.py` checks literal/regex/case-insensitive
results against `rg` on a disposable 400-file tree and records build cost, medians
and estimated break-even query count. Timings include process startup and vary with
hardware/cache/query selectivity; do not claim a universal speedup or token saving.

## Compression, handoff and measurement

Headroom handles eligible successful discovery and can retrieve the exact original.
Raw source, full diffs and failure/test artifacts remain authoritative. Pi handles compaction with its native summarizer. Do not trigger compaction after every step.

A reviewer handoff needs the task criteria, base/candidate, changed paths, unresolved
risks and evidence paths. Read each relevant artifact once, then only changed ranges.
No mandatory scout, second tracker, repeated full skill load or extra approval turn.

Compare the same task, model, acceptance and initial state with `megai report --text`.
Record hosted input/output tokens, turns and local ranking latency when available.
`tests/pi-context-economy-live.mjs` measures synthetic discovery characters and local
latency, including cold/warm Codedb and native `rg`, only. Small repositories may
be faster with native scans; no universal latency claim. Its smaller payload does not prove whole-task token, quality or cost
improvement. Required checks and independent review remain unchanged.

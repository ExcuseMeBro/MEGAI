# Spend context where the decision needs it

Use this reference for broad discovery, a Matt skill stage or context pressure.
Reuse the task's existing paths and evidence. This is tool-selection guidance,
not a mandatory extra phase or an automatic dispatcher.

| Stage | Smallest useful input | Completion condition |
| --- | --- | --- |
| Locate code | Unknown symbol → Codedb `find`; file API → `outline`; known path → native range read. Literal/regex → ready tgrep, otherwise `rg`. | Exact current source and relevant callers located; no unexplained search failure. |
| `codebase-design` | Affected interfaces and caller ranges. If 4–12 plausible files would otherwise be read broadly, `sift` once to order them. | Required interfaces/dependencies read; rankings never define the impact boundary. |
| `diagnosing-bugs` | Exact failure/stack plus affected symbol and focused reproduction. Laya may order competing hypotheses from these facts. | Reproduction and native evidence establish the cause; no score counts as proof. |
| `tdd` | Relevant test seam and changed source only; reuse diagnosis. | Required red/green assertions and raw command exit/results captured. No Laya pass/fail decision. |
| `code-review` | Fixed base, complete diff including WIP, task criteria, exact evidence paths and targeted dependencies. | Every changed file and criterion reviewed; no sift-based exclusion or transcript replay. |
| Delivery/cleanup | Verified commit vector, fresh ownership/ref checks and current receipts. | Queue, permission, ancestry and cleanup checks satisfied; no model substitutes for them. |

## Codedb: structure before content

Run in the owned task checkout, using the installed wrapper:

```sh
CODEDB_NO_TELEMETRY=1 megai-codedb find processPayment
CODEDB_NO_TELEMETRY=1 megai-codedb outline src/payments.ts
```

`find`/`symbol` locate definitions, not a complete call graph. Use scoped native
`rg -n` to find callers and exact references. `search` is case-insensitive full-text
discovery, not an exact/regex absence check. `tree` is for an unfamiliar layout;
avoid printing the whole repository just to find one symbol. `index PATH` runs a
tree query to warm the native cache, not a guaranteed forced rebuild. Cache location
depends on the installed CLI; never assume `.codedb` proves freshness or overwrite
a tracked `codedb.snapshot`. If ownership/cache safety is uncertain, use native tools.
No startup indexing, daemon or repository upload. For direct CLI calls keep
`CODEDB_NO_TELEMETRY=1`. After edits or branch changes use native source/`rg` until
the current tree's index coverage is verified. Reuse successful paths, not stale text.

## Laya: small local decisions, not extra ceremony

Use `sift` only when ranking avoids broad reads of several plausible local files:

```json
{"query":"Which modules implement payment retry behavior?","paths":["src/payments.ts","src/retry.ts","src/calendar.ts","src/cache.ts"]}
```

Paths are relative to the task cwd; the API accepts 1–12. Prefer one 4–12-file batch
for broad exploration. It sends file content to the on-device model and returns
path/score/error, not full source to the main model. It has inference latency, so
skip it when exact matching or a few small ranges already answer the question.
Read the likely paths first, then every dependency/test/changed file required by
the task regardless of rank. Scores are advisory model outputs, not calibrated
confidence. Sensitive, outside-root, unreadable or too-long files are unscored,
not irrelevant; inspect allowed relevant ranges natively instead of looping retries.

For several cheap decisions on compact facts already in context, one `laya` call
can batch questions. Example of the supported typed shape:

```json
{"state":"Failure occurs only after a cache hit; uncached requests pass.","questions":{"first":{"type":"choice","instructions":"Which path should be inspected first?","criteria":{"cache":"cache read and invalidation path","network":"uncached request path"}}}}
```

Do not send full logs/transcripts, invent unseen facts, ask for permission via a
score or use Laya to replace diagnosis, test execution, security review or acceptance.
On error or ambiguous output, continue with available native evidence; no remote
fallback, repeated local retries or model/role changes for this optimization.

## Compression, handoff and measurement

Headroom handles eligible successful discovery and can retrieve the exact original.
Raw source, full diffs and failure/test artifacts remain authoritative. Laya's
existing compaction shortcut only removes supported byte-identical repeated tool
text while preserving the earlier exact copy; unsupported/unique content falls
back to Pi's native summarizer. Do not trigger compaction after every step.

A reviewer handoff needs the task criteria, base/candidate, changed paths, unresolved
risks and evidence paths. Read each relevant artifact once, then only changed ranges.
No mandatory scout, second tracker, repeated full skill load or extra approval turn.

Compare the same task, model, acceptance and initial state with `megai report --text`.
Record hosted input/output tokens, turns and local ranking latency when available.
`tests/pi-context-economy-live.mjs` measures synthetic discovery characters and local
latency only. Its smaller payload does not prove whole-task token, quality or cost
improvement. Required checks and independent review remain unchanged.

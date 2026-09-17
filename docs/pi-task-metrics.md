# Read-only Pi session metrics for one explicit task

`lib/pi_task_metrics.py` aggregates Pi JSONL session usage for a **bounded** task
and prints JSON. It is stdlib-only, reads sessions read-only, and emits no
transcript content and no session paths. It exists to make task-level measurements
reproducible from native logs, not to become an observability framework.

> **Not installed yet.** This helper is repository source; the commands below run it
from the checkout. It is not copied into `~/.megai` by this change.

## Boundaries are required

A session is not assumed to be one task. Exactly one boundary kind is required:

- **Entry IDs** (`--start-entry ID --end-entry ID`): selects the ancestry of the
  end entry from the start entry inclusive, so work on another branch is excluded.
- **Timestamps** (`--start-time ISO --end-time ISO`): selects every entry in the
  inclusive range across branches (chronological work).

Entry boundaries apply to the parent session only; child sessions require
timestamp boundaries because a fork or an independent child session does not
share the parent's entry IDs. Mixing kinds, a half pair, or a boundary that is not
on the parent's ancestry fails clearly.

## Sessions and attribution

- `--parent PATH` is required.
- `--child PATH` (repeatable) adds explicit child sessions; `--children-complete`
  asserts those scopes are complete.
- `--assert-no-children` records a known zero instead of an unknown.

Without child flags the report keeps `child_attribution.mode = "unknown"` and
`totals = null`: **unknown is not zero**, and the note says so. When child scopes
are supplied, parent and child blocks are reported separately in
`child_attribution.observed_totals`. The complete `totals` stay `null` until
`--children-complete` (or `--assert-no-children`) asserts the scope, and even then
only when the observed usage and cost are themselves complete. `observed_totals`
always carries the observed subtotal so a partial scope is never hidden.

Each session block counts reported `input`, `output`, `cacheRead`, `cacheWrite`,
`reported_totalTokens`, `reasoning`, native `total` (the four-part sum),
`cost` fields, models, tool calls, tool errors, tool results, compactions and
branch summaries. `reasoning` is reported separately and never added to `total`;
cost is the provider-reported estimate carried in the session, not billed cost.

## Observed subtotal vs complete total

Reported numbers are observations, not completeness claims:

- `usage_complete` means **recorded native accounting coverage**: every assistant
message recorded usage and the recorded usage/cost objects were complete. It is
not billing proof. `usage_coverage` carries the per-source reported/present counts
(including `usage_objects_incomplete`); `usage` is an observed subtotal otherwise.
- Optional `toolResult`/`compaction`/`branch_summary` usage is tracked separately
in `usage_coverage` and never inferred or required; its absence is a coverage gap,
not a failure and not proof of zero billing.
- `usage.reported_totalTokens` and `usage.reasoning` are `null` when no recorded
usage object carried them, never a purported measured zero.
- `cost` is `null` when no usage entry reported a cost object. Missing or null
individual cost fields mark the cost object incomplete (`cost_objects_incomplete`)
and are not inferred; `cost_complete` requires every recorded usage object to
carry a complete cost object.
- `totals` (task and `child_attribution`) stay `null` until the child scope is
asserted complete **and** the observed usage/cost coverage is complete, so
`totals_known` matches the top-level completeness rule.
- **Nested tool usage:** a counted `toolResult` usage may itself summarize an
explicitly supplied child's LLM work. When explicit children are present and any
counted `toolResult` usage exists across the participating sessions,
`nested_usage_overlap_suspected` is true, a warning note is added, and complete
totals (top-level and child) stay `null`. The per-session blocks and
`observed_totals` are preserved as separately labeled subtotals; the helper never
dedupes by numerical equality or guesses attribution.

## Validation and tree safety

Limits are explicit, so malformed input fails instead of producing a plausible
number:

- Counters must be non-negative whole numbers. Booleans, fractional values,
negatives, `NaN` and `Infinity` are rejected rather than truncated or coerced.
- `cost` fields must be finite and non-negative.
- Session trees are validated up front: duplicate IDs, dangling, non-string and
cyclic `parentId` links fail without walking forever.
- Naive timestamps are interpreted as **UTC**; a half pair, mixed kinds, an
unparseable timestamp or a start after end fails clearly.

## Clone and fork safety

Pi `/fork` and `/clone` copy entries verbatim into a new session file and point
`parentSession` at the source. The helper tracks counted entry IDs across the
parent and children and skips a shared entry only when the lineage is verified
**and** the shared entries are structurally identical (canonical JSON: sorted
keys, normalized separators; reported as `shared_history_entries_skipped`). A
duplicate ID without verified lineage, or a linked duplicate whose structure
differs, fails instead of deduplicating by guess.

## Honest unknowns

`provider_wait_seconds` and `user_corrections` stay `null`: standard session logs
do not record provider stalls or corrections, and timestamps are used only for
boundary selection. No token, quota or speedup claim is derived from these totals.

## Usage

```bash
# Parent task bounded by ancestry.
python3 lib/pi_task_metrics.py --parent SESSION.jsonl \
  --start-entry 451e7d4d --end-entry 88aa11bb

# Parent plus explicit children in a timestamp window.
python3 lib/pi_task_metrics.py --parent PARENT.jsonl \
  --child CHILD.jsonl --children-complete \
  --start-time 2024-12-03T14:00:00Z --end-time 2024-12-03T16:00:00Z
```

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tests/task_metrics.py
```

Covers explicit boundaries, missing/incomplete usage and cost (including null
required fields, absent `totalTokens`/`reasoning`, and declared-but-incomplete
children), unknown and partial children, nested `toolResult`/child overlap,
two sessions, branches and fork duplicate suppression, malformed numeric counters,
cyclic/dangling trees, timezone handling, and cache/cost arithmetic.

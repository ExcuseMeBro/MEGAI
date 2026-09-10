# Proposed benchmark interfaces

Approval gate: these are proposed public seams, not implemented fixtures or test
results. Confirm them before writing acceptance tests. Each task will have its
own independent module; Python standard library only. Tests observe the public
interface, including specified errors and input consumption, not private helpers.
Inputs outside the domains stated below are out of scope.

## 1. Bugfix: overlapping intervals

**Seam:** `intervals.merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]`

Input is a list of integer endpoint pairs (excluding booleans). Return sorted,
non-overlapping closed intervals. Merge overlaps and shared endpoints, including
nested and duplicate intervals. Consecutive but disjoint integer ranges remain
separate. Return a new list without modifying the input. A reversed pair raises
`ValueError`; negative endpoints and zero-width intervals are valid.

Worked examples:

- `[(5, 8), (1, 3), (3, 6)]` returns `[(1, 8)]`.
- `[(1, 10), (2, 3), (12, 12)]` returns `[(1, 10), (12, 12)]`.
- `[(1, 2), (3, 4)]` remains `[(1, 2), (3, 4)]`.
- `[]` returns `[]`; `[(4, 2)]` raises `ValueError`.

The starter will contain a real interval-merging defect while retaining this
interface. Acceptance covers ordering, transitive overlap, nesting, duplication,
negative endpoints, empty input, errors and non-mutation. Participant adds a
regression test for the repaired defect. No required private implementation.

## 2. Feature: lazy batching

**Seam:** `batching.chunked(items: Iterable[T], size: int) -> Iterator[list[T]]`

Return an iterator of fresh lists, in source order, with at most `size` elements
per list. Include the final partial batch; omit an empty terminal batch. Support
single-pass iterators and empty input. Requesting one batch consumes only that
batch's items, with no lookahead. Source exceptions propagate unchanged.

Validate `size` when `chunked` is called, before consuming the source: a non-integer
or boolean raises `TypeError`; zero or a negative integer raises `ValueError`.
Calling with a valid size consumes no source items until iteration begins. Source
values are arbitrary objects, preserved by identity rather than deep-copied.

Worked examples:

- Consuming `chunked(iter([1, 2, 3, 4, 5]), 2)` yields `[[1, 2], [3, 4], [5]]`.
- Consuming `chunked([], 3)` yields no batches.
- With size `2`, requesting the first batch advances a counting source exactly
  twice; mutating that returned list does not mutate another returned batch.

The starter will expose an unimplemented function. Acceptance covers complete and
partial batches, laziness, one-pass consumption, identity, fresh lists, source
exceptions and immediate argument validation. Participant adds focused tests.

## 3. Refactor: check report formatting

**Seam:** `reporting.render_checks(checks: list[tuple[str, str]], style: str = "text") -> str`

Each pair is `(name, status)` with status exactly `pass`, `fail` or `skip`. Preserve
input order and duplicate names, leaving input unchanged. Unknown status or style
raises `ValueError`. Names are strings; for text output they contain no newline.
Empty input is valid. Supported styles are `text` and `json`; output has no final
newline. Preserve all specified outputs while removing duplicated counting and
validation logic from the starter; readability is reviewed separately from tests.

Text format is one `STATUS name` line per check (uppercase status), followed by
`TOTAL n | PASS p | FAIL f | SKIP s`. An empty name retains the space after STATUS.
JSON format has keys `total`, `pass`, `fail`, `skip`, `checks`; checks is a list of
objects with `name` and `status`. Serialize with `ensure_ascii=False`,
`sort_keys=True`, and `separators=(",", ":")` for byte-for-byte determinism.

For `[("lint", "pass"), ("unit", "fail"), ("network", "skip")]`, text is:

```text
PASS lint
FAIL unit
SKIP network
TOTAL 3 | PASS 1 | FAIL 1 | SKIP 1
```

For empty input, text is `TOTAL 0 | PASS 0 | FAIL 0 | SKIP 0`; JSON is:

```json
{"checks":[],"fail":0,"pass":0,"skip":0,"total":0}
```

The starter will already pass characterization tests in both styles. Acceptance
covers exact formatting, escaping, Unicode, counts, order, duplicates, defaults,
errors and non-mutation. Refactoring must retain the public interface and behavior;
no test will enforce helper names, a particular algorithm or shorter code.

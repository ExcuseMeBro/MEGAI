# Public task: review existing implementation

Review the single Python module in the current directory against its contract.
If it already satisfies the contract, leave the file byte-for-byte unchanged.
If you find a real defect, repair it without dependencies. Do not alter tests.

For `intervals.py`: `merge_intervals(intervals: list[tuple[int, int]]) ->
list[tuple[int, int]]` returns a fresh sorted list of non-overlapping closed
integer intervals. Merge overlaps and shared endpoints (including nesting and
duplicates); consecutive disjoint intervals remain separate. Preserve the input;
a reversed endpoint pair raises `ValueError`. Integers have arbitrary precision.

For `batching.py`: `chunked(items: Iterable[T], size: int) -> Iterator[list[T]]`
returns fresh lists of at most `size` items in order, supports single-pass
iterators, no lookahead, and consumes nothing before iteration. Return a final
partial batch, not an empty batch. Preserve item identity and source exceptions.
Validate `size` at call time: reject booleans/non-ints with `TypeError`, and
nonpositive ints with `ValueError`. Integers have arbitrary precision; a huge
positive size with a short input yields a partial batch without overflow.

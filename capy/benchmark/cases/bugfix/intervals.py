"""Merge closed integer intervals without changing the caller's list."""


def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if any(start > end for start, end in intervals):
        raise ValueError("reversed interval")
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged

"""Merge closed integer intervals."""


def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    for start, end in intervals:
        if start > end:
            raise ValueError("reversed interval")
    ordered = sorted(intervals, key=lambda pair: pair[0])
    result = []
    for start, end in ordered:
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(result[-1][1], end))
        else:
            result.append((start, end))
    return result

"""Lazy batching of single-pass iterables."""
from collections.abc import Iterable, Iterator
from typing import TypeVar

T = TypeVar("T")


def chunked(items: Iterable[T], size: int) -> Iterator[list[T]]:
    if isinstance(size, bool) or not isinstance(size, int):
        raise TypeError("size must be an integer")
    if size <= 0:
        raise ValueError("size must be positive")

    def batches() -> Iterator[list[T]]:
        source = iter(items)
        while True:
            batch = []
            for _ in range(size):
                try:
                    batch.append(next(source))
                except StopIteration:
                    break
            if not batch:
                return
            yield batch

    return batches()

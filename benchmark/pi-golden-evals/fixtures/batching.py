"""Lazy batching of single-pass iterables."""

from collections.abc import Iterable, Iterator
from itertools import islice
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
            batch = list(islice(source, size))
            if not batch:
                return
            yield batch

    return batches()

"""Lazy batching of single-pass iterables."""

from collections.abc import Iterable, Iterator
from typing import TypeVar

T = TypeVar("T")


def chunked(items: Iterable[T], size: int) -> Iterator[list[T]]:
    raise NotImplementedError("implement the approved chunked contract")

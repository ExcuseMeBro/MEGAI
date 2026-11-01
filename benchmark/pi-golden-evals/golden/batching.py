"""Independent, held-out public-contract checks. Never copy into a candidate."""
import unittest
from batching import chunked


class LargeIntegerBatchSize(unittest.TestCase):
    def test_huge_size_consumes_short_source(self):
        self.assertEqual(list(chunked(iter([1, 2]), 10**100)), [[1, 2]])

    def test_huge_size_preserves_laziness(self):
        consumed = []

        def source():
            for item in (1, 2):
                consumed.append(item)
                yield item

        batches = chunked(source(), 10**100)
        self.assertEqual(consumed, [])
        self.assertEqual(next(batches), [1, 2])
        self.assertEqual(consumed, [1, 2])

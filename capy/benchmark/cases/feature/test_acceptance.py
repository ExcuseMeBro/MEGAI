import unittest

from batching import chunked


class BatchAcceptance(unittest.TestCase):
    def test_partial_batch(self):
        self.assertEqual(list(chunked(iter([1, 2, 3, 4, 5]), 2)), [[1, 2], [3, 4], [5]])

    def test_exact_batches_have_no_empty_tail(self):
        self.assertEqual(list(chunked([1, 2, 3, 4], 2)), [[1, 2], [3, 4]])

    def test_empty_source(self):
        self.assertEqual(list(chunked([], 3)), [])

    def test_size_one(self):
        self.assertEqual(list(chunked(["a", "b"], 1)), [["a"], ["b"]])

    def test_large_size(self):
        self.assertEqual(list(chunked([1, 2], 10)), [[1, 2]])

    def test_lazy_iterator_without_lookahead(self):
        consumed = []

        def source():
            for value in range(5):
                consumed.append(value)
                yield value

        batches = chunked(source(), 2)
        self.assertIs(iter(batches), batches)
        self.assertEqual(consumed, [])
        self.assertEqual(next(batches), [0, 1])
        self.assertEqual(consumed, [0, 1])
        self.assertEqual(next(batches), [2, 3])
        self.assertEqual(consumed, [0, 1, 2, 3])
        self.assertEqual(next(batches), [4])
        with self.assertRaises(StopIteration):
            next(batches)

    def test_single_pass_source(self):
        source = iter([1, 2, 3])
        self.assertEqual(list(chunked(source, 2)), [[1, 2], [3]])
        self.assertEqual(list(source), [])

    def test_identity_and_fresh_lists(self):
        first, second = object(), object()
        batches = list(chunked([first, second], 1))
        self.assertIs(batches[0][0], first)
        self.assertIs(batches[1][0], second)
        self.assertIsNot(batches[0], batches[1])
        batches[0].clear()
        self.assertEqual(batches[1], [second])

    def test_nonpositive_size_rejected_at_call(self):
        for size in [0, -1, -100]:
            source = iter([1, 2])
            with self.subTest(size=size), self.assertRaises(ValueError):
                chunked(source, size)
            self.assertEqual(list(source), [1, 2])

    def test_wrong_size_type_rejected_at_call(self):
        for size in [True, False, 2.0, "2", None]:
            source = iter([1, 2])
            with self.subTest(size=size), self.assertRaises(TypeError):
                chunked(source, size)
            self.assertEqual(list(source), [1, 2])

    def test_source_exception_propagates_unchanged(self):
        error = RuntimeError("source failed")

        def source():
            yield 1
            yield 2
            raise error

        batches = chunked(source(), 2)
        self.assertEqual(next(batches), [1, 2])
        with self.assertRaises(RuntimeError) as raised:
            next(batches)
        self.assertIs(raised.exception, error)

    def test_exception_in_partial_batch_propagates(self):
        error = LookupError("partial source failed")

        def source():
            yield 1
            raise error

        batches = chunked(source(), 3)
        with self.assertRaises(LookupError) as raised:
            next(batches)
        self.assertIs(raised.exception, error)


if __name__ == "__main__":
    unittest.main()

import unittest

from intervals import merge_intervals


class IntervalAcceptance(unittest.TestCase):
    def test_transitive_unsorted_overlap(self):
        self.assertEqual(merge_intervals([(5, 8), (1, 3), (3, 6)]), [(1, 8)])

    def test_nested_interval_does_not_shrink_outer(self):
        self.assertEqual(
            merge_intervals([(1, 10), (2, 3), (12, 12)]), [(1, 10), (12, 12)]
        )

    def test_nesting_keeps_later_overlap_connected(self):
        self.assertEqual(merge_intervals([(1, 10), (2, 3), (8, 12)]), [(1, 12)])

    def test_disjoint_consecutive_ranges_remain_separate(self):
        self.assertEqual(merge_intervals([(3, 4), (1, 2)]), [(1, 2), (3, 4)])

    def test_shared_endpoint_merges(self):
        self.assertEqual(merge_intervals([(1, 2), (2, 4)]), [(1, 4)])

    def test_duplicate_and_zero_width(self):
        self.assertEqual(merge_intervals([(2, 2), (2, 2), (5, 5)]), [(2, 2), (5, 5)])

    def test_negative_endpoints(self):
        self.assertEqual(
            merge_intervals([(-2, 0), (-5, -2), (3, 3)]), [(-5, 0), (3, 3)]
        )

    def test_empty_returns_fresh_list(self):
        source = []
        result = merge_intervals(source)
        self.assertEqual(result, [])
        self.assertIsNot(result, source)

    def test_nonmutation(self):
        source = [(8, 9), (1, 4), (2, 3)]
        result = merge_intervals(source)
        self.assertEqual(source, [(8, 9), (1, 4), (2, 3)])
        self.assertIsNot(result, source)

    def test_reversed_interval_is_rejected(self):
        for source in [[(4, 2)], [(0, 1), (9, 3)]]:
            with self.subTest(source=source), self.assertRaises(ValueError):
                merge_intervals(source)


if __name__ == "__main__":
    unittest.main()

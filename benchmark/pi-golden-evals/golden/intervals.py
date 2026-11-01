"""Independent, held-out public-contract checks. Never copy into a candidate."""
import unittest
from intervals import merge_intervals


class LargeIntegerIntervals(unittest.TestCase):
    def test_far_above_float_range(self):
        n = 10**400
        self.assertEqual(merge_intervals([(n + 2, n + 3), (n, n + 2)]), [(n, n + 3)])

    def test_close_values_not_rounded_to_same_float(self):
        n = 10**100
        self.assertEqual(merge_intervals([(n + 1, n + 1), (n, n)]), [(n, n), (n + 1, n + 1)])

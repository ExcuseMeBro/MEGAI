import unittest

from cache import TTLCache


class FakeClock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        return self.now


class TTLCacheTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.cache = TTLCache(2, clock=self.clock)

    def test_capacity_validation(self):
        for capacity in (True, False, 0, -1, 1.0, "2", None):
            with self.subTest(capacity=capacity):
                with self.assertRaises(ValueError):
                    TTLCache(capacity)
        self.assertEqual(len(TTLCache(1)), 0)

    def test_expiry_boundary(self):
        self.cache.put("a", 1, 10)
        self.clock.now = 9.999
        self.assertEqual(self.cache.get("a"), 1)
        self.clock.now = 10
        self.assertEqual(self.cache.get("a", "missing"), "missing")
        self.assertEqual(len(self.cache), 0)

    def test_get_promotes_and_evicts_lru(self):
        self.cache.put("a", 1, 10)
        self.cache.put("b", 2, 10)
        self.assertEqual(self.cache.get("a"), 1)
        self.cache.put("c", 3, 10)
        self.assertIsNone(self.cache.get("b"))
        self.assertEqual(self.cache.get("a"), 1)
        self.assertEqual(self.cache.get("c"), 3)

    def test_miss_does_not_change_order(self):
        self.cache.put("a", 1, 10)
        self.cache.put("b", 2, 10)
        sentinel = object()
        self.assertIs(self.cache.get("missing", sentinel), sentinel)
        self.cache.put("c", 3, 10)
        self.assertIsNone(self.cache.get("a"))
        self.assertEqual(self.cache.get("b"), 2)

    def test_replacement_promotes_and_resets_expiry(self):
        self.cache.put("a", 1, 2)
        self.cache.put("b", 2, 20)
        self.clock.now = 1
        self.cache.put("a", 3, 10)
        self.cache.put("c", 4, 20)
        self.assertIsNone(self.cache.get("b"))
        self.clock.now = 2
        self.assertEqual(self.cache.get("a"), 3)
        self.clock.now = 11
        self.assertIsNone(self.cache.get("a"))

    def test_purge_expired_before_eviction_even_if_mru(self):
        self.cache.put("a", 1, 20)
        self.cache.put("b", 2, 1)
        self.clock.now = 1
        self.cache.put("c", 3, 20)
        self.assertEqual(self.cache.get("a"), 1)
        self.assertEqual(self.cache.get("c"), 3)
        self.assertEqual(len(self.cache), 2)

    def test_len_purges_all_expired_entries(self):
        self.cache.put("a", 1, 2)
        self.cache.put("b", 2, 1)
        self.clock.now = 1
        self.assertEqual(len(self.cache), 1)
        self.clock.now = 2
        self.assertEqual(len(self.cache), 0)

    def test_nonpositive_ttl_removes_and_stores_nothing(self):
        for ttl in (0, -1):
            with self.subTest(ttl=ttl):
                self.cache.put("a", 1, 10)
                self.cache.put("a", 2, ttl)
                self.assertIsNone(self.cache.get("a"))
                self.cache.put("missing", 3, ttl)
                self.assertEqual(len(self.cache), 0)

    def test_delete_reports_only_live_removals(self):
        self.assertFalse(self.cache.delete("missing"))
        self.cache.put("a", None, 10)
        self.assertTrue(self.cache.delete("a"))
        self.assertFalse(self.cache.delete("a"))
        self.cache.put("b", 2, 1)
        self.clock.now = 1
        self.assertFalse(self.cache.delete("b"))
        self.assertEqual(len(self.cache), 0)

    def test_none_value_and_arbitrary_hashable_keys(self):
        keys = [None, (1, "tuple"), frozenset({1, 2}), object(), 42]
        cache = TTLCache(len(keys), clock=self.clock)
        for key in keys:
            cache.put(key, None, 10)
        for key in keys:
            self.assertIsNone(cache.get(key, "missing"))
        self.assertEqual(len(cache), len(keys))

    def test_expired_key_can_be_reinserted(self):
        self.cache.put("a", 1, 1)
        self.clock.now = 1
        self.cache.put("a", 2, 3)
        self.assertEqual(self.cache.get("a"), 2)
        self.assertEqual(len(self.cache), 1)

    def test_capacity_one(self):
        cache = TTLCache(1, clock=self.clock)
        cache.put("a", 1, 10)
        cache.put("a", 2, 10)
        self.assertEqual(cache.get("a"), 2)
        cache.put("b", 3, 10)
        self.assertIsNone(cache.get("a"))
        self.assertEqual(cache.get("b"), 3)


if __name__ == "__main__":
    unittest.main()

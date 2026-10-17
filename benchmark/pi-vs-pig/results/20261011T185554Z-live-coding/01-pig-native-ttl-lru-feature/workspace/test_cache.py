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

    def test_expiration_boundary_and_default(self):
        self.cache.put("a", 1, 10)
        self.clock.now = 9
        self.assertEqual(self.cache.get("a"), 1)
        self.clock.now = 10
        sentinel = object()
        self.assertIs(self.cache.get("a", sentinel), sentinel)
        self.assertIsNone(self.cache.get("missing"))
        self.assertEqual(len(self.cache), 0)

    def test_get_promotes_and_miss_does_not(self):
        self.cache.put("a", 1, 10)
        self.cache.put("b", 2, 10)
        self.cache.get("a")
        self.cache.get("missing")
        self.cache.put("c", 3, 10)
        self.assertIsNone(self.cache.get("b"))
        self.assertEqual(self.cache.get("a"), 1)
        self.assertEqual(self.cache.get("c"), 3)

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

    def test_expired_mru_is_purged_before_eviction(self):
        self.cache.put("live", 1, 20)
        self.cache.put("expired", 2, 1)
        self.clock.now = 1
        self.cache.put("new", 3, 20)
        self.assertEqual(self.cache.get("live"), 1)
        self.assertIsNone(self.cache.get("expired"))
        self.assertEqual(len(self.cache), 2)

    def test_len_purges_all_expired_entries(self):
        self.cache.put("a", 1, 1)
        self.cache.put("b", 2, 2)
        self.clock.now = 1
        self.assertEqual(len(self.cache), 1)
        self.clock.now = 3
        self.assertEqual(len(self.cache), 0)

    def test_nonpositive_ttl_removes_and_stores_nothing(self):
        for ttl in (0, -1):
            with self.subTest(ttl=ttl):
                self.cache.put("a", 1, 10)
                self.cache.put("a", 2, ttl)
                self.cache.put("missing", 3, ttl)
                self.assertIsNone(self.cache.get("a"))
                self.assertEqual(len(self.cache), 0)

    def test_delete_only_reports_live_entries(self):
        self.cache.put("live", None, 10)
        self.assertTrue(self.cache.delete("live"))
        self.assertFalse(self.cache.delete("live"))
        self.cache.put("expired", 1, 1)
        self.clock.now = 1
        self.assertFalse(self.cache.delete("expired"))
        self.assertEqual(len(self.cache), 0)

    def test_none_value_and_arbitrary_hashable_keys(self):
        keys = [None, (1, "a"), object(), frozenset({1, 2}), 42]
        cache = TTLCache(len(keys), clock=self.clock)
        sentinel = object()
        for key in keys:
            cache.put(key, None, 1)
        for key in keys:
            self.assertIsNone(cache.get(key, sentinel))
        self.assertEqual(len(cache), len(keys))
        self.clock.now = 1
        cache.put("new", 1, 10)
        self.assertEqual(len(cache), 1)

    def test_expired_key_can_be_reinserted(self):
        self.cache.put("a", 1, 1)
        self.clock.now = 1
        self.cache.put("a", 2, 10)
        self.assertEqual(self.cache.get("a"), 2)
        self.assertEqual(len(self.cache), 1)


if __name__ == "__main__":
    unittest.main()

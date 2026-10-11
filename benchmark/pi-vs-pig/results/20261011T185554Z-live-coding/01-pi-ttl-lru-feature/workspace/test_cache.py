import unittest

from cache import TTLCache


class Clock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        return self.now


class TTLCacheTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.cache = TTLCache(2, clock=self.clock)

    def test_capacity_validation(self):
        for capacity in (True, False, 0, -1, 1.0, 2.5, "2", None):
            with self.subTest(capacity=capacity):
                with self.assertRaises(ValueError):
                    TTLCache(capacity)
        self.assertEqual(len(TTLCache(1)), 0)

    def test_expiration_boundary(self):
        self.cache.put("a", 1, 10)
        self.clock.now = 9.999
        self.assertEqual(self.cache.get("a"), 1)
        self.clock.now = 10
        self.assertEqual(self.cache.get("a", "expired"), "expired")
        self.assertEqual(len(self.cache), 0)

    def test_get_promotes_and_miss_does_not(self):
        self.cache.put("a", 1, 10)
        self.cache.put("b", 2, 10)
        self.assertEqual(self.cache.get("a"), 1)
        self.assertEqual(self.cache.get("missing", "default"), "default")
        self.cache.put("c", 3, 10)
        self.assertIsNone(self.cache.get("b"))
        self.assertEqual(self.cache.get("a"), 1)
        self.assertEqual(self.cache.get("c"), 3)

    def test_put_replaces_promotes_and_resets_expiry(self):
        self.cache.put("a", 1, 5)
        self.cache.put("b", 2, 20)
        self.clock.now = 4
        self.cache.put("a", 3, 10)
        self.cache.put("c", 4, 20)
        self.assertIsNone(self.cache.get("b"))
        self.clock.now = 5
        self.assertEqual(self.cache.get("a"), 3)
        self.clock.now = 14
        self.assertIsNone(self.cache.get("a"))

    def test_purge_before_eviction_even_when_expired_is_mru(self):
        self.cache.put("live", 1, 20)
        self.cache.put("expired", 2, 5)
        self.clock.now = 5
        self.cache.put("new", 3, 20)
        self.assertEqual(self.cache.get("live"), 1)
        self.assertEqual(self.cache.get("new"), 3)
        self.assertEqual(len(self.cache), 2)

    def test_len_purges_all_expired_without_promoting_live_keys(self):
        cache = TTLCache(4, clock=self.clock)
        cache.put("a", 1, 20)
        cache.put("b", 2, 5)
        cache.put("c", 3, 20)
        cache.put("d", 4, 5)
        self.clock.now = 5
        self.assertEqual(len(cache), 2)
        cache.put("e", 5, 20)
        cache.put("f", 6, 20)
        cache.put("g", 7, 20)
        self.assertIsNone(cache.get("a"))
        self.assertEqual(cache.get("c"), 3)

    def test_nonpositive_ttl_removes_and_stores_nothing(self):
        for ttl in (0, -1, -0.5):
            with self.subTest(ttl=ttl):
                self.cache.put("a", 1, 10)
                self.cache.put("a", 2, ttl)
                self.cache.put("missing", 3, ttl)
                self.assertEqual(len(self.cache), 0)
                self.assertEqual(self.cache.get("a", "missing"), "missing")

    def test_delete_live_expired_and_missing(self):
        self.cache.put("live", None, 10)
        self.cache.put("expired", 2, 5)
        self.clock.now = 5
        self.assertTrue(self.cache.delete("live"))
        self.assertFalse(self.cache.delete("live"))
        self.assertFalse(self.cache.delete("expired"))
        self.assertFalse(self.cache.delete("missing"))
        self.assertEqual(len(self.cache), 0)

    def test_none_values_and_arbitrary_hashable_keys(self):
        keys = (None, (1, "a"), frozenset({1, 2}), object(), 42)
        for key in keys:
            with self.subTest(key=key):
                self.cache.put(key, None, 10)
                self.assertIsNone(self.cache.get(key, "missing"))
                self.assertTrue(self.cache.delete(key))
                self.assertEqual(self.cache.get(key, "missing"), "missing")

    def test_expired_key_can_be_reinserted(self):
        self.cache.put("a", 1, 1)
        self.cache.put("b", 2, 20)
        self.clock.now = 1
        self.cache.put("a", 3, 10)
        self.assertEqual(len(self.cache), 2)
        self.assertEqual(self.cache.get("a"), 3)
        self.assertEqual(self.cache.get("b"), 2)


if __name__ == "__main__":
    unittest.main()

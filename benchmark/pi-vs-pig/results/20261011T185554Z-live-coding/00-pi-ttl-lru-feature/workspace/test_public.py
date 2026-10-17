import unittest
from cache import TTLCache
class PublicTests(unittest.TestCase):
    def test_put_get(self):
        c=TTLCache(2, clock=lambda: 0)
        c.put('a', 1, 10)
        self.assertEqual(c.get('a'), 1)
    def test_missing(self):
        c=TTLCache(2, clock=lambda: 0)
        self.assertEqual(c.get('x', 'missing'), 'missing')

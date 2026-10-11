import unittest
from cache import TTLCache
class Acceptance(unittest.TestCase):
    def setUp(self):
        self.now=0
        self.c=TTLCache(2, clock=lambda: self.now)
    def test_capacity(self):
        for v in [0,-1,True,False,1.5,'2',None]:
            with self.assertRaises(ValueError): TTLCache(v)
    def test_store(self): self.c.put('a',1,10); self.assertEqual(self.c.get('a'),1)
    def test_missing(self): self.assertEqual(self.c.get('a','x'),'x')
    def test_none_value(self): self.c.put('a',None,10); self.assertIsNone(self.c.get('a','x'))
    def test_boundary(self): self.c.put('a',1,10); self.now=10; self.assertEqual(self.c.get('a','x'),'x')
    def test_before_boundary(self): self.c.put('a',1,10); self.now=9.9; self.assertEqual(self.c.get('a'),1)
    def test_get_no_ttl_refresh(self): self.c.put('a',1,10); self.now=9; self.c.get('a'); self.now=10; self.assertEqual(len(self.c),0)
    def test_zero_ttl(self): self.c.put('a',1,0); self.assertEqual(len(self.c),0)
    def test_negative_removes(self): self.c.put('a',1,10); self.c.put('a',2,-1); self.assertEqual(len(self.c),0)
    def test_update_expiry(self): self.c.put('a',1,10); self.now=5; self.c.put('a',2,10); self.now=11; self.assertEqual(self.c.get('a'),2)
    def test_lru(self):
        self.c.put('a',1,100); self.c.put('b',2,100); self.c.get('a'); self.c.put('c',3,100)
        self.assertEqual(self.c.get('b','x'),'x'); self.assertEqual(self.c.get('a'),1); self.assertEqual(self.c.get('c'),3)
    def test_update_promotes(self):
        self.c.put('a',1,100); self.c.put('b',2,100); self.c.put('a',3,100); self.c.put('c',4,100)
        self.assertEqual(self.c.get('b','x'),'x')
    def test_miss_does_not_promote(self):
        self.c.put('a',1,100); self.c.put('b',2,100); self.c.get('x'); self.c.put('c',3,100)
        self.assertEqual(self.c.get('a','x'),'x')
    def test_expired_before_eviction(self):
        self.c.put('a',1,100); self.c.put('b',2,1); self.now=2; self.c.put('c',3,100)
        self.assertEqual(self.c.get('a'),1); self.assertEqual(len(self.c),2)
    def test_len_purges(self): self.c.put('a',1,1); self.now=1; self.assertEqual(len(self.c),0)
    def test_delete_live(self): self.c.put('a',1,10); self.assertTrue(self.c.delete('a')); self.assertFalse(self.c.delete('a'))
    def test_delete_expired(self): self.c.put('a',1,1); self.now=1; self.assertFalse(self.c.delete('a'))
    def test_tuple_key(self): self.c.put(('a',1),2,10); self.assertEqual(self.c.get(('a',1)),2)
    def test_capacity_one(self):
        c=TTLCache(1,clock=lambda: 0); c.put('a',1,10); c.put('b',2,10)
        self.assertEqual(c.get('a','x'),'x'); self.assertEqual(c.get('b'),2)

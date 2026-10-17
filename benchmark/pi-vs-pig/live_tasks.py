"""Small coding fixtures + independent acceptance suites (standard-library only)."""

TASKS = {
    'query-bugfix': {
        'prompt': '''Fix query.py's parse_query(query) implementation. Contract: accept a raw query string with an optional leading '?'; split fields on '&'; skip empty fields; split each field only at the first '='; no '=' means a blank value; preserve blank values and empty keys; decode UTF-8 percent escapes and '+' as space; collect repeated keys in encounter order as lists; malformed percent escapes follow urllib.parse.unquote_plus behavior. Keep the public API and do not mutate inputs. Use only Python's standard library. Add useful tests and run them. Do not change public tests. Stop after implementation and verification; give a brief summary.''',
        'files': {
            'query.py': '''def parse_query(query):
    result = {}
    for field in query.lstrip('?').split('&'):
        if not field:
            continue
        parts = field.split('=')
        if len(parts) != 2:
            continue
        result[parts[0]] = [parts[1]]
    return result
''',
            'test_public.py': '''import unittest
from query import parse_query
class PublicTests(unittest.TestCase):
    def test_duplicates(self):
        self.assertEqual(parse_query('a=1&a=2'), {'a': ['1', '2']})
    def test_decoding(self):
        self.assertEqual(parse_query('q=hello+world'), {'q': ['hello world']})
''',
        },
        'acceptance': '''import unittest
from query import parse_query
from urllib.parse import unquote_plus
class Acceptance(unittest.TestCase):
    def test_empty(self): self.assertEqual(parse_query(''), {})
    def test_question(self): self.assertEqual(parse_query('?a=1'), {'a':['1']})
    def test_only_one_question_removed(self): self.assertEqual(parse_query('??a=1'), {'?a':['1']})
    def test_repeated(self): self.assertEqual(parse_query('a=1&b=2&a=3'), {'a':['1','3'], 'b':['2']})
    def test_flag(self): self.assertEqual(parse_query('flag'), {'flag':['']})
    def test_blank(self): self.assertEqual(parse_query('a=&a&b='), {'a':['',''], 'b':['']})
    def test_empty_key(self): self.assertEqual(parse_query('=x&=y'), {'':['x','y']})
    def test_equals(self): self.assertEqual(parse_query('a=b=c'), {'a':['b=c']})
    def test_separators(self): self.assertEqual(parse_query('&&a=1&&'), {'a':['1']})
    def test_encoded_key(self): self.assertEqual(parse_query('a%20b=x&a+b=y'), {'a b':['x','y']})
    def test_encoded_separators(self): self.assertEqual(parse_query('q=a%26b%3Dc'), {'q':['a&b=c']})
    def test_unicode(self): self.assertEqual(parse_query('q=%E4%BD%A0%E5%A5%BD'), {'q':['你好']})
    def test_plus_literal(self): self.assertEqual(parse_query('x=%2B+%252B'), {'x':['+ %2B']})
    def test_bad_percent(self):
        for s in ['%', '%2', '%GG', '%FF', '%E4%A0']:
            self.assertEqual(parse_query('q='+s), {'q':[unquote_plus(s)]})
    def test_semicolon_literal(self): self.assertEqual(parse_query('a=1;b=2'), {'a':['1;b=2']})
    def test_encoded_duplicate(self): self.assertEqual(parse_query('a=1&%61=2'), {'a':['1','2']})
''',
    },
    'ttl-lru-feature': {
        'prompt': '''Implement TTLCache in cache.py using Python's standard library. API: TTLCache(capacity, clock=time.monotonic), put(key, value, ttl), get(key, default=None), delete(key)->bool, len(cache). Require positive integer capacity (reject bool/noninteger with ValueError). ttl <= 0 removes any existing key and stores nothing. At clock() >= expiry, entries are expired. get of a live key promotes it to most recently used; misses return default without changing order. put replaces/promotes a live key and resets its expiry. Purge expired entries before capacity eviction and before len(); when full evict the least recently used live key. delete returns true only for a currently live removed key. Values can be None. Support arbitrary hashable keys. No threads or external dependencies. Add tests, run them, and do not modify test_public.py. Stop after verification and summarize briefly.''',
        'files': {
            'cache.py': '''import time

class TTLCache:
    def __init__(self, capacity, clock=time.monotonic):
        raise NotImplementedError
    def put(self, key, value, ttl):
        raise NotImplementedError
    def get(self, key, default=None):
        raise NotImplementedError
    def delete(self, key):
        raise NotImplementedError
    def __len__(self):
        raise NotImplementedError
''',
            'test_public.py': '''import unittest
from cache import TTLCache
class PublicTests(unittest.TestCase):
    def test_put_get(self):
        c=TTLCache(2, clock=lambda: 0)
        c.put('a', 1, 10)
        self.assertEqual(c.get('a'), 1)
    def test_missing(self):
        c=TTLCache(2, clock=lambda: 0)
        self.assertEqual(c.get('x', 'missing'), 'missing')
''',
        },
        'acceptance': '''import unittest
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
''',
    },
    'order-refactor': {
        'prompt': '''Refactor orders.py to remove duplication and improve readability while preserving the summarize(rows) API and its existing behavior. Input is any iterable of mapping rows. Canceled rows (status exactly 'cancelled') are skipped; missing status is processed. For each other row: stringified customer (default 'unknown'), int(qty default 1), Decimal(str(price default '0')), Decimal(str(discount default '0')); amount = price*qty*(1-discount). Return {'customers': {name: {'qty': int, 'total': Decimal}}, 'grand_total': Decimal}. Preserve first-seen customer order and exact Decimal arithmetic, including negative qty, discounts outside [0,1], empty input and generator input. Do not mutate input rows. Keep existing exceptions for malformed numeric fields. Use standard library only. Add regression tests and run them. Do not modify test_public.py. Stop after verification; summarize briefly.''',
        'files': {
            'orders.py': '''from decimal import Decimal

def summarize(rows):
    data = {}
    grand = Decimal('0')
    for row in rows:
        if row.get('status', '') != 'cancelled':
            if str(row.get('customer', 'unknown')) in data:
                q = int(row.get('qty', 1))
                p = Decimal(str(row.get('price', '0')))
                d = Decimal(str(row.get('discount', '0')))
                total = p*q*(Decimal('1')-d)
                data[str(row.get('customer', 'unknown'))]['qty'] = data[str(row.get('customer', 'unknown'))]['qty'] + q
                data[str(row.get('customer', 'unknown'))]['total'] = data[str(row.get('customer', 'unknown'))]['total'] + total
                grand = grand + total
            else:
                q = int(row.get('qty', 1))
                p = Decimal(str(row.get('price', '0')))
                d = Decimal(str(row.get('discount', '0')))
                total = p*q*(Decimal('1')-d)
                data[str(row.get('customer', 'unknown'))] = {'qty': q, 'total': total}
                grand = grand + total
    return {'customers': data, 'grand_total': grand}
''',
            'test_public.py': '''import unittest
from decimal import Decimal
from orders import summarize
class PublicTests(unittest.TestCase):
    def test_total(self):
        self.assertEqual(summarize([{'customer':'a','qty':2,'price':'1.25'}])['grand_total'], Decimal('2.50'))
    def test_cancelled(self):
        self.assertEqual(summarize([{'status':'cancelled'}])['customers'], {})
''',
        },
        'acceptance': '''import unittest, copy, random
from decimal import Decimal
from orders import summarize

def reference(rows):
    out={}; grand=Decimal('0')
    for row in rows:
        if row.get('status','')=='cancelled': continue
        key=str(row.get('customer','unknown')); qty=int(row.get('qty',1))
        amount=Decimal(str(row.get('price','0')))*qty*(Decimal('1')-Decimal(str(row.get('discount','0'))))
        if key not in out: out[key]={'qty':0,'total':Decimal('0')}
        out[key]['qty']+=qty; out[key]['total']+=amount; grand+=amount
    return {'customers':out,'grand_total':grand}
class Acceptance(unittest.TestCase):
    def test_empty(self): self.assertEqual(summarize([]),reference([]))
    def test_defaults(self): self.assertEqual(summarize([{}]),reference([{}]))
    def test_grouping(self):
        rows=[{'customer':'b','price':'1.2'}, {'customer':'a','qty':3,'price':'0.10'}, {'customer':'b','qty':-1,'price':'1.2'}]
        self.assertEqual(summarize(rows),reference(rows)); self.assertEqual(list(summarize(rows)['customers']),['b','a'])
    def test_generator(self):
        rows=[{'price':'2.55','discount':'0.2'}]*3
        self.assertEqual(summarize((x for x in rows)),reference(rows))
    def test_no_mutation(self):
        rows=[{'customer':None,'qty':'2','price':'3.14'}]; before=copy.deepcopy(rows)
        summarize(rows); self.assertEqual(rows,before)
    def test_cancelled_invalid(self): self.assertEqual(summarize([{'status':'cancelled','qty':'bad'}]),reference([]))
    def test_case_sensitive_status(self): self.assertEqual(summarize([{'status':'CANCELLED','price':'1'}]),reference([{'status':'CANCELLED','price':'1'}]))
    def test_discount_bounds(self):
        rows=[{'price':'1','discount':'-0.5'},{'price':'2','discount':'1.5'}]
        self.assertEqual(summarize(rows),reference(rows))
    def test_decimal_type(self): self.assertIsInstance(summarize([{}])['grand_total'],Decimal)
    def test_qty_error(self):
        with self.assertRaises(ValueError): summarize([{'qty':'bad'}])
    def test_price_error(self):
        from decimal import InvalidOperation
        with self.assertRaises(InvalidOperation): summarize([{'price':'bad'}])
    def test_generated(self):
        rng=random.Random(71)
        for _ in range(50):
            rows=[{'customer':rng.choice(['a','b',None,1]),'qty':rng.randint(-5,5),'price':str(rng.randint(0,500)/100),'discount':rng.choice(['0','0.1','-0.2','1.2']),'status':rng.choice(['ok','cancelled'])} for _ in range(30)]
            self.assertEqual(summarize(rows),reference(rows))
''',
    },
}

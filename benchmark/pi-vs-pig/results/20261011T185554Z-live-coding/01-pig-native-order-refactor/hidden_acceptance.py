import unittest, copy, random
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

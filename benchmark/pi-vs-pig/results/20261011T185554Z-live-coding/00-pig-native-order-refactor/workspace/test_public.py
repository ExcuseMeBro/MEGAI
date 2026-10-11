import unittest
from decimal import Decimal
from orders import summarize
class PublicTests(unittest.TestCase):
    def test_total(self):
        self.assertEqual(summarize([{'customer':'a','qty':2,'price':'1.25'}])['grand_total'], Decimal('2.50'))
    def test_cancelled(self):
        self.assertEqual(summarize([{'status':'cancelled'}])['customers'], {})

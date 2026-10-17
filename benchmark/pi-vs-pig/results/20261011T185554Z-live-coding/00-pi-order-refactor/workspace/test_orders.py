import unittest
from collections import UserDict
from decimal import Decimal, InvalidOperation, localcontext
from types import MappingProxyType

from orders import summarize


class SummarizeRegressionTests(unittest.TestCase):
    def test_empty_iterables(self):
        for rows in ([], iter(())):
            with self.subTest(rows=rows):
                result = summarize(rows)
                self.assertEqual(result, {'customers': {}, 'grand_total': Decimal('0')})
                self.assertIsInstance(result['grand_total'], Decimal)

    def test_generator_aggregation_and_first_seen_order(self):
        rows = (
            {'customer': 'b', 'qty': '2', 'price': '1.25'},
            {'customer': 'a', 'price': '0.10'},
            {'customer': 'b', 'qty': 3, 'price': '2', 'discount': '0.25'},
        )
        result = summarize(row for row in rows)
        self.assertEqual(list(result['customers']), ['b', 'a'])
        self.assertEqual(result, {
            'customers': {
                'b': {'qty': 5, 'total': Decimal('7.00')},
                'a': {'qty': 1, 'total': Decimal('0.10')},
            },
            'grand_total': Decimal('7.10'),
        })
        for summary in result['customers'].values():
            self.assertIsInstance(summary['qty'], int)
            self.assertIsInstance(summary['total'], Decimal)

    def test_defaults_and_customer_stringification(self):
        result = summarize([{}, {'customer': 42}, {'customer': '42'}, {'customer': None}])
        self.assertEqual(result, {
            'customers': {
                'unknown': {'qty': 1, 'total': Decimal('0')},
                '42': {'qty': 2, 'total': Decimal('0')},
                'None': {'qty': 1, 'total': Decimal('0')},
            },
            'grand_total': Decimal('0'),
        })

    def test_only_exact_cancelled_status_is_skipped(self):
        rows = [{'status': 'cancelled', 'qty': 'invalid', 'price': None}]
        rows.extend({'status': status, 'price': '1'}
                    for status in ('canceled', 'Cancelled', 'cancelled ', '', None))
        rows.append({'price': '1'})
        self.assertEqual(summarize(rows), {
            'customers': {'unknown': {'qty': 6, 'total': Decimal('6')}},
            'grand_total': Decimal('6'),
        })

    def test_negative_quantity_and_unrestricted_discounts(self):
        result = summarize([
            {'qty': -2, 'price': '3', 'discount': '-0.5'},
            {'qty': 3, 'price': '4', 'discount': '1.5'},
            {'qty': 0, 'price': '100'},
        ])
        self.assertEqual(result, {
            'customers': {'unknown': {'qty': 1, 'total': Decimal('-15.0')}},
            'grand_total': Decimal('-15.0'),
        })

    def test_decimal_conversion_uses_string_not_binary_float(self):
        result = summarize([{'price': 0.1, 'qty': '3', 'discount': 0.2}])
        self.assertEqual(result['grand_total'], Decimal('0.24'))

    def test_mappings_are_not_mutated(self):
        original = {'customer': 'a', 'qty': '2', 'price': '1.25', 'extra': []}
        snapshot = original.copy()
        rows = [MappingProxyType(original), UserDict(original)]
        self.assertEqual(summarize(rows)['grand_total'], Decimal('5.00'))
        self.assertEqual(original, snapshot)
        self.assertEqual(rows[1], snapshot)

    def test_malformed_numeric_fields_raise_for_new_and_existing_customers(self):
        cases = (
            ('qty', 'invalid', ValueError),
            ('qty', None, TypeError),
            ('price', 'invalid', InvalidOperation),
            ('price', None, InvalidOperation),
            ('discount', 'invalid', InvalidOperation),
            ('discount', None, InvalidOperation),
        )
        for field, value, exception in cases:
            for existing in (False, True):
                with self.subTest(field=field, value=value, existing=existing):
                    rows = [{}] if existing else []
                    rows.append({field: value})
                    with self.assertRaises(exception):
                        summarize(rows)

    def test_decimal_accumulation_order_under_limited_precision(self):
        with localcontext() as context:
            context.prec = 3
            result = summarize([
                {'customer': 'a', 'price': '1000'},
                {'customer': 'b', 'price': '1'},
                {'customer': 'a', 'price': '-1000'},
            ])
        self.assertEqual(result['customers']['a']['total'], Decimal('0'))
        self.assertEqual(result['customers']['b']['total'], Decimal('1'))
        self.assertEqual(result['grand_total'], Decimal('0'))

    def test_first_customer_amount_retains_signed_zero(self):
        result = summarize([{'price': '-0.00'}])
        self.assertEqual(result['customers']['unknown']['total'].as_tuple(),
                         Decimal('-0.00').as_tuple())
        self.assertEqual(result['grand_total'].as_tuple(), Decimal('0.00').as_tuple())


if __name__ == '__main__':
    unittest.main()

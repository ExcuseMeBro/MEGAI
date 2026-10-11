import unittest
from copy import deepcopy
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

    def test_defaults_and_stringified_customers(self):
        result = summarize([{}, {'customer': 7}, {'customer': '7'}, {'customer': None}])
        self.assertEqual(result, {
            'customers': {
                'unknown': {'qty': 1, 'total': Decimal('0')},
                '7': {'qty': 2, 'total': Decimal('0')},
                'None': {'qty': 1, 'total': Decimal('0')},
            },
            'grand_total': Decimal('0'),
        })

    def test_generator_aggregation_and_first_seen_order(self):
        rows = (
            {'customer': 'b', 'qty': '2', 'price': '1.25', 'discount': '0.1'},
            {'customer': 'a', 'price': '0.10'},
            {'customer': 'b', 'qty': 3, 'price': Decimal('0.20')},
        )
        result = summarize(row for row in rows)
        self.assertEqual(list(result['customers']), ['b', 'a'])
        self.assertEqual(result, {
            'customers': {
                'b': {'qty': 5, 'total': Decimal('2.850')},
                'a': {'qty': 1, 'total': Decimal('0.10')},
            },
            'grand_total': Decimal('2.950'),
        })
        for summary in result['customers'].values():
            self.assertIsInstance(summary['qty'], int)
            self.assertIsInstance(summary['total'], Decimal)

    def test_only_exact_cancelled_status_is_skipped(self):
        rows = [
            {'status': 'cancelled', 'customer': 'skip', 'qty': 'bad', 'price': 'bad'},
            {'customer': 'kept', 'price': '2'},
            {'status': 'Cancelled', 'customer': 'kept', 'price': '3'},
            {'status': None, 'customer': 'kept', 'price': '4'},
            {'status': '', 'customer': 'kept', 'price': '5'},
        ]
        self.assertEqual(summarize(rows), {
            'customers': {'kept': {'qty': 4, 'total': Decimal('14')}},
            'grand_total': Decimal('14'),
        })
        self.assertEqual(summarize([rows[0]])['customers'], {})

    def test_negative_quantities_and_unbounded_discounts(self):
        result = summarize([
            {'customer': 'a', 'qty': -2, 'price': '3', 'discount': '-0.5'},
            {'customer': 'a', 'qty': 4, 'price': '2', 'discount': '1.25'},
            {'customer': 'b', 'qty': 0, 'price': '9'},
        ])
        self.assertEqual(result, {
            'customers': {
                'a': {'qty': 2, 'total': Decimal('-11')},
                'b': {'qty': 0, 'total': Decimal('0')},
            },
            'grand_total': Decimal('-11'),
        })

    def test_numeric_conversions(self):
        result = summarize([{'qty': 2.9, 'price': 0.1, 'discount': 0.2}])
        self.assertEqual(result['customers']['unknown'], {
            'qty': 2, 'total': Decimal('0.16'),
        })
        self.assertEqual(result['grand_total'], Decimal('0.16'))

    def test_decimal_context_and_operation_order(self):
        with localcontext() as context:
            context.prec = 3
            result = summarize([{'price': '1.234', 'qty': 3, 'discount': '0.12'}])
            self.assertEqual(result['grand_total'], Decimal('3.26'))
        result = summarize([{'price': '-0.00'}])
        self.assertEqual(result['customers']['unknown']['total'].as_tuple(),
                         Decimal('-0.00').as_tuple())

    def test_rows_are_not_mutated_and_accept_read_only_mappings(self):
        rows = [{'customer': 'a', 'price': '2'}, {'status': 'cancelled'}]
        original = deepcopy(rows)
        summarize(rows)
        self.assertEqual(rows, original)
        result = summarize(MappingProxyType(row) for row in rows)
        self.assertEqual(result['grand_total'], Decimal('2'))

    def test_malformed_numeric_fields_keep_exceptions(self):
        cases = (
            ('qty', 'bad', ValueError),
            ('qty', None, TypeError),
            ('price', 'bad', InvalidOperation),
            ('price', None, InvalidOperation),
            ('discount', 'bad', InvalidOperation),
            ('discount', None, InvalidOperation),
        )
        for field, value, exception in cases:
            for repeated in (False, True):
                with self.subTest(field=field, value=value, repeated=repeated):
                    rows = [{}] if repeated else []
                    rows.append({field: value})
                    with self.assertRaises(exception):
                        summarize(rows)


if __name__ == '__main__':
    unittest.main()

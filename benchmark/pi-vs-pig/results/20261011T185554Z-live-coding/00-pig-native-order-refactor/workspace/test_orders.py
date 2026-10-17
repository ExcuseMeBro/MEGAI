import unittest
from decimal import Decimal, InvalidOperation, localcontext
from types import MappingProxyType

from orders import summarize


class SummarizeRegressionTests(unittest.TestCase):
    def test_aggregation_order_and_numeric_conversions(self):
        result = summarize([
            {'customer': 'b', 'qty': '2', 'price': '1.25', 'discount': '0.2'},
            {'customer': 7, 'qty': 3, 'price': Decimal('0.10')},
            {'customer': 'b', 'qty': -1, 'price': 0.5},
            {'customer': '7', 'price': '0.20'},
        ])
        self.assertEqual(list(result['customers']), ['b', '7'])
        self.assertEqual(result, {
            'customers': {
                'b': {'qty': 1, 'total': Decimal('1.50')},
                '7': {'qty': 4, 'total': Decimal('0.50')},
            },
            'grand_total': Decimal('2.00'),
        })
        for summary in result['customers'].values():
            self.assertIsInstance(summary['qty'], int)
            self.assertIsInstance(summary['total'], Decimal)
        self.assertIsInstance(result['grand_total'], Decimal)

    def test_defaults_and_exact_cancellation(self):
        result = summarize([
            {'status': 'cancelled', 'qty': 'bad', 'price': 'bad'},
            {},
            {'status': 'Cancelled', 'price': '2'},
            {'status': None, 'customer': None, 'price': '3'},
            {'status': '', 'customer': '', 'price': '4'},
        ])
        self.assertEqual(result, {
            'customers': {
                'unknown': {'qty': 2, 'total': Decimal('2')},
                'None': {'qty': 1, 'total': Decimal('3')},
                '': {'qty': 1, 'total': Decimal('4')},
            },
            'grand_total': Decimal('9'),
        })

    def test_negative_quantity_and_unbounded_discounts(self):
        result = summarize([
            {'customer': 'a', 'qty': -2, 'price': '3', 'discount': '-0.5'},
            {'customer': 'a', 'qty': 2, 'price': '3', 'discount': '1.5'},
        ])
        self.assertEqual(result, {
            'customers': {'a': {'qty': 0, 'total': Decimal('-12')}},
            'grand_total': Decimal('-12'),
        })

    def test_empty_and_all_cancelled_iterables(self):
        for rows in ([], iter(()), ({'status': 'cancelled'} for _ in range(2))):
            with self.subTest(rows=rows):
                result = summarize(rows)
                self.assertEqual(result, {'customers': {}, 'grand_total': Decimal('0')})
                self.assertIsInstance(result['grand_total'], Decimal)

    def test_generator_of_read_only_mappings_does_not_mutate_rows(self):
        rows = [{'customer': 'a', 'price': '0.1'}, {'customer': 'a', 'price': '0.2'}]
        before = [row.copy() for row in rows]
        result = summarize(MappingProxyType(row) for row in rows)
        self.assertEqual(result, {
            'customers': {'a': {'qty': 2, 'total': Decimal('0.3')}},
            'grand_total': Decimal('0.3'),
        })
        self.assertEqual(rows, before)

    def test_decimal_precision_and_accumulation_order(self):
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

    def test_first_amount_preserves_signed_zero_and_scale(self):
        result = summarize([{'qty': -1, 'price': '0.00'}])
        self.assertEqual(
            result['customers']['unknown']['total'].as_tuple(),
            Decimal('-0.00').as_tuple(),
        )

    def test_malformed_numeric_fields_raise_for_new_and_existing_customers(self):
        cases = [
            ('qty', 'bad', ValueError),
            ('qty', None, TypeError),
            ('price', 'bad', InvalidOperation),
            ('price', None, InvalidOperation),
            ('discount', 'bad', InvalidOperation),
            ('discount', None, InvalidOperation),
        ]
        for field, value, exception in cases:
            for existing in (False, True):
                with self.subTest(field=field, value=value, existing=existing):
                    rows = [{}] if existing else []
                    rows.append({field: value})
                    with self.assertRaises(exception):
                        summarize(rows)


if __name__ == '__main__':
    unittest.main()

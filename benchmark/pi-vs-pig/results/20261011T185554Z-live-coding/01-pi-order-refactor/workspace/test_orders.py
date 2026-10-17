import unittest
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
            {'customer': 'b', 'qty': '2', 'price': '1.25'},
            {'customer': 'a', 'price': '0.10', 'discount': '0.2'},
            {'customer': 'b', 'qty': 3, 'price': '0.10'},
        )
        result = summarize(row for row in rows)
        self.assertEqual(list(result['customers']), ['b', 'a'])
        self.assertEqual(result, {
            'customers': {
                'b': {'qty': 5, 'total': Decimal('2.80')},
                'a': {'qty': 1, 'total': Decimal('0.080')},
            },
            'grand_total': Decimal('2.880'),
        })
        for summary in result['customers'].values():
            self.assertIsInstance(summary['qty'], int)
            self.assertIsInstance(summary['total'], Decimal)

    def test_only_exact_cancelled_status_is_skipped(self):
        rows = [{'customer': 'skipped', 'status': 'cancelled',
                 'qty': None, 'price': 'bad', 'discount': 'bad'}]
        rows.extend({'customer': 'kept', 'status': status, 'price': '2'}
                    for status in ('Cancelled', 'canceled', '', None, False))
        rows.append({'customer': 'kept', 'price': '2'})
        self.assertEqual(summarize(rows), {
            'customers': {'kept': {'qty': 6, 'total': Decimal('12')}},
            'grand_total': Decimal('12'),
        })

    def test_negative_quantity_and_unbounded_discounts(self):
        result = summarize([
            {'customer': 'a', 'qty': -2, 'price': '3', 'discount': '-0.5'},
            {'customer': 'a', 'qty': 4, 'price': '2', 'discount': '1.25'},
            {'customer': 'b', 'qty': 0, 'price': '10', 'discount': '3'},
        ])
        self.assertEqual(result, {
            'customers': {
                'a': {'qty': 2, 'total': Decimal('-11.00')},
                'b': {'qty': 0, 'total': Decimal('0')},
            },
            'grand_total': Decimal('-11.00'),
        })

    def test_decimal_precision_and_numeric_conversion(self):
        with localcontext() as context:
            context.prec = 60
            price = '12345678901234567890.12345678901234567890'
            amount = Decimal(price) * 3 * (Decimal('1') - Decimal('0.123456789'))
            result = summarize([
                {'customer': 'a', 'qty': '3', 'price': price, 'discount': '0.123456789'},
                {'customer': 'a', 'qty': 1.9, 'price': 0.1, 'discount': Decimal('0.2')},
            ])
            self.assertEqual(result['customers']['a']['qty'], 4)
            self.assertEqual(result['customers']['a']['total'], amount + Decimal('0.08'))
            self.assertEqual(result['grand_total'], amount + Decimal('0.08'))

    def test_first_amount_preserves_signed_zero(self):
        result = summarize([{'price': '-0.00'}])
        self.assertEqual(result['customers']['unknown']['total'].as_tuple(),
                         Decimal('-0.00').as_tuple())
        self.assertEqual(result['grand_total'].as_tuple(), Decimal('0.00').as_tuple())

    def test_rows_are_not_mutated_and_read_only_mappings_work(self):
        rows = [{'customer': 'a', 'qty': '2', 'price': '1.25', 'extra': []},
                {'status': 'cancelled', 'qty': 'invalid'}]
        originals = [row.copy() for row in rows]
        summarize(rows)
        self.assertEqual(rows, originals)
        self.assertEqual(summarize(map(MappingProxyType, rows)), summarize(rows))

    def test_malformed_numeric_fields_raise_existing_exceptions(self):
        cases = [
            ({'qty': 'bad'}, ValueError),
            ({'qty': None}, TypeError),
            ({'price': 'bad'}, InvalidOperation),
            ({'price': None}, InvalidOperation),
            ({'discount': 'bad'}, InvalidOperation),
            ({'discount': None}, InvalidOperation),
        ]
        for row, exception in cases:
            for prefix in ([], [{'customer': 'unknown'}]):
                with self.subTest(row=row, existing_customer=bool(prefix)):
                    with self.assertRaises(exception):
                        summarize(prefix + [row])


if __name__ == '__main__':
    unittest.main()

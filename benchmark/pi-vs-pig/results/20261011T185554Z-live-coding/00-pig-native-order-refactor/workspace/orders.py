from decimal import Decimal


def summarize(rows):
    """Aggregate quantities and discounted totals for non-cancelled rows."""
    customers = {}
    grand_total = Decimal('0')

    for row in rows:
        if row.get('status', '') == 'cancelled':
            continue

        customer = str(row.get('customer', 'unknown'))
        qty = int(row.get('qty', 1))
        price = Decimal(str(row.get('price', '0')))
        discount = Decimal(str(row.get('discount', '0')))
        amount = price * qty * (Decimal('1') - discount)

        if customer in customers:
            summary = customers[customer]
            summary['qty'] += qty
            summary['total'] += amount
        else:
            customers[customer] = {'qty': qty, 'total': amount}
        grand_total += amount

    return {'customers': customers, 'grand_total': grand_total}
